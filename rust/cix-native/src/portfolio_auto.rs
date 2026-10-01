//! Bounded whole-archive BEST selection for ordinary named inputs.
//!
//! CIXG frames remain the streaming encoder.  For a regular, named file that
//! fits the declared memory limit, BEST can also compare a complete native
//! CIXG2 archive with complete CIXB1 backend envelopes.  This module never
//! changes the streaming path: it reads the source once, rejects a metadata
//! race, and owns every whole-input allocation explicitly.

use super::{check_interrupted, decode, encode_with_strategy, external, ioerr, Opt, MAX_BLOCK};
use std::fs::{self, File, Metadata};
use std::io::{self, Read, Write};
use std::time::{Duration, Instant};

/// Native BEST is deliberately granted a whole-file budget rather than the
/// historical per-route 180 second portfolio cutoff.  This is a cooperative
/// deadline.  One-shot native-library backends do not have cooperative
/// cancellation points; they are admitted by memory and report that limit
/// honestly rather than claiming signal-interrupt latency they cannot provide.
const NATIVE_WHOLE_ARCHIVE_BUDGET: Duration = Duration::from_secs(15 * 60);
const OUTPUT_SLACK: usize = 2 * 1024 * 1024;
const NATIVE_MINIMUM: usize = 16 * 1024 * 1024;

#[derive(Debug)]
pub(super) struct SelectedArchive {
    pub archive: Vec<u8>,
    pub selected: String,
    pub evaluated: usize,
    pub omitted: Vec<String>,
    pub elapsed: Duration,
}

/// Whole-archive candidates are legal only where reading a single bounded
/// regular file cannot weaken stream semantics or surprise an expert override.
pub(super) fn eligible(o: &Opt) -> bool {
    let file_fits = fs::metadata(&o.input).is_ok_and(|metadata| {
        metadata.is_file()
            && metadata.len() <= external::MAX_INPUT as u64
            && usize::try_from(metadata.len()).is_ok_and(|length| {
                let cap = archive_cap(length);
                o.memory
                    >= length
                        .saturating_add(1)
                        .saturating_add(cap.saturating_mul(2))
                        .saturating_add(NATIVE_MINIMUM)
            })
    });
    o.level >= 9
        && !o.decode
        && !o.test
        && !o.list
        && o.input != "-"
        && !o.stream
        && o.flush_interval.is_none()
        && !o.independent_blocks
        && o.route.as_deref().is_none_or(|route| route == "auto")
        && !o.backend_set
        && o.format == "auto"
        && o.block.is_none()
        && o.history == 0
        && o.portfolio.is_none()
        && o.external_backend.is_none()
        && file_fits
}

pub(super) fn exclusion_reason(o: &Opt) -> Option<&'static str> {
    if o.level < 9 || o.decode || o.test || o.list {
        return None;
    }
    if o.input == "-" {
        Some("stdin/non-seekable input uses bounded CIXG streaming")
    } else if o.stream || o.flush_interval.is_some() {
        Some("--stream/--flush-interval requires bounded CIXG streaming")
    } else if fs::metadata(&o.input).is_err() || !fs::metadata(&o.input).is_ok_and(|m| m.is_file())
    {
        Some("whole-archive BEST requires a readable regular named file")
    } else if fs::metadata(&o.input).is_ok_and(|m| m.len() > external::MAX_INPUT as u64) {
        Some("input exceeds the bounded whole-archive BEST limit; using CIXG streaming")
    } else if fs::metadata(&o.input).is_ok_and(|m| {
        usize::try_from(m.len()).is_ok_and(|length| {
            o.memory
                < length
                    .saturating_add(1)
                    .saturating_add(archive_cap(length).saturating_mul(2))
                    .saturating_add(NATIVE_MINIMUM)
        })
    }) {
        Some("--memory cannot admit source and complete archive trials; using CIXG streaming")
    } else if o.independent_blocks {
        Some("--independent-blocks constrains CIXG framing")
    } else if o.route.as_deref().is_some_and(|route| route != "auto")
        || o.backend_set
        || o.format != "auto"
        || o.block.is_some()
    {
        Some("expert route/backend/format/block constraint excludes whole-archive CIXB1 candidates")
    } else if o.history != 0 {
        Some("history constraint excludes whole-archive CIXB1 candidates")
    } else if o.portfolio.is_some() || o.external_backend.is_some() {
        Some("explicit portfolio/external selection already controls whole-archive candidates")
    } else {
        None
    }
}

fn same_identity(before: &Metadata, after: &Metadata) -> bool {
    if before.len() != after.len() {
        return false;
    }
    // A changed modification time catches replacements on all supported
    // platforms.  Unix inode/device identity catches replacement preserving
    // length and timestamp resolution.
    if before.modified().ok() != after.modified().ok() {
        return false;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        before.dev() == after.dev()
            && before.ino() == after.ino()
            && before.ctime() == after.ctime()
            && before.ctime_nsec() == after.ctime_nsec()
    }
    #[cfg(not(unix))]
    {
        true
    }
}

fn read_regular_once(path: &str) -> Result<Vec<u8>, String> {
    let mut file = File::open(path).map_err(ioerr)?;
    let before = file.metadata().map_err(ioerr)?;
    if !before.is_file() {
        return Err("whole-archive BEST requires a regular named input file".into());
    }
    let declared = usize::try_from(before.len()).map_err(|_| "input is too large")?;
    if declared > external::MAX_INPUT {
        return Err(format!(
            "whole-archive BEST excludes input above {} MiB; using bounded CIXG streaming",
            external::MAX_INPUT / (1024 * 1024)
        ));
    }
    let cap = declared.checked_add(1).ok_or("input length overflow")?;
    // Reserve the single overflow-probe byte too.  `read_to_end` therefore
    // cannot geometrically grow the source while checking declared_len + 1.
    let mut data = Vec::with_capacity(cap);
    std::io::Read::by_ref(&mut file)
        .take(cap as u64)
        .read_to_end(&mut data)
        .map_err(ioerr)?;
    // Compare the opened descriptor as well as the path.  The descriptor
    // catches writes to the file while it is open; comparing the path catches
    // an atomic replacement between the read and the check.
    let after_descriptor = file.metadata().map_err(ioerr)?;
    let after_path = fs::metadata(path).map_err(ioerr)?;
    if data.len() != declared
        || !same_identity(&before, &after_descriptor)
        || !same_identity(&after_descriptor, &after_path)
    {
        return Err("input changed while BEST was reading it; refusing a raced archive".into());
    }
    Ok(data)
}

/// A strict output writer means a candidate cannot allocate or emit beyond its
/// admitted complete archive capacity.  `WriteZero` is classified as a normal
/// candidate omission by the caller, never as a corrupt archive.
struct CappedWriter {
    bytes: Vec<u8>,
    cap: usize,
}

impl CappedWriter {
    fn new(cap: usize) -> Self {
        Self {
            bytes: Vec::with_capacity(cap),
            cap,
        }
    }

    fn into_inner(self) -> Vec<u8> {
        self.bytes
    }
}

impl Write for CappedWriter {
    fn write(&mut self, data: &[u8]) -> io::Result<usize> {
        if data.len() > self.cap.saturating_sub(self.bytes.len()) {
            return Err(io::Error::new(
                io::ErrorKind::WriteZero,
                "whole-archive candidate output exceeded admission",
            ));
        }
        self.bytes.extend_from_slice(data);
        Ok(data.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

fn archive_cap(input_len: usize) -> usize {
    input_len
        .saturating_add(OUTPUT_SLACK)
        .min(external::MAX_PAYLOAD.saturating_add(47))
}

fn is_interruption(error: &str) -> bool {
    error.contains("interrupted") || error == crate::limits::INTERRUPTED_ERROR
}

fn is_resource_omission(error: &str) -> bool {
    error == crate::limits::DEADLINE_ERROR
        || error.contains(crate::limits::DEADLINE_ERROR)
        || error.contains("memory budget")
        || error.starts_with("whole-archive validation memory/resource limit")
        || error.starts_with("memory reservation")
        || error.starts_with("input/profiler buffers exceed --memory")
        || error.starts_with("CIXM6 history, source and candidate buffers exceed --memory")
        || error.starts_with("mixture route needs")
        || error.starts_with("block needs about")
        || error == "whole-archive candidate output exceeded admission"
}

fn native_remaining(started: Instant) -> Option<Duration> {
    NATIVE_WHOLE_ARCHIVE_BUDGET.checked_sub(started.elapsed())
}

struct CompareWriter<'a> {
    expected: &'a [u8],
    offset: usize,
    exact: bool,
}

impl<'a> CompareWriter<'a> {
    fn new(expected: &'a [u8]) -> Self {
        Self {
            expected,
            offset: 0,
            exact: true,
        }
    }
}

impl Write for CompareWriter<'_> {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        let end = self.offset.saturating_add(bytes.len());
        if end > self.expected.len() || self.expected.get(self.offset..end) != Some(bytes) {
            self.exact = false;
        }
        self.offset = end;
        Ok(bytes.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

fn decode_budget(
    memory: usize,
    source_capacity: usize,
    incumbent_capacity: usize,
    archive_capacity: usize,
) -> Result<usize, String> {
    memory
        .checked_sub(source_capacity)
        .and_then(|rest| rest.checked_sub(incumbent_capacity))
        .and_then(|rest| rest.checked_sub(archive_capacity))
        // Both CIXG and CIXB1 decoding now charge their retained buffers and
        // native state against this remainder. A second arbitrary halving
        // would exclude valid model archives that fit the aggregate budget.
        .filter(|rest| *rest >= 128 * 1024)
        .ok_or_else(|| "whole-archive validation memory/resource limit exceeded".into())
}

fn validate(
    archive: &[u8],
    archive_capacity: usize,
    input: &Vec<u8>,
    incumbent_capacity: usize,
    memory: usize,
) -> Result<(), String> {
    let decoder_memory = decode_budget(
        memory,
        input.capacity(),
        incumbent_capacity,
        archive_capacity,
    )?;
    let mut restored = CompareWriter::new(input);
    decode(
        io::Cursor::new(archive),
        &mut restored,
        false,
        false,
        -1,
        decoder_memory,
    )?;
    if !restored.exact || restored.offset != input.len() {
        return Err("whole-archive candidate failed exact reconstruction".into());
    }
    Ok(())
}

fn consider(
    winner: &mut Vec<u8>,
    winner_name: &mut String,
    name: &str,
    archive: Vec<u8>,
    input: &Vec<u8>,
    memory: usize,
) -> Result<bool, String> {
    validate(
        &archive,
        archive.capacity(),
        input,
        winner.capacity(),
        memory,
    )?;
    if archive.len() < winner.len() {
        *winner = archive;
        *winner_name = name.into();
        Ok(true)
    } else {
        Ok(false)
    }
}

fn external_validation_admitted(
    descriptor: &external::CandidateDescriptor,
    source_capacity: usize,
    incumbent_capacity: usize,
    archive_capacity: usize,
    input_len: usize,
    memory: usize,
) -> Result<(), String> {
    let available = memory
        .checked_sub(source_capacity)
        .and_then(|rest| rest.checked_sub(incumbent_capacity))
        .and_then(|rest| rest.checked_sub(archive_capacity))
        .ok_or("whole-archive validation memory/resource limit exceeded")?;
    let required = descriptor.decoder_peak_bytes(input_len)?;
    if required > available {
        return Err(format!(
            "whole-archive validation memory/resource limit exceeded: {} needs {required} bytes, available {available}",
            descriptor.id
        ));
    }
    Ok(())
}

/// Select a complete archive.  The source is read once before candidate work;
/// candidate execution is serial because native CIXG2 may use `--threads` and
/// backend libraries have coarse cancellation points.
pub(super) fn select(o: &Opt) -> Result<SelectedArchive, String> {
    let started = Instant::now();
    let data = read_regular_once(&o.input)?;
    check_interrupted()?;
    let cap = archive_cap(data.len());
    let fallback_available = o
        .memory
        .checked_sub(data.capacity())
        .and_then(|rest| rest.checked_sub(cap))
        .ok_or("whole-archive BEST cannot admit source and raw fallback")?;
    if fallback_available < NATIVE_MINIMUM {
        return Err(format!(
            "whole-archive BEST requires at least {} bytes of --memory for this input; using bounded CIXG streaming",
            data.capacity().saturating_add(cap).saturating_add(NATIVE_MINIMUM)
        ));
    }

    // Establish the raw fallback through the same bounded writer used for
    // every native trial.  No helper may materialize an uncharged Vec here.
    let mut raw_output = CappedWriter::new(cap);
    encode_with_strategy(
        io::Cursor::new(data.as_slice()),
        &mut raw_output,
        MAX_BLOCK,
        9,
        Some("raw"),
        "hybrid",
        false,
        "cixg2",
        -1,
        None,
        fallback_available,
        o.threads,
        false,
        false,
        &o.parallelism,
    )?;
    let mut winner = raw_output.into_inner();
    validate(&winner, winner.capacity(), &data, 0, o.memory)?;
    let mut winner_name = "cixg2:raw-fallback".to_string();
    let mut evaluated = 1usize;
    let mut omitted = Vec::new();

    let native_memory = o
        .memory
        .checked_sub(data.capacity())
        .and_then(|rest| rest.checked_sub(winner.capacity()))
        .and_then(|rest| rest.checked_sub(cap));
    if native_memory.is_none_or(|available| available < NATIVE_MINIMUM) {
        omitted.push("cixg2:native-auto (insufficient aggregate memory after raw fallback)".into());
    } else {
        let native_deadline =
            crate::limits::DeadlineGuard::new(native_remaining(started).unwrap_or(Duration::ZERO));
        let mut native_output = CappedWriter::new(cap);
        let native = encode_with_strategy(
            io::Cursor::new(data.as_slice()),
            &mut native_output,
            MAX_BLOCK,
            9,
            None,
            "hybrid",
            false,
            "cixg2",
            -1,
            None,
            native_memory.unwrap(),
            o.threads,
            o.explain,
            o.verbose,
            &o.parallelism,
        );
        drop(native_deadline);
        match native {
            Ok(()) => {
                evaluated += 1;
                match consider(
                    &mut winner,
                    &mut winner_name,
                    "cixg2:native-auto",
                    native_output.into_inner(),
                    &data,
                    o.memory,
                ) {
                    Ok(_) => {}
                    Err(error) if is_resource_omission(&error) => {
                        omitted.push(format!("cixg2:native-auto ({error})"));
                    }
                    Err(error) => return Err(error),
                }
            }
            Err(error) if is_interruption(&error) => return Err(error),
            Err(error) if is_resource_omission(&error) => {
                // The admitted output buffer belongs to the failed native trial,
                // not to the incumbent.  Release it before allocating any
                // backend payload so a failed trial cannot weaken the aggregate
                // memory bound for subsequent candidates.
                drop(native_output);
                omitted.push(format!("cixg2:native-auto ({error})"));
            }
            Err(error) => return Err(error),
        }
    }

    // CIXM6 remains an explicit production format.  Its whole-package
    // automatic comparison is experimental until matched qualification covers
    // its persistent-history trade-offs, so ordinary BEST reports the gap.
    omitted.push("cixm6:native-auto (experimental package not promoted)".into());

    // Registry order is deterministic.  Every descriptor represents a full
    // CIXB1 archive, including all backend framing and configuration cost.
    for descriptor in external::best_candidates() {
        check_interrupted()?;
        let available = o
            .memory
            .saturating_sub(data.capacity())
            .saturating_sub(winner.capacity());
        if let Err(omission) = descriptor.admit(data.len(), available) {
            omitted.push(format!("{} ({})", descriptor.id, omission.reason));
            continue;
        }
        match descriptor.full_archive_encode(&data) {
            Ok(archive) => {
                evaluated += 1;
                if o.explain || o.verbose {
                    eprintln!(
                        "cix: packaging_candidate={} backend={} version={} archive_bytes={}",
                        descriptor.id,
                        descriptor.backend,
                        external::backend_version(descriptor.backend)?,
                        archive.len()
                    );
                }
                match external_validation_admitted(
                    descriptor,
                    data.capacity(),
                    winner.capacity(),
                    archive.capacity(),
                    data.len(),
                    o.memory,
                ) {
                    Ok(()) => {}
                    Err(error) if is_resource_omission(&error) => {
                        omitted.push(format!("{} ({error})", descriptor.id));
                        continue;
                    }
                    Err(error) => return Err(error),
                }
                match consider(
                    &mut winner,
                    &mut winner_name,
                    descriptor.id,
                    archive,
                    &data,
                    o.memory,
                ) {
                    Ok(_) => {}
                    Err(error) if is_resource_omission(&error) => {
                        omitted.push(format!("{} ({error})", descriptor.id));
                    }
                    Err(error) => return Err(error),
                }
            }
            Err(error) if is_interruption(&error) => return Err(error),
            // Only an explicitly recognised resource/deadline condition is
            // omittable. ABI/configuration/codec failures are correctness
            // failures, never a reason to claim BEST completed.
            Err(error) if is_resource_omission(&error) => {
                omitted.push(format!("{} ({error})", descriptor.id));
            }
            Err(error) => return Err(error),
        }
    }
    validate(&winner, winner.capacity(), &data, 0, o.memory)?;
    Ok(SelectedArchive {
        archive: winner,
        selected: winner_name,
        evaluated,
        omitted,
        elapsed: started.elapsed(),
    })
}

pub(super) fn encode<W: Write>(o: &Opt, mut dst: W) -> Result<(), String> {
    let selected = select(o)?;
    dst.write_all(&selected.archive).map_err(ioerr)?;
    dst.flush().map_err(ioerr)?;
    if o.explain || o.verbose || !selected.omitted.is_empty() {
        eprintln!(
            "cix: effort=best whole_archive=yes selected={} archive_bytes={} candidates_evaluated={} search_seconds={:.3} native_search_budget_seconds={} external_one_shot_deadline=not_preemptible omitted={}",
            selected.selected,
            selected.archive.len(),
            selected.evaluated,
            selected.elapsed.as_secs_f64(),
            NATIVE_WHOLE_ARCHIVE_BUDGET.as_secs(),
            if selected.omitted.is_empty() { "none".to_string() } else { selected.omitted.join(",") },
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validation_uses_the_charged_aggregate_remainder() {
        assert_eq!(
            decode_budget(512 << 20, 1 << 20, 2 << 20, 3 << 20).unwrap(),
            506 << 20
        );
        assert!(decode_budget(5 << 20, 1 << 20, 2 << 20, 3 << 20).is_err());
    }

    #[test]
    fn validation_accepts_a_large_native_mixer_that_fits_the_budget() {
        use sha2::{Digest, Sha256};
        let data = vec![b'x'; MAX_BLOCK as usize];
        let cap = archive_cap(data.len());
        let mut output = CappedWriter::new(cap);
        // Materialize this bounded model directly: a debug selector can
        // legitimately time out the trial and choose raw, which would not
        // exercise the decoder's large-model admission being tested.
        let payload = super::super::fixedmix::encode_with_history_eta(&data, &[], 6).unwrap();
        let hash: [u8; 32] = Sha256::digest(&data).into();
        output.write_all(super::super::MAGIC_V2).unwrap();
        output.write_all(&MAX_BLOCK.to_le_bytes()).unwrap();
        output.write_all(&0u32.to_le_bytes()).unwrap();
        super::super::put_frame(
            &mut output,
            9,
            data.len() as u32,
            payload.len() as u32,
            &hash,
        )
        .unwrap();
        output.write_all(&payload).unwrap();
        super::super::put_frame(&mut output, 255, 0, 0, &hash).unwrap();
        let archive = output.into_inner();
        assert_eq!(archive[13], 9, "fixture actually uses the mixer");
        validate(&archive, archive.capacity(), &data, 1 << 20, 512 << 20).unwrap();
    }
}
