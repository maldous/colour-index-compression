//! Bounded whole-input archive selection.
//!
//! This is deliberately a complete-input planner (maximum 128 MiB), not a
//! streaming selector.  It never derives a route from a filename, environment,
//! benchmark identity, or cache.  Reservations are declared buffers/model
//! state, not measured process RSS; an outer supervisor remains responsible
//! for hard RSS and filesystem enforcement.

use super::{
    backend_provider::{
        BackendProvider, BackendRequest, BackendVariant, PaqLevel, TrustedBackendPaths,
    },
    catalogue::{self, Candidate, Recipe},
    containers,
    dispatch::{FullEngine, OperationLimits},
    jxl_provider::JxlProvider,
    mixed_selection, native_portfolio,
    spatial_provider::SpatialProvider,
};
use crate::paq_bridge::PaqVariant;
use std::{
    path::PathBuf,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
    time::Instant,
};

pub const MAX_WHOLE_INPUT: usize = 128 << 20;
const MIB: usize = 1 << 20;
const PAQ_BASE: usize = 4_500_000_000;
const PAQ_9L_BASE: usize = 5_000_000_000;
const NATIVE_BASE: usize = 8_000_000_000;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SelectionProfile {
    Fast,
    Default,
    Best,
}

#[derive(Clone, Debug)]
pub struct SelectionLimits {
    pub memory_bytes: usize,
    pub workers: usize,
    pub temporary_bytes: usize,
    pub output_bytes: usize,
    pub intermediate_bytes: usize,
    pub deadline: Option<Instant>,
    pub cancellation: Option<Arc<AtomicBool>>,
}

#[derive(Clone, Debug)]
pub struct ProviderConfig {
    pub backends: TrustedBackendPaths,
    /// An absolute installed bridge path.  It is loaded afresh per trial;
    /// `JxlProvider` itself is intentionally not shared across threads.
    pub jxl_bridge: Option<PathBuf>,
    pub spatial_bridge: Option<PathBuf>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum TrialStatus {
    Completed,
    BudgetOmitted,
    ProfileOmitted,
    Failed,
    Selected,
}
#[derive(Clone, Debug)]
pub struct Trial {
    pub id: String,
    pub priority: usize,
    pub status: TrialStatus,
    pub reason: Option<String>,
    pub archive_bytes: Option<usize>,
    /// Inner searches retain their own units: native complete archives and
    /// mixed-region payloads must not be confused in reporting.
    pub details: TrialDetails,
}
#[derive(Clone, Debug, Default)]
pub enum TrialDetails {
    #[default]
    None,
    Native(Vec<native_portfolio::NativePortfolioCandidate>),
    Mixed(mixed_selection::MixedDiagnostics),
}
#[derive(Clone, Debug)]
pub struct CandidateExecution {
    pub archive: Vec<u8>,
    pub details: TrialDetails,
}
impl CandidateExecution {
    fn bare(archive: Vec<u8>) -> Self {
        Self {
            archive,
            details: TrialDetails::None,
        }
    }
}
#[derive(Clone, Debug)]
pub struct SelectionReport {
    pub profile: SelectionProfile,
    pub input_bytes: usize,
    pub trials: Vec<Trial>,
    pub peak_reserved_memory: usize,
    pub peak_reserved_workers: usize,
    pub peak_reserved_temporary: usize,
    pub selected: String,
}
#[derive(Clone, Debug)]
pub struct SelectionResult {
    pub archive: Vec<u8>,
    pub report: SelectionReport,
}

#[derive(Clone, Debug)]
enum PlanKind {
    Raw,
    Native {
        profile: SelectionProfile,
    },
    Paq {
        variant: PaqVariant,
        level: u8,
        lstm: bool,
    },
    Specialist(Candidate),
    Mixed {
        profile: SelectionProfile,
    },
}
#[derive(Clone, Debug)]
pub struct Plan {
    pub id: String,
    priority: usize,
    kind: PlanKind,
    memory: usize,
    workers: usize,
    temporary: usize,
}

fn checked_add(a: usize, b: usize) -> Result<usize, String> {
    a.checked_add(b)
        .ok_or_else(|| "selection reservation overflow".into())
}
fn scaled(base: usize, n: usize) -> Result<usize, String> {
    checked_add(
        base,
        n.checked_mul(8).ok_or("selection reservation overflow")?,
    )
}
fn temporary(n: usize, output: usize) -> Result<usize, String> {
    checked_add(n, output)
}
fn cancelled(limits: &SelectionLimits) -> bool {
    limits
        .cancellation
        .as_ref()
        .is_some_and(|v| v.load(Ordering::Acquire))
        || limits.deadline.is_some_and(|d| Instant::now() >= d)
}

fn specialist_is_paq(candidate: &Candidate) -> bool {
    match candidate.recipe {
        Recipe::Geometry { .. }
        | Recipe::Hydrogen
        | Recipe::GroupedGrid
        | Recipe::BoundedGrid { .. } => true,
        Recipe::RecordConstraints { paq, .. } | Recipe::Address { paq, .. } => paq,
        _ => false,
    }
}

fn plans(
    data: &[u8],
    profile: SelectionProfile,
    limits: &SelectionLimits,
    trials: &mut Vec<Trial>,
) -> Result<Vec<Plan>, String> {
    let n = data.len();
    let temp = temporary(n, limits.output_bytes)?;
    let mut out = Vec::new();
    let mut next_priority = 0usize;
    let raw_memory = checked_add(
        n.checked_mul(3).ok_or("raw reservation overflow")?,
        32 * MIB,
    )?;
    out.push(Plan {
        id: "raw".into(),
        priority: next_priority,
        kind: PlanKind::Raw,
        memory: raw_memory,
        workers: 1,
        temporary: temp,
    });
    next_priority += 1;
    let native_budget = limits
        .memory_bytes
        .saturating_sub(checked_add(
            n.checked_mul(12).ok_or("native reservation overflow")?,
            256 * MIB,
        )?)
        .max(64 * MIB)
        .min(NATIVE_BASE);
    out.push(Plan {
        id: "native".into(),
        priority: next_priority,
        kind: PlanKind::Native { profile },
        memory: checked_add(
            native_budget,
            checked_add(
                n.checked_mul(12).ok_or("native reservation overflow")?,
                128 * MIB,
            )?,
        )?,
        workers: limits.workers,
        temporary: temp,
    });
    next_priority += 1;
    if profile == SelectionProfile::Best {
        for (id, variant, level, lstm, base) in [
            ("paq-v216-8", PaqVariant::V216, 8, false, PAQ_BASE),
            ("paq-v215-8", PaqVariant::V215, 8, false, PAQ_BASE),
            ("paq-v215-9L", PaqVariant::V215, 9, true, PAQ_9L_BASE),
        ] {
            out.push(Plan {
                id: id.into(),
                priority: next_priority,
                kind: PlanKind::Paq {
                    variant,
                    level,
                    lstm,
                },
                memory: scaled(base, n)?,
                workers: 1,
                temporary: checked_add(
                    n,
                    limits
                        .output_bytes
                        .checked_mul(2)
                        .ok_or("selection reservation overflow")?,
                )?,
            });
            next_priority += 1;
        }
    }
    if profile == SelectionProfile::Fast {
        return Ok(out);
    }
    for candidate in catalogue::catalog(data)?.candidates {
        let priority = next_priority;
        next_priority += 1;
        if profile == SelectionProfile::Default && specialist_is_paq(&candidate) {
            trials.push(Trial {
                id: candidate.id,
                priority,
                status: TrialStatus::ProfileOmitted,
                reason: Some("DEFAULT omits PAQ-backed specialist trials".into()),
                archive_bytes: None,
                details: TrialDetails::None,
            });
            continue;
        }
        out.push(Plan {
            id: candidate.id.clone(),
            priority,
            memory: candidate.memory_bytes,
            workers: 1,
            temporary: checked_add(limits.intermediate_bytes, limits.output_bytes)?,
            kind: PlanKind::Specialist(candidate),
        });
    }
    out.push(Plan {
        id: "heterogeneous-cixh1-v1".into(),
        priority: next_priority,
        kind: PlanKind::Mixed { profile },
        memory: 5 << 30,
        workers: 1,
        temporary: checked_add(limits.intermediate_bytes, limits.output_bytes)?,
    });
    Ok(out)
}

pub trait CandidateExecutor: Clone + Send + Sync + 'static {
    fn run(&self, plan: &Plan, data: &[u8], limits: &SelectionLimits) -> Result<Vec<u8>, String>;
    fn run_detailed(
        &self,
        plan: &Plan,
        data: &[u8],
        limits: &SelectionLimits,
    ) -> Result<CandidateExecution, String> {
        self.run(plan, data, limits).map(CandidateExecution::bare)
    }
}
#[derive(Clone, Debug)]
pub struct NativeExecutor {
    pub providers: ProviderConfig,
}
impl NativeExecutor {
    fn engine(
        &self,
        output: usize,
        need_jxl: bool,
        need_spatial: bool,
    ) -> Result<FullEngine, String> {
        let images = match self.providers.jxl_bridge.as_ref().filter(|_| need_jxl) {
            Some(path) => {
                Some(JxlProvider::load_package_bridge(path, output).map_err(|e| e.to_string())?)
            }
            None => None,
        };
        let spatial = match self
            .providers
            .spatial_bridge
            .as_ref()
            .filter(|_| need_spatial)
        {
            Some(path) => Some(
                SpatialProvider::load_package_bridge(path, output).map_err(|e| e.to_string())?,
            ),
            None => None,
        };
        Ok(FullEngine {
            backends: BackendProvider {
                paths: self.providers.backends.clone(),
            },
            images,
            spatial,
        })
    }
}
impl CandidateExecutor for NativeExecutor {
    fn run(&self, plan: &Plan, data: &[u8], limits: &SelectionLimits) -> Result<Vec<u8>, String> {
        self.run_detailed(plan, data, limits)
            .map(|result| result.archive)
    }
    fn run_detailed(
        &self,
        plan: &Plan,
        data: &[u8],
        limits: &SelectionLimits,
    ) -> Result<CandidateExecution, String> {
        if cancelled(limits) {
            return Err("selection cancelled or deadline exceeded".into());
        }
        match &plan.kind {
            PlanKind::Mixed { profile } => {
                return mixed_selection::encode(
                    &self.engine(limits.output_bytes, true, true)?,
                    data,
                    *profile,
                    &OperationLimits {
                        memory_bytes: plan.memory,
                        output_bytes: limits.output_bytes,
                        intermediate_bytes: limits.intermediate_bytes,
                        deadline: limits.deadline,
                        cancellation: limits.cancellation.clone(),
                    },
                )
                .map(|result| CandidateExecution {
                    archive: result.archive,
                    details: TrialDetails::Mixed(result.diagnostics),
                })
            }
            PlanKind::Raw => containers::encode_raw(data, limits.output_bytes),
            PlanKind::Native { profile } => {
                return native_portfolio::select(
                    data,
                    &native_portfolio::NativePortfolioOptions {
                        profile: match profile {
                            SelectionProfile::Fast => {
                                native_portfolio::NativePortfolioProfile::Fast
                            }
                            SelectionProfile::Default => {
                                native_portfolio::NativePortfolioProfile::Default
                            }
                            SelectionProfile::Best => {
                                native_portfolio::NativePortfolioProfile::Best
                            }
                        },
                        output_bytes: limits.output_bytes,
                        memory_bytes: plan.memory,
                        workers: plan.workers,
                        deadline: limits.deadline,
                        cancellation: limits.cancellation.clone(),
                    },
                )
                .map(|result| CandidateExecution {
                    archive: result.archive,
                    details: TrialDetails::Native(result.candidates),
                });
            }
            PlanKind::Paq {
                variant,
                level,
                lstm,
            } => {
                let provider = BackendProvider {
                    paths: self.providers.backends.clone(),
                };
                let member = provider.encode(
                    data,
                    &BackendRequest {
                        variant: BackendVariant::Paq {
                            variant: *variant,
                            level: PaqLevel {
                                number: *level,
                                lstm: *lstm,
                            },
                            lstm_layers: 1,
                            joint_discount_mode: None,
                        },
                        output_limit: limits.output_bytes,
                        memory_limit: plan.memory,
                        deadline: limits.deadline,
                        cancellation: limits.cancellation.clone(),
                    },
                )?;
                containers::wrap_paq(&member, *variant, limits.output_bytes)
            }
            PlanKind::Specialist(candidate) => self
                .engine(
                    limits.output_bytes,
                    matches!(
                        candidate.recipe,
                        Recipe::Spatial { .. }
                            | Recipe::Volume { .. }
                            | Recipe::VolumeSharedIdentity { .. }
                    ),
                    matches!(candidate.recipe, Recipe::SpatialAlternative { .. }),
                )?
                .encode_candidate(
                    candidate,
                    data,
                    &OperationLimits {
                        memory_bytes: plan.memory,
                        output_bytes: limits.output_bytes,
                        intermediate_bytes: limits.intermediate_bytes,
                        deadline: limits.deadline,
                        cancellation: limits.cancellation.clone(),
                    },
                ),
        }
        .map(CandidateExecution::bare)
    }
}

/// Run a deterministic first-fit schedule.  Equal-size frames retain their
/// original priority even if a later worker returns first.
pub fn select_whole_input<E: CandidateExecutor>(
    data: &[u8],
    profile: SelectionProfile,
    limits: SelectionLimits,
    executor: E,
) -> Result<SelectionResult, String> {
    if data.len() > MAX_WHOLE_INPUT
        || limits.workers == 0
        || limits.memory_bytes == 0
        || limits.temporary_bytes == 0
    {
        return Err("whole-input selection exceeds declared admission".into());
    }
    if cancelled(&limits) {
        return Err("whole-input selection cancelled or deadline exceeded".into());
    }
    let mut trials = Vec::new();
    let queue = plans(data, profile, &limits, &mut trials)?;
    let mut pending: Vec<(usize, Plan)> = queue
        .into_iter()
        .map(|plan| (plan.priority, plan))
        .collect();
    let mut incumbent: Option<(usize, Vec<u8>)> = None;
    let mut peak = (data.len(), 0usize, 0usize);
    let mut aborted = false;
    let accept = |priority: usize,
                  plan: Plan,
                  result: Result<CandidateExecution, String>,
                  incumbent: &mut Option<(usize, Vec<u8>)>,
                  trials: &mut Vec<Trial>| {
        if cancelled(&limits) {
            trials.push(Trial {
                id: plan.id,
                priority,
                status: TrialStatus::BudgetOmitted,
                reason: Some("deadline or cancellation before result acceptance".into()),
                archive_bytes: None,
                details: TrialDetails::None,
            });
            return;
        }
        match result {
            Ok(CandidateExecution {
                archive: frame,
                details,
            }) if frame.len() <= limits.output_bytes && frame.capacity() <= limits.output_bytes => {
                let bytes = frame.len();
                if incumbent
                    .as_ref()
                    .is_none_or(|(old, prior)| (bytes, priority) < (prior.len(), *old))
                {
                    *incumbent = Some((priority, frame));
                }
                trials.push(Trial {
                    id: plan.id,
                    priority,
                    status: TrialStatus::Completed,
                    reason: None,
                    archive_bytes: Some(bytes),
                    details,
                });
            }
            Ok(_) => trials.push(Trial {
                id: plan.id,
                priority,
                status: TrialStatus::Failed,
                reason: Some("candidate returned frame beyond declared output reservation".into()),
                archive_bytes: None,
                details: TrialDetails::None,
            }),
            Err(reason) => trials.push(Trial {
                id: plan.id,
                priority,
                status: TrialStatus::Failed,
                reason: Some(reason),
                archive_bytes: None,
                details: TrialDetails::None,
            }),
        }
    };
    // Raw runs by itself before any concurrent work, matching the historical policy.
    if let Some((priority, raw)) = pending.first().cloned() {
        pending.remove(0);
        if raw.id != "raw" {
            return Err("raw candidate priority invariant".into());
        }
        let raw_memory = checked_add(data.len(), checked_add(raw.memory, limits.output_bytes)?)?;
        if raw_memory > limits.memory_bytes
            || raw.workers > limits.workers
            || raw.temporary > limits.temporary_bytes
        {
            trials.push(Trial {
                id: raw.id,
                priority,
                status: TrialStatus::BudgetOmitted,
                reason: Some("raw memory/workers/temporary admission".into()),
                archive_bytes: None,
                details: TrialDetails::None,
            });
        } else {
            peak.0 = raw_memory;
            peak.1 = raw.workers;
            peak.2 = raw.temporary;
            let raw_result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                executor.run_detailed(&raw, data, &limits)
            }))
            .unwrap_or_else(|_| Err("candidate worker panicked".into()));
            accept(
                priority,
                raw.clone(),
                raw_result,
                &mut incumbent,
                &mut trials,
            );
        }
    }
    std::thread::scope(|scope| -> Result<(), String> {
        use std::sync::mpsc;
        let (sender, receiver) = mpsc::channel();
        let mut running: Vec<(usize, Plan, std::thread::ScopedJoinHandle<'_, ()>)> = Vec::new();
        while !pending.is_empty() || !running.is_empty() {
            if cancelled(&limits) && !pending.is_empty() {
                aborted = true;
                for (priority, plan) in pending.drain(..) {
                    trials.push(Trial {
                        id: plan.id,
                        priority,
                        status: TrialStatus::BudgetOmitted,
                        reason: Some("deadline or cancellation".into()),
                        archive_bytes: None,
                        details: TrialDetails::None,
                    });
                }
            }
            if cancelled(&limits) && running.is_empty() {
                aborted = true;
                break;
            }
            // Admission reserves the fixed output cap for the retained winner,
            // rather than Vec capacity.  That makes future first-fit decisions
            // independent of allocator growth and completion order.
            let retained = checked_add(
                data.len(),
                if incumbent.is_some() {
                    limits.output_bytes
                } else {
                    0
                },
            )?;
            let used_memory = running.iter().try_fold(retained, |total, (_, plan, _)| {
                checked_add(total, checked_add(plan.memory, limits.output_bytes)?)
            })?;
            let used_workers = running.iter().try_fold(0usize, |total, (_, plan, _)| {
                checked_add(total, plan.workers)
            })?;
            let used_temp = running.iter().try_fold(0usize, |total, (_, plan, _)| {
                checked_add(total, plan.temporary)
            })?;
            let mut started = false;
            let mut index = 0;
            while index < pending.len() {
                let (_, plan) = &pending[index];
                let memory =
                    checked_add(used_memory, checked_add(plan.memory, limits.output_bytes)?)?;
                let workers = checked_add(used_workers, plan.workers)?;
                let temp = checked_add(used_temp, plan.temporary)?;
                if memory <= limits.memory_bytes
                    && workers <= limits.workers
                    && temp <= limits.temporary_bytes
                {
                    let (priority, plan) = pending.remove(index);
                    let worker = executor.clone();
                    let job_limits = limits.clone();
                    let tx = sender.clone();
                    peak.0 = peak.0.max(memory);
                    peak.1 = peak.1.max(workers);
                    peak.2 = peak.2.max(temp);
                    let running_plan = plan.clone();
                    let handle = scope.spawn(move || {
                        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                            worker.run_detailed(&plan, data, &job_limits)
                        }))
                        .unwrap_or_else(|_| Err("candidate worker panicked".into()));
                        let _ = tx.send((priority, plan, result));
                    });
                    running.push((priority, running_plan, handle));
                    started = true;
                    break;
                }
                index += 1;
            }
            if started {
                continue;
            }
            if running.is_empty() {
                let (priority, plan) = pending.remove(0);
                trials.push(Trial {
                    id: plan.id,
                    priority,
                    status: TrialStatus::BudgetOmitted,
                    reason: Some("memory/workers/temporary first-fit admission".into()),
                    archive_bytes: None,
                    details: TrialDetails::None,
                });
                continue;
            }
            let (priority, plan, result) = receiver
                .recv()
                .map_err(|_| "candidate scheduler channel closed")?;
            if let Some(at) = running.iter().position(|(p, _, _)| *p == priority) {
                let (_, _, handle) = running.swap_remove(at);
                handle.join().map_err(|_| "candidate worker panicked")?;
            }
            accept(priority, plan, result, &mut incumbent, &mut trials);
        }
        Ok(())
    })?;
    if aborted || cancelled(&limits) {
        return Err("whole-input selection cancelled or deadline exceeded".into());
    }
    let (winner_priority, archive) = incumbent.ok_or("no complete candidate archive")?;
    let selected = trials
        .iter()
        .find(|trial| trial.priority == winner_priority)
        .ok_or("missing completed trial")?
        .id
        .clone();
    for trial in &mut trials {
        if trial.priority == winner_priority {
            trial.status = TrialStatus::Selected;
        }
    }
    trials.sort_by_key(|trial| trial.priority);
    Ok(SelectionResult {
        archive,
        report: SelectionReport {
            profile,
            input_bytes: data.len(),
            trials,
            peak_reserved_memory: peak.0,
            peak_reserved_workers: peak.1,
            peak_reserved_temporary: peak.2,
            selected,
        },
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    #[derive(Clone)]
    struct Fake {
        live: Arc<AtomicUsize>,
        peak: Arc<AtomicUsize>,
    }
    impl CandidateExecutor for Fake {
        fn run(&self, plan: &Plan, _: &[u8], _: &SelectionLimits) -> Result<Vec<u8>, String> {
            let live = self.live.fetch_add(1, Ordering::SeqCst) + 1;
            self.peak.fetch_max(live, Ordering::SeqCst);
            // Reverse generic completion pressure cannot alter priority ties.
            if matches!(plan.kind, PlanKind::Paq { .. }) {
                std::thread::sleep(std::time::Duration::from_millis(5));
            }
            self.live.fetch_sub(1, Ordering::SeqCst);
            Ok(vec![0; 7])
        }
    }
    fn limits() -> SelectionLimits {
        SelectionLimits {
            memory_bytes: 11_000_000_000,
            workers: 2,
            temporary_bytes: 512 << 20,
            output_bytes: 64 << 20,
            intermediate_bytes: 64 << 20,
            deadline: None,
            cancellation: None,
        }
    }
    #[test]
    fn first_priority_wins_equal_complete_frames_and_generic_trials_overlap() {
        let live = Arc::new(AtomicUsize::new(0));
        let peak = Arc::new(AtomicUsize::new(0));
        let result = select_whole_input(
            b"selector",
            SelectionProfile::Best,
            limits(),
            Fake {
                live,
                peak: peak.clone(),
            },
        )
        .unwrap();
        assert_eq!(result.report.selected, "raw");
        assert!(peak.load(Ordering::SeqCst) >= 2);
        assert!(result.report.peak_reserved_workers <= 2);
        assert!(result.report.peak_reserved_memory <= 11_000_000_000);
        assert!(result.report.peak_reserved_temporary <= 512 << 20);
        // Frames are seven bytes here, yet admission reserves the fixed output
        // cap, so changing a worker's Vec allocation cannot change scheduling.
        assert!(result.report.peak_reserved_memory >= (64 << 20));
    }
    #[test]
    fn nested_diagnostics_survive_outer_selection() {
        #[derive(Clone)]
        struct Detailed;
        impl CandidateExecutor for Detailed {
            fn run(&self, _: &Plan, _: &[u8], _: &SelectionLimits) -> Result<Vec<u8>, String> {
                unreachable!("scheduler must preserve detailed results")
            }
            fn run_detailed(
                &self,
                plan: &Plan,
                _: &[u8],
                _: &SelectionLimits,
            ) -> Result<CandidateExecution, String> {
                Ok(CandidateExecution {
                    archive: vec![0; if plan.id == "native" { 1 } else { 7 }],
                    details: TrialDetails::Native(vec![
                        native_portfolio::NativePortfolioCandidate {
                            id: "inner-size-trial".into(),
                            status: native_portfolio::NativePortfolioStatus::Completed,
                            archive_bytes: Some(1),
                            reason: None,
                        },
                    ]),
                })
            }
        }
        let result =
            select_whole_input(b"diagnostics", SelectionProfile::Fast, limits(), Detailed).unwrap();
        assert_eq!(result.report.selected, "native");
        for trial in &result.report.trials {
            let TrialDetails::Native(inner) = &trial.details else {
                panic!("inner diagnostics lost")
            };
            assert_eq!(inner[0].id, "inner-size-trial");
        }
    }

    #[test]
    fn default_marks_paq_specialists_as_profile_omitted() {
        // A validated grid provides PAQ-only specialist recipes without using a codec.
        let mut grid = vec![0u8; 28 * 3];
        grid[8..12].copy_from_slice(&2i32.to_le_bytes());
        grid[12..16].copy_from_slice(&0i32.to_le_bytes());
        grid[16..20].copy_from_slice(&1i32.to_le_bytes());
        grid[20..24].copy_from_slice(&1i32.to_le_bytes());
        grid[24..28].copy_from_slice(&28i32.to_le_bytes());
        let live = Arc::new(AtomicUsize::new(0));
        let peak = Arc::new(AtomicUsize::new(0));
        let result = select_whole_input(
            &grid,
            SelectionProfile::Default,
            limits(),
            Fake { live, peak },
        )
        .unwrap();
        assert!(result
            .report
            .trials
            .iter()
            .any(|trial| trial.status == TrialStatus::ProfileOmitted));
    }
}

#[cfg(test)]
mod cancellation_regressions {
    use super::*;

    #[derive(Clone)]
    struct Panic;
    impl CandidateExecutor for Panic {
        fn run(&self, _: &Plan, _: &[u8], _: &SelectionLimits) -> Result<Vec<u8>, String> {
            panic!("test executor panic")
        }
    }
    #[derive(Clone)]
    struct CancelAfterRaw {
        token: Arc<AtomicBool>,
    }
    impl CandidateExecutor for CancelAfterRaw {
        fn run(&self, plan: &Plan, _: &[u8], _: &SelectionLimits) -> Result<Vec<u8>, String> {
            if plan.id == "raw" {
                self.token.store(true, Ordering::Release);
            }
            Ok(vec![1])
        }
    }
    fn limits(token: Option<Arc<AtomicBool>>) -> SelectionLimits {
        SelectionLimits {
            memory_bytes: 11_000_000_000,
            workers: 2,
            temporary_bytes: 512 << 20,
            output_bytes: 64 << 20,
            intermediate_bytes: 64 << 20,
            deadline: None,
            cancellation: token,
        }
    }
    #[test]
    fn pre_cancel_is_terminal() {
        let token = Arc::new(AtomicBool::new(true));
        assert!(
            select_whole_input(b"x", SelectionProfile::Fast, limits(Some(token)), Panic).is_err()
        );
    }
    #[test]
    fn cancellation_after_raw_never_returns_archive() {
        let token = Arc::new(AtomicBool::new(false));
        assert!(select_whole_input(
            b"x",
            SelectionProfile::Fast,
            limits(Some(token.clone())),
            CancelAfterRaw { token }
        )
        .is_err());
    }
    #[test]
    fn panicking_worker_is_recorded_without_scheduler_hang() {
        assert!(select_whole_input(b"x", SelectionProfile::Fast, limits(None), Panic).is_err());
    }
}
