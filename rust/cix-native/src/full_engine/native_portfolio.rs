//! Process-free whole-archive native portfolio.
//!
//! This is the library counterpart of the historical BEST archive search.  It
//! accepts bytes already owned by its caller: it neither opens paths nor
//! consults environment state, installs handlers, starts processes, or writes
//! diagnostics.  The result carries every attempted family and every bounded
//! omission so an embedding can make an honest policy decision.

use crate::core::{
    self,
    engine::{
        check_interrupted, decode, encode_m6, encode_with_strategy, EncodeOptions, MAX_BLOCK,
    },
    external,
};
use std::{
    io::{self, Write},
    sync::{atomic::AtomicBool, Arc},
    time::{Duration, Instant},
};

const MIB: usize = 1 << 20;
const OUTPUT_SLACK: usize = 2 * MIB;
const MIN_REMAINDER: usize = 16 * MIB;
const MAX_INPUT: usize = external::MAX_INPUT;
const MAX_DIAGNOSTICS: usize = 64;
const PREFIX_PRUNED: &str = "whole-archive candidate prefix cannot improve the incumbent";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativePortfolioProfile {
    Fast,
    Default,
    Best,
}

#[derive(Clone, Debug)]
pub struct NativePortfolioOptions {
    pub profile: NativePortfolioProfile,
    /// Aggregate budget.  The selector charges caller source bytes, retained
    /// winner capacity, trial output capacity and codec/backend reservations.
    pub memory_bytes: usize,
    /// Maximum serialized archive capacity for any retained or trial result.
    pub output_bytes: usize,
    pub workers: usize,
    /// Absolute caller deadline. Native one-shot CIXB1 backends observe it
    /// before and after their call, so expiry cannot preempt a backend ABI.
    pub deadline: Option<Instant>,
    pub cancellation: Option<Arc<AtomicBool>>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativePortfolioStatus {
    Completed,
    Omitted,
    Selected,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativePortfolioCandidate {
    pub id: String,
    pub status: NativePortfolioStatus,
    pub archive_bytes: Option<usize>,
    pub reason: Option<String>,
}

#[derive(Clone, Debug)]
pub struct NativePortfolioResult {
    pub archive: Vec<u8>,
    pub selected: String,
    pub candidates: Vec<NativePortfolioCandidate>,
    pub source_bytes_charged: usize,
    pub retained_output_capacity: usize,
    pub search_budget: Duration,
    pub elapsed: Duration,
}

impl NativePortfolioOptions {
    fn validate(&self, input_len: usize) -> Result<(), String> {
        if input_len > MAX_INPUT {
            return Err("native whole-archive input exceeds 128 MiB admission".into());
        }
        if self.memory_bytes == 0 || self.output_bytes == 0 || self.workers == 0 {
            return Err(
                "native portfolio requires non-zero memory, output and worker limits".into(),
            );
        }
        Ok(())
    }
}

fn archive_cap(n: usize) -> usize {
    n.saturating_add(OUTPUT_SLACK)
        .min(external::MAX_PAYLOAD.saturating_add(47))
}
fn best_fallback_cap(options: &NativePortfolioOptions, input_len: usize) -> Result<usize, String> {
    let cap = archive_cap(input_len);
    if options.output_bytes < cap {
        Err("BEST output limit cannot admit the raw CIXG2 fallback".into())
    } else {
        Ok(cap)
    }
}
fn whole_budget(n: usize) -> Duration {
    // The historical level-9 policy: 15 minutes plus up to 45 minutes scaled
    // by input.  The two native families each retain half of this allocation.
    Duration::from_secs(900 + (n / MIB).saturating_mul(30).min(2700) as u64)
}
fn stopped(o: &NativePortfolioOptions) -> bool {
    o.cancellation
        .as_ref()
        .is_some_and(|v| v.load(std::sync::atomic::Ordering::Acquire))
        || o.deadline.is_some_and(|d| Instant::now() >= d)
}
fn remaining(
    o: &NativePortfolioOptions,
    family: Duration,
    started: Instant,
    slots: usize,
) -> Option<Duration> {
    let local = family.saturating_sub(started.elapsed());
    let global = o
        .deadline
        .map(|d| d.saturating_duration_since(Instant::now()))
        .unwrap_or(local);
    local
        .min(global)
        .checked_div(slots as u32)
        .filter(|v| !v.is_zero())
}
fn omission(
    out: &mut Vec<NativePortfolioCandidate>,
    id: impl Into<String>,
    reason: impl Into<String>,
) {
    if out.len() < MAX_DIAGNOSTICS {
        out.push(NativePortfolioCandidate {
            id: id.into(),
            status: NativePortfolioStatus::Omitted,
            archive_bytes: None,
            reason: Some(reason.into()),
        });
    }
}
fn completed(out: &mut Vec<NativePortfolioCandidate>, id: impl Into<String>, bytes: usize) {
    if out.len() < MAX_DIAGNOSTICS {
        out.push(NativePortfolioCandidate {
            id: id.into(),
            status: NativePortfolioStatus::Completed,
            archive_bytes: Some(bytes),
            reason: None,
        });
    }
}
fn resource_error(error: &str) -> bool {
    error.contains("deadline")
        || error.contains("memory")
        || error.contains("output")
        || error.contains(PREFIX_PRUNED)
}
fn candidate_rejection(error: &str) -> bool {
    error.starts_with("BSC candidate rejected:") || error.starts_with("ZPAQ candidate rejected:")
}

struct CappedWriter {
    bytes: Vec<u8>,
    cap: usize,
    incumbent: Option<usize>,
}
impl CappedWriter {
    fn new(cap: usize, incumbent: Option<usize>) -> Result<Self, String> {
        let mut bytes = Vec::new();
        bytes
            .try_reserve_exact(cap)
            .map_err(|_| "whole-archive output reservation allocation failed".to_string())?;
        Ok(Self {
            bytes,
            cap,
            incumbent,
        })
    }
}
impl Write for CappedWriter {
    fn write(&mut self, input: &[u8]) -> io::Result<usize> {
        if input.len() > self.cap.saturating_sub(self.bytes.len()) {
            return Err(io::Error::other("whole-archive output limit exceeded"));
        }
        if self
            .incumbent
            .is_some_and(|n| input.len() > n.saturating_sub(self.bytes.len()))
        {
            return Err(io::Error::other(PREFIX_PRUNED));
        }
        self.bytes.extend_from_slice(input);
        Ok(input.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
struct CompareWriter<'a> {
    expected: &'a [u8],
    offset: usize,
    exact: bool,
}
impl Write for CompareWriter<'_> {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        let end = self.offset.saturating_add(bytes.len());
        self.exact &=
            end <= self.expected.len() && self.expected.get(self.offset..end) == Some(bytes);
        self.offset = end;
        Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
fn available(
    o: &NativePortfolioOptions,
    source: usize,
    winner: usize,
    trial: usize,
) -> Option<usize> {
    o.memory_bytes
        .checked_sub(source)?
        .checked_sub(winner)?
        .checked_sub(trial)
        .filter(|n| *n >= MIN_REMAINDER)
}
fn validate(
    archive: &[u8],
    archive_capacity: usize,
    input: &[u8],
    o: &NativePortfolioOptions,
    retained: usize,
) -> Result<(), String> {
    let memory = available(o, input.len(), retained, archive_capacity)
        .ok_or("validation memory admission")?;
    let mut restored = CompareWriter {
        expected: input,
        offset: 0,
        exact: true,
    };
    decode(
        io::Cursor::new(archive),
        &mut restored,
        false,
        false,
        -1,
        memory,
    )?;
    if restored.exact && restored.offset == input.len() {
        check_interrupted()?;
        Ok(())
    } else {
        Err("whole-archive candidate failed exact reconstruction".into())
    }
}
fn consider(
    id: String,
    candidate: Vec<u8>,
    input: &[u8],
    o: &NativePortfolioOptions,
    winner: &mut Vec<u8>,
    name: &mut String,
    diagnostics: &mut Vec<NativePortfolioCandidate>,
) -> Result<(), String> {
    if candidate.len() > o.output_bytes || candidate.capacity() > o.output_bytes {
        omission(diagnostics, id, "candidate exceeded output reservation");
        return Ok(());
    }
    validate(
        &candidate,
        candidate.capacity(),
        input,
        o,
        winner.capacity(),
    )?;
    completed(diagnostics, id.clone(), candidate.len());
    if candidate.len() < winner.len() {
        *winner = candidate;
        *name = id;
    }
    Ok(())
}
fn native_trial(
    input: &[u8],
    o: &NativePortfolioOptions,
    winner: &mut Vec<u8>,
    selected: &mut String,
    diagnostics: &mut Vec<NativePortfolioCandidate>,
    id: String,
    budget: Duration,
    format: &str,
    block: u32,
) -> Result<(), String> {
    check_interrupted()?;
    let Some(memory) = available(o, input.len(), winner.capacity(), o.output_bytes) else {
        omission(
            diagnostics,
            id,
            "source, retained output and trial output exceed memory admission",
        );
        return Ok(());
    };
    let mut writer = match CappedWriter::new(o.output_bytes, Some(winner.len())) {
        Ok(writer) => writer,
        Err(error) => {
            omission(diagnostics, id, error);
            return Ok(());
        }
    };
    let guard = crate::limits::DeadlineGuard::new(budget);
    let result = encode_with_strategy(
        io::Cursor::new(input),
        &mut writer,
        EncodeOptions {
            block,
            level: 9,
            forced: None,
            backend: "hybrid",
            backend_set: false,
            format,
            input_fd: -1,
            flush_interval: None,
            memory,
            workers: o.workers,
            explain: false,
            verbose: false,
            strategy: "blocks",
        },
    );
    let terminal = check_interrupted();
    drop(guard);
    if let Err(error) = terminal {
        if stopped(o) {
            return Err("native portfolio cancelled or deadline exceeded".into());
        }
        if error == crate::limits::DEADLINE_ERROR {
            omission(diagnostics, id, error);
            return Ok(());
        }
        return Err(error);
    }
    match result {
        Ok(()) => consider(id, writer.bytes, input, o, winner, selected, diagnostics),
        Err(e) if resource_error(&e) => {
            omission(diagnostics, id, e);
            Ok(())
        }
        Err(e) => Err(e),
    }
}
fn m6_trial(
    input: &[u8],
    o: &NativePortfolioOptions,
    winner: &mut Vec<u8>,
    selected: &mut String,
    diagnostics: &mut Vec<NativePortfolioCandidate>,
    id: String,
    budget: Duration,
    block: usize,
) -> Result<(), String> {
    check_interrupted()?;
    let Some(memory) = available(o, input.len(), winner.capacity(), o.output_bytes) else {
        omission(
            diagnostics,
            id,
            "source, retained output and trial output exceed memory admission",
        );
        return Ok(());
    };
    let mut writer = match CappedWriter::new(o.output_bytes, Some(winner.len())) {
        Ok(writer) => writer,
        Err(error) => {
            omission(diagnostics, id, error);
            return Ok(());
        }
    };
    let guard = crate::limits::DeadlineGuard::new(budget);
    let result = encode_m6(io::Cursor::new(input), &mut writer, block, None, 9, memory);
    let terminal = check_interrupted();
    drop(guard);
    if let Err(error) = terminal {
        if stopped(o) {
            return Err("native portfolio cancelled or deadline exceeded".into());
        }
        if error == crate::limits::DEADLINE_ERROR {
            omission(diagnostics, id, error);
            return Ok(());
        }
        return Err(error);
    }
    match result {
        Ok(()) => consider(id, writer.bytes, input, o, winner, selected, diagnostics),
        Err(e) if resource_error(&e) => {
            omission(diagnostics, id, e);
            Ok(())
        }
        Err(e) => Err(e),
    }
}

/// Encode one buffer. FAST and DEFAULT deliberately retain the existing
/// direct core path. BEST additionally evaluates CIXG1/CIXG2, CIXM6 and all
/// registered complete CIXB1 descriptors, serially and deterministically.
pub fn select(
    input: &[u8],
    options: &NativePortfolioOptions,
) -> Result<NativePortfolioResult, String> {
    options.validate(input.len())?;
    if stopped(options) {
        return Err("native portfolio cancelled or deadline exceeded".into());
    }
    let started = Instant::now();
    let _library = crate::limits::LibraryGuard::new();
    let _cancel = options
        .cancellation
        .clone()
        .map(crate::limits::CancellationGuard::new);
    // This is the caller's absolute cancellation contract.  The historical
    // CIXG/CIXM6 effort budget below is deliberately narrower and does not
    // impose a synthetic timeout on retained one-shot CIXB1 backends.
    let _caller_deadline = options.deadline.map(|deadline| {
        crate::limits::DeadlineGuard::new(deadline.saturating_duration_since(Instant::now()))
    });
    if options.profile != NativePortfolioProfile::Best {
        let memory_limit = available(options, input.len(), 0, options.output_bytes)
            .ok_or("native profile cannot admit source, output reservation and codec remainder")?;
        // `encode_buffer` owns an unconstrained Vec whose allocator capacity
        // can exceed its logical writer limit. Reserve the caller's complete
        // output bound first and pass that bounded writer to the core path.
        let mut writer = CappedWriter::new(options.output_bytes, None)?;
        core::encode(
            input,
            &mut writer,
            &core::NativeOptions {
                profile: match options.profile {
                    NativePortfolioProfile::Fast => core::NativeProfile::Fast,
                    _ => core::NativeProfile::Default,
                },
                output_limit: options.output_bytes,
                memory_limit,
                workers: options.workers,
                deadline: options
                    .deadline
                    .map(|d| d.saturating_duration_since(Instant::now())),
                cancellation: options.cancellation.clone(),
            },
        )
        .map_err(|e| e.to_string())?;
        check_interrupted()?;
        let archive = writer.bytes;
        let archive_bytes = archive.len();
        return Ok(NativePortfolioResult {
            selected: "core-native".into(),
            retained_output_capacity: archive.capacity(),
            archive,
            candidates: vec![NativePortfolioCandidate {
                id: "core-native".into(),
                status: NativePortfolioStatus::Selected,
                archive_bytes: Some(archive_bytes),
                reason: None,
            }],
            source_bytes_charged: input.len(),
            search_budget: Duration::ZERO,
            elapsed: started.elapsed(),
        });
    }
    let cap = best_fallback_cap(options, input.len())?;
    let Some(memory) = available(options, input.len(), 0, cap) else {
        return Err("BEST cannot admit source, raw fallback and codec remainder".into());
    };
    let mut raw = CappedWriter::new(cap, None)?;
    encode_with_strategy(
        io::Cursor::new(input),
        &mut raw,
        EncodeOptions {
            block: MAX_BLOCK,
            level: 9,
            forced: Some("raw"),
            backend: "hybrid",
            backend_set: false,
            format: "cixg2",
            input_fd: -1,
            flush_interval: None,
            memory,
            workers: options.workers,
            explain: false,
            verbose: false,
            strategy: "blocks",
        },
    )?;
    let mut winner = raw.bytes;
    check_interrupted()?;
    validate(&winner, winner.capacity(), input, options, 0)?;
    let mut selected = "cixg2:raw-baseline".to_string();
    let mut diagnostics = vec![NativePortfolioCandidate {
        id: selected.clone(),
        status: NativePortfolioStatus::Completed,
        archive_bytes: Some(winner.len()),
        reason: None,
    }];
    let budget = whole_budget(input.len());
    let cixg_budget = budget / 2;
    let m6_budget = budget.saturating_sub(cixg_budget);
    let blocks: Vec<u32> = if input.len() <= 16 * MIB {
        vec![16 * 1024, 32 * 1024, MAX_BLOCK]
    } else {
        vec![MAX_BLOCK]
    };
    let cixg_started = Instant::now();
    for (i, (format, block)) in ["cixg1", "cixg2"]
        .into_iter()
        .flat_map(|f| blocks.iter().copied().map(move |b| (f, b)))
        .enumerate()
    {
        let id = format!("{format}:native-auto:block={block}");
        let Some(slice) = remaining(options, cixg_budget, cixg_started, blocks.len() * 2 - i)
        else {
            omission(
                &mut diagnostics,
                id,
                "CIXG family deadline allocation exhausted",
            );
            continue;
        };
        native_trial(
            input,
            options,
            &mut winner,
            &mut selected,
            &mut diagnostics,
            id,
            slice,
            format,
            block,
        )?;
    }
    let m6_started = Instant::now();
    for (i, block) in blocks.iter().copied().enumerate() {
        let id = format!("cixm6:native-auto:block={block}");
        let Some(slice) = remaining(options, m6_budget, m6_started, blocks.len() - i) else {
            omission(
                &mut diagnostics,
                id,
                "CIXM6 family deadline allocation exhausted",
            );
            continue;
        };
        m6_trial(
            input,
            options,
            &mut winner,
            &mut selected,
            &mut diagnostics,
            id,
            slice,
            block as usize,
        )?;
    }
    for descriptor in external::best_candidates() {
        check_interrupted()?;
        if stopped(options) {
            return Err("native portfolio cancelled or deadline exceeded".into());
        }
        let available = options
            .memory_bytes
            .saturating_sub(input.len())
            .saturating_sub(winner.capacity());
        if let Err(reason) = descriptor.admit(input.len(), available) {
            omission(&mut diagnostics, descriptor.id, reason.reason);
            continue;
        }
        let archive = match descriptor.full_archive_encode(input) {
            Ok(v) => v,
            Err(e) if resource_error(&e) || candidate_rejection(&e) => {
                if stopped(options) {
                    return Err("native portfolio cancelled or deadline exceeded".into());
                }
                omission(&mut diagnostics, descriptor.id, e);
                continue;
            }
            Err(e) => return Err(e),
        };
        // A one-shot backend can only observe cancellation before/after its
        // native call.  Do not publish or validate its archive after a caller
        // cancellation/deadline raced the call.
        check_interrupted()?;
        // `encoder_peak_bytes` above reserves the descriptor's payload/wrapper
        // copies; this check makes the caller-visible retained-output bound
        // explicit even when a backend produced an unexpectedly large frame.
        let decoder_available = options
            .memory_bytes
            .saturating_sub(input.len())
            .saturating_sub(winner.capacity())
            .saturating_sub(archive.capacity());
        match descriptor.decoder_peak_bytes(input.len()) {
            Ok(needed) if needed <= decoder_available => consider(
                descriptor.id.into(),
                archive,
                input,
                options,
                &mut winner,
                &mut selected,
                &mut diagnostics,
            )?,
            Ok(needed) => omission(
                &mut diagnostics,
                descriptor.id,
                format!("validation needs {needed} bytes, available {decoder_available}"),
            ),
            Err(reason) => omission(&mut diagnostics, descriptor.id, reason),
        }
    }
    validate(&winner, winner.capacity(), input, options, 0)?;
    if let Some(entry) = diagnostics.iter_mut().find(|x| x.id == selected) {
        entry.status = NativePortfolioStatus::Selected;
    }
    Ok(NativePortfolioResult {
        retained_output_capacity: winner.capacity(),
        archive: winner,
        selected,
        candidates: diagnostics,
        source_bytes_charged: input.len(),
        search_budget: budget,
        elapsed: started.elapsed(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn best_admission_includes_a_raw_fallback() {
        let n = 4096;
        let options = NativePortfolioOptions {
            profile: NativePortfolioProfile::Best,
            memory_bytes: 128 * MIB,
            output_bytes: archive_cap(n).saturating_sub(1),
            workers: 1,
            deadline: None,
            cancellation: None,
        };
        assert!(options.validate(n).is_ok());
        assert!(best_fallback_cap(&options, n).is_err());
    }

    #[test]
    fn direct_profile_allows_a_smaller_legal_output_cap() {
        let options = NativePortfolioOptions {
            profile: NativePortfolioProfile::Fast,
            memory_bytes: 128 * MIB,
            output_bytes: 1,
            workers: 1,
            deadline: None,
            cancellation: None,
        };
        assert!(options.validate(4096).is_ok());
    }

    #[test]
    fn output_reservation_failure_is_fallible() {
        assert!(CappedWriter::new(usize::MAX, None).is_err());
    }

    #[test]
    fn family_budget_is_split_without_losing_total_time() {
        let total = whole_budget(8 * MIB);
        let cixg = total / 2;
        assert_eq!(cixg + total.saturating_sub(cixg), total);
    }

    #[test]
    fn capped_writer_keeps_an_equal_candidate_materializable() {
        let mut writer = CappedWriter::new(8, Some(3)).unwrap();
        writer.write_all(b"abc").unwrap();
        assert_eq!(writer.bytes, b"abc");
        assert_eq!(
            writer.write_all(b"d").unwrap_err().to_string(),
            PREFIX_PRUNED
        );
    }

    #[test]
    fn best_tiny_input_keeps_every_whole_archive_family_observable() {
        // Deliberately generated bytes: this exercises selection without a
        // corpus identity, file name, or pre-existing archive.
        let input: Vec<u8> = (0..191)
            .map(|index| ((index * 37 + index / 7) & 0xff) as u8)
            .collect();
        let output_bytes = archive_cap(input.len());
        let options = NativePortfolioOptions {
            profile: NativePortfolioProfile::Best,
            memory_bytes: 2usize << 30,
            output_bytes,
            workers: 1,
            deadline: None,
            cancellation: None,
        };

        let selected = select(&input, &options).expect("tiny BEST selection");
        assert!(selected.retained_output_capacity <= options.output_bytes);
        assert!(selected.archive.len() <= options.output_bytes);

        let cixg_ids: Vec<String> = ["cixg1", "cixg2"]
            .into_iter()
            .flat_map(|format| {
                [16 * 1024, 32 * 1024, MAX_BLOCK]
                    .into_iter()
                    .map(move |block| format!("{format}:native-auto:block={block}"))
            })
            .collect();
        let m6_ids: Vec<String> = [16 * 1024, 32 * 1024, MAX_BLOCK]
            .into_iter()
            .map(|block| format!("cixm6:native-auto:block={block}"))
            .collect();
        assert_eq!(external::best_candidates().len(), 14);
        let external_ids: Vec<String> = external::best_candidates()
            .iter()
            .map(|candidate| candidate.id.to_string())
            .collect();
        for id in cixg_ids
            .iter()
            .chain(m6_ids.iter())
            .chain(external_ids.iter())
        {
            let trial = selected
                .candidates
                .iter()
                .find(|trial| trial.id == id.as_str())
                .unwrap_or_else(|| panic!("missing BEST diagnostic for {id}"));
            assert!(matches!(
                trial.status,
                NativePortfolioStatus::Completed
                    | NativePortfolioStatus::Omitted
                    | NativePortfolioStatus::Selected
            ));
        }

        let minimum_completed = selected
            .candidates
            .iter()
            .filter_map(|trial| match trial.status {
                NativePortfolioStatus::Completed | NativePortfolioStatus::Selected => {
                    trial.archive_bytes
                }
                NativePortfolioStatus::Omitted => None,
            })
            .min()
            .expect("raw baseline is complete");
        assert_eq!(selected.archive.len(), minimum_completed);

        // This is intentionally archive-only: the decoder receives only the
        // selected bytes, with no selector state or original input supplied.
        let restored = core::decode_buffer(
            &selected.archive,
            &core::NativeOptions {
                profile: core::NativeProfile::Best,
                output_limit: input.len(),
                memory_limit: options.memory_bytes,
                workers: 1,
                deadline: None,
                cancellation: None,
            },
        )
        .expect("selected archive restores independently");
        assert_eq!(restored, input);
    }
}
