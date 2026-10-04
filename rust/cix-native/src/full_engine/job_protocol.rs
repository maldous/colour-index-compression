//! Versioned, same-executable full-engine job protocol.
//!
//! Control records travel on a small bounded binary wire. Input/archive bytes
//! never share that wire: the embedding supplies `Read`/`Write` transports for
//! data, so this library never opens paths or executes arbitrary commands.
//! Cancellation is cooperative: it is checked between protocol stages; an
//! in-process codec call cannot be force-preempted.

use super::{
    dispatch::{FullEngine, OperationLimits},
    io::{self, DecodePath},
    selection::{
        self, CandidateExecutor, SelectionLimits, SelectionProfile, TrialDetails, TrialStatus,
    },
};
use std::{
    io::{self as stdio, Read, Write},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
    time::{Duration, Instant},
};

pub const JOB_PROTOCOL_VERSION: u16 = 1;
pub const MAX_CONTROL_RECORD_BYTES: usize = 8 << 20;
pub const MAX_CONTROL_TEXT_BYTES: usize = 16 << 10;
pub const MAX_PROGRESS_STAGES: usize = 16;
const MAGIC: [u8; 4] = *b"CJB1";
const HEADER: usize = 4 + 2 + 1 + 4;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum JobOperation {
    SelectWholeInput,
    DecodeArchive,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum JobProfile {
    Fast,
    Default,
    Best,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum JobStage {
    Accepted,
    InputRead,
    SelectionStarted,
    SelectionFinished,
    DecodeStarted,
    DecodeFinished,
    OutputWritten,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JobLimits {
    pub input_bytes: usize,
    pub archive_bytes: usize,
    pub output_bytes: usize,
    pub memory_bytes: usize,
    pub intermediate_bytes: usize,
    pub temporary_bytes: usize,
    pub workers: usize,
    pub deadline_millis: Option<u64>,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JobRequest {
    pub request_id: u64,
    pub operation: JobOperation,
    pub profile: JobProfile,
    pub limits: JobLimits,
    pub diagnostics: bool,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JobCapability {
    pub protocol_version: u16,
    pub select_whole_input: bool,
    pub decode_archive: bool,
    pub data_transport: String,
    pub cancellation: String,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JobProgress {
    pub request_id: u64,
    pub stage: JobStage,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JobError {
    pub request_id: u64,
    pub code: JobErrorCode,
    pub message: String,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum JobErrorCode {
    InvalidRequest,
    ResourceLimit,
    Cancelled,
    Unsupported,
    Io,
    Execution,
    Protocol,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JobTrial {
    pub id: String,
    pub priority: usize,
    pub status: String,
    pub reason: Option<String>,
    pub archive_bytes: Option<usize>,
    pub nested: Vec<JobDiagnostic>,
    pub nested_omitted: usize,
    pub provider_omissions: Vec<String>,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JobDiagnostic {
    pub kind: String,
    pub id: String,
    pub status: String,
    pub region: Option<usize>,
    pub backend: Option<String>,
    /// `archive` for whole candidates; `payload` for mixed region choices.
    pub bytes_unit: String,
    pub bytes: Option<usize>,
    pub detail: Option<String>,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JobDiscovery {
    pub family: String,
    pub admitted: bool,
    pub available: bool,
    pub reason: String,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JobSelectionReport {
    pub profile: JobProfile,
    pub input_bytes: usize,
    pub discovery: Vec<JobDiscovery>,
    pub trials: Vec<JobTrial>,
    pub peak_reserved_memory: usize,
    pub peak_reserved_workers: usize,
    pub peak_reserved_temporary: usize,
    pub selected: String,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JobResult {
    pub request_id: u64,
    pub operation: JobOperation,
    pub output_bytes: usize,
    pub selection: Option<JobSelectionReport>,
    pub decode_path: Option<String>,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ControlRecord {
    Request(JobRequest),
    Capability(JobCapability),
    Progress(JobProgress),
    Result(JobResult),
    Error(JobError),
    Cancel { request_id: u64 },
}

#[derive(Clone, Default)]
pub struct CancelToken(Arc<AtomicBool>);
impl CancelToken {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn cancel(&self) {
        self.0.store(true, Ordering::Release);
    }
    pub fn is_cancelled(&self) -> bool {
        self.0.load(Ordering::Acquire)
    }
    pub fn as_arc(&self) -> Arc<AtomicBool> {
        self.0.clone()
    }
}

pub fn capabilities() -> JobCapability {
    JobCapability {
        protocol_version: JOB_PROTOCOL_VERSION,
        select_whole_input: true,
        decode_archive: true,
        data_transport: "caller-provided Read/Write; no paths".into(),
        cancellation: "cooperative stage-boundary cancellation; no in-process force-preemption"
            .into(),
    }
}

#[derive(Default)]
struct Buf {
    bytes: Vec<u8>,
    failed: bool,
}
impl Buf {
    fn add(&mut self, value: &[u8]) {
        if self.failed {
            return;
        }
        let Some(next) = self.bytes.len().checked_add(value.len()) else {
            self.failed = true;
            return;
        };
        if next > MAX_CONTROL_RECORD_BYTES || self.bytes.try_reserve_exact(value.len()).is_err() {
            self.failed = true;
            return;
        }
        self.bytes.extend_from_slice(value);
    }
    fn u8(&mut self, n: u8) {
        self.add(&[n])
    }
    fn u16(&mut self, n: u16) {
        self.add(&n.to_be_bytes())
    }
    fn u32(&mut self, n: u32) {
        self.add(&n.to_be_bytes())
    }
    fn u64(&mut self, n: u64) {
        self.add(&n.to_be_bytes())
    }
    fn usize(&mut self, n: usize) -> Result<(), String> {
        self.u64(u64::try_from(n).map_err(|_| "control integer overflow")?);
        Ok(())
    }
    fn text(&mut self, s: &str) -> Result<(), String> {
        if s.len() > MAX_CONTROL_TEXT_BYTES || !s.is_char_boundary(s.len()) {
            return Err("control text exceeds limit".into());
        }
        self.u32(u32::try_from(s.len()).map_err(|_| "control text overflow")?);
        self.add(s.as_bytes());
        Ok(())
    }
    fn opt_usize(&mut self, n: Option<usize>) -> Result<(), String> {
        self.u8(u8::from(n.is_some()));
        if let Some(n) = n {
            self.usize(n)?
        }
        Ok(())
    }
    fn opt_text(&mut self, s: &Option<String>) -> Result<(), String> {
        self.u8(u8::from(s.is_some()));
        if let Some(s) = s {
            self.text(s)?
        }
        Ok(())
    }
}
struct Take<'a> {
    b: &'a [u8],
    p: usize,
}
impl<'a> Take<'a> {
    fn take(&mut self, n: usize) -> Result<&'a [u8], String> {
        let end = self.p.checked_add(n).ok_or("control length overflow")?;
        let out = self.b.get(self.p..end).ok_or("truncated control record")?;
        self.p = end;
        Ok(out)
    }
    fn u8(&mut self) -> Result<u8, String> {
        Ok(self.take(1)?[0])
    }
    fn u16(&mut self) -> Result<u16, String> {
        Ok(u16::from_be_bytes(self.take(2)?.try_into().unwrap()))
    }
    fn u32(&mut self) -> Result<u32, String> {
        Ok(u32::from_be_bytes(self.take(4)?.try_into().unwrap()))
    }
    fn u64(&mut self) -> Result<u64, String> {
        Ok(u64::from_be_bytes(self.take(8)?.try_into().unwrap()))
    }
    fn usize(&mut self) -> Result<usize, String> {
        usize::try_from(self.u64()?).map_err(|_| "control integer overflow".into())
    }
    fn text(&mut self) -> Result<String, String> {
        let n = usize::try_from(self.u32()?).map_err(|_| "control text overflow")?;
        if n > MAX_CONTROL_TEXT_BYTES {
            return Err("control text exceeds limit".into());
        }
        let b = self.take(n)?;
        let s = std::str::from_utf8(b).map_err(|_| "invalid control UTF-8")?;
        Ok(s.into())
    }
    fn opt_usize(&mut self) -> Result<Option<usize>, String> {
        match self.u8()? {
            0 => Ok(None),
            1 => Ok(Some(self.usize()?)),
            _ => Err("invalid control option".into()),
        }
    }
    fn opt_text(&mut self) -> Result<Option<String>, String> {
        match self.u8()? {
            0 => Ok(None),
            1 => Ok(Some(self.text()?)),
            _ => Err("invalid control option".into()),
        }
    }
    fn end(&self) -> Result<(), String> {
        if self.p == self.b.len() {
            Ok(())
        } else {
            Err("trailing control bytes".into())
        }
    }
}
fn op_tag(v: JobOperation) -> u8 {
    match v {
        JobOperation::SelectWholeInput => 1,
        JobOperation::DecodeArchive => 2,
    }
}
fn op(v: u8) -> Result<JobOperation, String> {
    match v {
        1 => Ok(JobOperation::SelectWholeInput),
        2 => Ok(JobOperation::DecodeArchive),
        _ => Err("unknown job operation".into()),
    }
}
fn profile_tag(v: JobProfile) -> u8 {
    match v {
        JobProfile::Fast => 1,
        JobProfile::Default => 2,
        JobProfile::Best => 3,
    }
}
fn profile(v: u8) -> Result<JobProfile, String> {
    match v {
        1 => Ok(JobProfile::Fast),
        2 => Ok(JobProfile::Default),
        3 => Ok(JobProfile::Best),
        _ => Err("unknown job profile".into()),
    }
}
fn put_limits(b: &mut Buf, l: &JobLimits) -> Result<(), String> {
    for n in [
        l.input_bytes,
        l.archive_bytes,
        l.output_bytes,
        l.memory_bytes,
        l.intermediate_bytes,
        l.temporary_bytes,
        l.workers,
    ] {
        b.usize(n)?
    }
    b.u8(u8::from(l.deadline_millis.is_some()));
    if let Some(n) = l.deadline_millis {
        b.u64(n)
    }
    Ok(())
}
fn get_limits(t: &mut Take<'_>) -> Result<JobLimits, String> {
    let x = JobLimits {
        input_bytes: t.usize()?,
        archive_bytes: t.usize()?,
        output_bytes: t.usize()?,
        memory_bytes: t.usize()?,
        intermediate_bytes: t.usize()?,
        temporary_bytes: t.usize()?,
        workers: t.usize()?,
        deadline_millis: match t.u8()? {
            0 => None,
            1 => Some(t.u64()?),
            _ => return Err("invalid deadline option".into()),
        },
    };
    if x.input_bytes == 0
        || x.archive_bytes == 0
        || x.output_bytes == 0
        || x.memory_bytes == 0
        || x.intermediate_bytes == 0
        || x.temporary_bytes == 0
        || x.workers == 0
    {
        return Err("zero job limit".into());
    }
    Ok(x)
}

/// Write one bounded control record. The data transport is intentionally not
/// touched by this function.
pub fn write_control<W: Write>(out: &mut W, record: &ControlRecord) -> Result<(), String> {
    let (mut kind, mut p) = (0u8, Buf::default());
    match record {
        ControlRecord::Request(r) => {
            kind = 1;
            p.u64(r.request_id);
            p.u8(op_tag(r.operation));
            p.u8(profile_tag(r.profile));
            put_limits(&mut p, &r.limits)?;
            p.u8(u8::from(r.diagnostics));
        }
        ControlRecord::Capability(c) => {
            kind = 2;
            p.u16(c.protocol_version);
            p.u8(u8::from(c.select_whole_input));
            p.u8(u8::from(c.decode_archive));
            p.text(&c.data_transport)?;
            p.text(&c.cancellation)?;
        }
        ControlRecord::Progress(x) => {
            kind = 3;
            p.u64(x.request_id);
            p.u8(match x.stage {
                JobStage::Accepted => 1,
                JobStage::InputRead => 2,
                JobStage::SelectionStarted => 3,
                JobStage::SelectionFinished => 4,
                JobStage::DecodeStarted => 5,
                JobStage::DecodeFinished => 6,
                JobStage::OutputWritten => 7,
            });
        }
        ControlRecord::Result(r) => {
            kind = 4;
            p.u64(r.request_id);
            p.u8(op_tag(r.operation));
            p.usize(r.output_bytes)?;
            p.u8(u8::from(r.selection.is_some()));
            if let Some(s) = &r.selection {
                put_report(&mut p, s)?
            }
            p.opt_text(&r.decode_path)?;
        }
        ControlRecord::Error(e) => {
            kind = 5;
            p.u64(e.request_id);
            p.u8(e.code as u8);
            p.text(&e.message)?;
        }
        ControlRecord::Cancel { request_id } => {
            kind = 6;
            p.u64(*request_id);
        }
    }
    if p.failed || p.bytes.len() > MAX_CONTROL_RECORD_BYTES {
        return Err("control record exceeds limit".into());
    }
    out.write_all(&MAGIC).map_err(|e| e.to_string())?;
    out.write_all(&JOB_PROTOCOL_VERSION.to_be_bytes())
        .map_err(|e| e.to_string())?;
    out.write_all(&[kind]).map_err(|e| e.to_string())?;
    out.write_all(
        &u32::try_from(p.bytes.len())
            .map_err(|_| "control record overflow")?
            .to_be_bytes(),
    )
    .map_err(|e| e.to_string())?;
    out.write_all(&p.bytes).map_err(|e| e.to_string())?;
    Ok(())
}

/// Read exactly one control record, rejecting unknown versions, oversized
/// length fields, truncated input and non-UTF-8 text.
pub fn read_control<R: Read>(input: &mut R) -> Result<ControlRecord, String> {
    let mut h = [0u8; HEADER];
    input.read_exact(&mut h).map_err(|e| e.to_string())?;
    if h[..4] != MAGIC {
        return Err("invalid control magic".into());
    }
    if u16::from_be_bytes([h[4], h[5]]) != JOB_PROTOCOL_VERSION {
        return Err("unsupported control version".into());
    }
    let n = usize::try_from(u32::from_be_bytes(h[7..11].try_into().unwrap()))
        .map_err(|_| "control length overflow")?;
    if n > MAX_CONTROL_RECORD_BYTES {
        return Err("control record exceeds limit".into());
    }
    let mut b = Vec::new();
    b.try_reserve_exact(n)
        .map_err(|_| "control allocation failed")?;
    b.resize(n, 0);
    input.read_exact(&mut b).map_err(|e| e.to_string())?;
    let mut t = Take { b: &b, p: 0 };
    let record = match h[6] {
        1 => ControlRecord::Request(JobRequest {
            request_id: t.u64()?,
            operation: op(t.u8()?)?,
            profile: profile(t.u8()?)?,
            limits: get_limits(&mut t)?,
            diagnostics: match t.u8()? {
                0 => false,
                1 => true,
                _ => return Err("invalid diagnostic flag".into()),
            },
        }),
        2 => {
            let version = t.u16()?;
            if version != JOB_PROTOCOL_VERSION {
                return Err("unsupported capability version".into());
            }
            let a = match t.u8()? {
                0 => false,
                1 => true,
                _ => return Err("invalid capability flag".into()),
            };
            let d = match t.u8()? {
                0 => false,
                1 => true,
                _ => return Err("invalid capability flag".into()),
            };
            ControlRecord::Capability(JobCapability {
                protocol_version: version,
                select_whole_input: a,
                decode_archive: d,
                data_transport: t.text()?,
                cancellation: t.text()?,
            })
        }
        3 => ControlRecord::Progress(JobProgress {
            request_id: t.u64()?,
            stage: match t.u8()? {
                1 => JobStage::Accepted,
                2 => JobStage::InputRead,
                3 => JobStage::SelectionStarted,
                4 => JobStage::SelectionFinished,
                5 => JobStage::DecodeStarted,
                6 => JobStage::DecodeFinished,
                7 => JobStage::OutputWritten,
                _ => return Err("unknown progress stage".into()),
            },
        }),
        4 => get_result(&mut t)?,
        5 => ControlRecord::Error(JobError {
            request_id: t.u64()?,
            code: match t.u8()? {
                0 => JobErrorCode::InvalidRequest,
                1 => JobErrorCode::ResourceLimit,
                2 => JobErrorCode::Cancelled,
                3 => JobErrorCode::Unsupported,
                4 => JobErrorCode::Io,
                5 => JobErrorCode::Execution,
                6 => JobErrorCode::Protocol,
                _ => return Err("unknown job error code".into()),
            },
            message: t.text()?,
        }),
        6 => ControlRecord::Cancel {
            request_id: t.u64()?,
        },
        _ => return Err("unknown control record kind".into()),
    };
    t.end()?;
    Ok(record)
}
fn put_report(b: &mut Buf, r: &JobSelectionReport) -> Result<(), String> {
    b.u8(profile_tag(r.profile));
    b.usize(r.input_bytes)?;
    b.usize(r.peak_reserved_memory)?;
    b.usize(r.peak_reserved_workers)?;
    b.usize(r.peak_reserved_temporary)?;
    b.text(&r.selected)?;
    b.u32(u32::try_from(r.discovery.len()).map_err(|_| "too many discovery diagnostics")?);
    for d in &r.discovery {
        b.text(&d.family)?;
        b.u8(u8::from(d.admitted));
        b.u8(u8::from(d.available));
        b.text(&d.reason)?;
    }
    b.u32(u32::try_from(r.trials.len()).map_err(|_| "too many trial diagnostics")?);
    for x in &r.trials {
        b.text(&x.id)?;
        b.usize(x.priority)?;
        b.text(&x.status)?;
        b.opt_text(&x.reason)?;
        b.opt_usize(x.archive_bytes)?;
        b.usize(x.nested_omitted)?;
        b.u32(
            u32::try_from(x.provider_omissions.len()).map_err(|_| "too many provider omissions")?,
        );
        for omission in &x.provider_omissions {
            b.text(omission)?;
        }
        b.u32(u32::try_from(x.nested.len()).map_err(|_| "too many nested diagnostics")?);
        for n in &x.nested {
            b.text(&n.kind)?;
            b.text(&n.id)?;
            b.text(&n.status)?;
            b.opt_usize(n.region)?;
            b.opt_text(&n.backend)?;
            b.text(&n.bytes_unit)?;
            b.opt_usize(n.bytes)?;
            b.opt_text(&n.detail)?;
        }
    }
    Ok(())
}
fn get_report(t: &mut Take<'_>) -> Result<JobSelectionReport, String> {
    let profile = profile(t.u8()?)?;
    let input_bytes = t.usize()?;
    let peak_reserved_memory = t.usize()?;
    let peak_reserved_workers = t.usize()?;
    let peak_reserved_temporary = t.usize()?;
    let selected = t.text()?;
    let discovery_count = usize::try_from(t.u32()?).map_err(|_| "discovery count overflow")?;
    if discovery_count > t.b.len().saturating_sub(t.p) / 7 {
        return Err("too many discovery diagnostics".into());
    }
    let mut discovery = Vec::new();
    discovery
        .try_reserve_exact(discovery_count)
        .map_err(|_| "diagnostic allocation failed")?;
    for _ in 0..discovery_count {
        let family = t.text()?;
        let admitted = match t.u8()? {
            0 => false,
            1 => true,
            _ => return Err("invalid control boolean".into()),
        };
        let available = match t.u8()? {
            0 => false,
            1 => true,
            _ => return Err("invalid control boolean".into()),
        };
        let reason = t.text()?;
        discovery.push(JobDiscovery {
            family,
            admitted,
            available,
            reason,
        });
    }
    let count = usize::try_from(t.u32()?).map_err(|_| "trial count overflow")?;
    if count > MAX_CONTROL_RECORD_BYTES / 8 || count > t.b.len().saturating_sub(t.p) / 23 {
        return Err("too many trial diagnostics".into());
    }
    let mut trials = Vec::new();
    trials
        .try_reserve_exact(count)
        .map_err(|_| "diagnostic allocation failed")?;
    for _ in 0..count {
        let id = t.text()?;
        let priority = t.usize()?;
        let status = t.text()?;
        let reason = t.opt_text()?;
        let archive_bytes = t.opt_usize()?;
        let nested_omitted = t.usize()?;
        let omissions =
            usize::try_from(t.u32()?).map_err(|_| "provider omission count overflow")?;
        if omissions > t.b.len().saturating_sub(t.p) / 4 {
            return Err("too many provider omissions".into());
        }
        let mut provider_omissions = Vec::new();
        provider_omissions
            .try_reserve_exact(omissions)
            .map_err(|_| "diagnostic allocation failed")?;
        for _ in 0..omissions {
            provider_omissions.push(t.text()?);
        }
        let nested_count = usize::try_from(t.u32()?).map_err(|_| "nested count overflow")?;
        if nested_count > t.b.len().saturating_sub(t.p) / 12 {
            return Err("too many nested diagnostics".into());
        }
        let mut nested = Vec::new();
        nested
            .try_reserve_exact(nested_count)
            .map_err(|_| "diagnostic allocation failed")?;
        for _ in 0..nested_count {
            nested.push(JobDiagnostic {
                kind: t.text()?,
                id: t.text()?,
                status: t.text()?,
                region: t.opt_usize()?,
                backend: t.opt_text()?,
                bytes_unit: t.text()?,
                bytes: t.opt_usize()?,
                detail: t.opt_text()?,
            });
        }
        trials.push(JobTrial {
            id,
            priority,
            status,
            reason,
            archive_bytes,
            nested,
            nested_omitted,
            provider_omissions,
        });
    }
    Ok(JobSelectionReport {
        profile,
        input_bytes,
        discovery,
        trials,
        peak_reserved_memory,
        peak_reserved_workers,
        peak_reserved_temporary,
        selected,
    })
}
fn get_result(t: &mut Take<'_>) -> Result<ControlRecord, String> {
    let request_id = t.u64()?;
    let operation = op(t.u8()?)?;
    let output_bytes = t.usize()?;
    let selection = match t.u8()? {
        0 => None,
        1 => Some(get_report(t)?),
        _ => return Err("invalid selection report option".into()),
    };
    let decode_path = t.opt_text()?;
    Ok(ControlRecord::Result(JobResult {
        request_id,
        operation,
        output_bytes,
        selection,
        decode_path,
    }))
}
fn simple_status(v: TrialStatus) -> String {
    match v {
        TrialStatus::Completed => "completed",
        TrialStatus::BudgetOmitted => "budget-omitted",
        TrialStatus::ProfileOmitted => "profile-omitted",
        TrialStatus::Failed => "failed",
        TrialStatus::Selected => "selected",
    }
    .into()
}
fn report_of(r: selection::SelectionReport) -> JobSelectionReport {
    let discovery = r
        .discovery
        .into_iter()
        .map(|d| JobDiscovery {
            family: d.family.into(),
            admitted: d.admitted,
            available: d.available,
            reason: d.reason.into(),
        })
        .collect();
    let trials = r
        .trials
        .into_iter()
        .map(|x| {
            let (nested, nested_omitted, provider_omissions) = match x.details {
                TrialDetails::None => (Vec::new(), 0, Vec::new()),
                TrialDetails::Native(v) => {
                    let rows = v
                        .into_iter()
                        .map(|n| JobDiagnostic {
                            kind: "native".into(),
                            id: n.id,
                            status: format!("{:?}", n.status),
                            region: None,
                            backend: None,
                            bytes_unit: "archive".into(),
                            bytes: n.archive_bytes,
                            detail: n.reason,
                        })
                        .collect();
                    (rows, 0, Vec::new())
                }
                TrialDetails::Mixed(v) => {
                    let omitted = v.omitted_entries;
                    let provider_omissions = v.provider_omissions;
                    let rows = v
                        .entries
                        .into_iter()
                        .map(|n| JobDiagnostic {
                            kind: format!("mixed:{}", n.region_kind.name()),
                            id: n.candidate,
                            status: format!("{:?}", n.status),
                            region: Some(n.region),
                            backend: n.backend.map(|value| format!("{:?}", value)),
                            bytes_unit: "payload".into(),
                            bytes: n.payload_bytes,
                            detail: n.detail,
                        })
                        .collect();
                    (rows, omitted, provider_omissions)
                }
            };
            JobTrial {
                id: x.id,
                priority: x.priority,
                status: simple_status(x.status),
                reason: x.reason,
                archive_bytes: x.archive_bytes,
                nested,
                nested_omitted,
                provider_omissions,
            }
        })
        .collect();
    JobSelectionReport {
        profile: match r.profile {
            SelectionProfile::Fast => JobProfile::Fast,
            SelectionProfile::Default => JobProfile::Default,
            SelectionProfile::Best => JobProfile::Best,
        },
        input_bytes: r.input_bytes,
        discovery,
        trials,
        peak_reserved_memory: r.peak_reserved_memory,
        peak_reserved_workers: r.peak_reserved_workers,
        peak_reserved_temporary: r.peak_reserved_temporary,
        selected: r.selected,
    }
}
fn stage<F: FnMut(JobProgress)>(
    request_id: u64,
    s: JobStage,
    emit: &mut F,
    c: &CancelToken,
) -> Result<(), String> {
    if c.is_cancelled() {
        return Err("job cancelled before stage".into());
    }
    emit(JobProgress {
        request_id,
        stage: s,
    });
    Ok(())
}
fn validate_limits(request: &JobRequest) -> Result<Option<Instant>, String> {
    let l = &request.limits;
    if l.input_bytes == 0
        || l.archive_bytes == 0
        || l.output_bytes == 0
        || l.memory_bytes == 0
        || l.intermediate_bytes == 0
        || l.temporary_bytes == 0
        || l.workers == 0
    {
        return Err("zero job limit".into());
    }
    if request.operation == JobOperation::SelectWholeInput
        && l.input_bytes > selection::MAX_WHOLE_INPUT
    {
        return Err("whole-input job exceeds maximum input".into());
    }
    l.deadline_millis
        .map(|m| {
            Instant::now()
                .checked_add(Duration::from_millis(m))
                .ok_or_else(|| "job deadline overflow".into())
        })
        .transpose()
}
fn read_data<R: Read>(
    input: &mut R,
    cap: usize,
    memory: usize,
    deadline: Option<Instant>,
    c: &CancelToken,
) -> Result<Vec<u8>, String> {
    const SCRATCH: usize = 64 << 10;
    if cap.checked_add(SCRATCH).is_none_or(|need| need > memory) {
        return Err("job input and scratch exceed memory limit".into());
    }
    let mut out = Vec::new();
    out.try_reserve_exact(cap)
        .map_err(|_| "job input allocation failed")?;
    if out
        .capacity()
        .checked_add(SCRATCH)
        .is_none_or(|need| need > memory)
    {
        return Err("job input allocation exceeds memory limit".into());
    }
    let mut chunk = [0u8; SCRATCH];
    loop {
        if c.is_cancelled() || deadline.is_some_and(|d| Instant::now() >= d) {
            return Err("job cancelled while reading input".into());
        }
        let n = input.read(&mut chunk).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        let next = out.len().checked_add(n).ok_or("job input size overflow")?;
        if next > cap {
            return Err("job input exceeds declared cap".into());
        }
        out.extend_from_slice(&chunk[..n]);
    }
    Ok(out)
}

struct CountingWriter<W> {
    inner: W,
    count: usize,
    cap: usize,
}
impl<W: Write> Write for CountingWriter<W> {
    fn write(&mut self, data: &[u8]) -> stdio::Result<usize> {
        let next = self
            .count
            .checked_add(data.len())
            .ok_or_else(|| stdio::Error::other("job output overflow"))?;
        if next > self.cap {
            return Err(stdio::Error::other("job output exceeds declared cap"));
        }
        let n = self.inner.write(data)?;
        self.count += n;
        Ok(n)
    }
    fn flush(&mut self) -> stdio::Result<()> {
        self.inner.flush()
    }
}

/// Run the real bounded whole-input selector with external data transports.
/// `emit` receives only stage transitions; no made-up byte-progress is emitted.
pub fn execute_select_whole_input<
    E: CandidateExecutor,
    R: Read,
    W: Write,
    F: FnMut(JobProgress),
>(
    request: &JobRequest,
    source: &mut R,
    destination: &mut W,
    executor: E,
    cancel: CancelToken,
    mut emit: F,
) -> Result<JobResult, String> {
    if request.operation != JobOperation::SelectWholeInput {
        return Err("wrong job operation".into());
    }
    let deadline = validate_limits(request)?;
    stage(request.request_id, JobStage::Accepted, &mut emit, &cancel)?;
    let data = read_data(
        source,
        request.limits.input_bytes,
        request.limits.memory_bytes,
        deadline,
        &cancel,
    )?;
    stage(request.request_id, JobStage::InputRead, &mut emit, &cancel)?;
    stage(
        request.request_id,
        JobStage::SelectionStarted,
        &mut emit,
        &cancel,
    )?;
    let capacity_slack = data.capacity().saturating_sub(data.len());
    let selection_memory = request
        .limits
        .memory_bytes
        .checked_sub(capacity_slack)
        .ok_or("job input capacity exceeds memory limit")?;
    let r = selection::select_whole_input(
        &data,
        match request.profile {
            JobProfile::Fast => SelectionProfile::Fast,
            JobProfile::Default => SelectionProfile::Default,
            JobProfile::Best => SelectionProfile::Best,
        },
        SelectionLimits {
            memory_bytes: selection_memory,
            workers: request.limits.workers,
            temporary_bytes: request.limits.temporary_bytes,
            output_bytes: request.limits.output_bytes,
            intermediate_bytes: request.limits.intermediate_bytes,
            deadline,
            cancellation: Some(cancel.as_arc()),
        },
        executor,
    )?;
    stage(
        request.request_id,
        JobStage::SelectionFinished,
        &mut emit,
        &cancel,
    )?;
    if r.archive.len() > request.limits.archive_bytes
        || r.archive.capacity() > request.limits.archive_bytes
    {
        return Err("selected archive exceeds declared cap".into());
    }
    destination
        .write_all(&r.archive)
        .map_err(|e| e.to_string())?;
    stage(
        request.request_id,
        JobStage::OutputWritten,
        &mut emit,
        &cancel,
    )?;
    Ok(JobResult {
        request_id: request.request_id,
        operation: request.operation,
        output_bytes: r.archive.len(),
        selection: request.diagnostics.then(|| report_of(r.report)),
        decode_path: None,
    })
}

/// Run the bounded full-engine decoder against supplied streams. Constructing
/// `FullEngine` and selecting installed providers remains the caller's job.
pub fn execute_decode<R: Read, W: Write, F: FnMut(JobProgress)>(
    request: &JobRequest,
    engine: &FullEngine,
    source: R,
    destination: W,
    cancel: CancelToken,
    mut emit: F,
) -> Result<JobResult, String> {
    if request.operation != JobOperation::DecodeArchive {
        return Err("wrong job operation".into());
    }
    let deadline = validate_limits(request)?;
    stage(request.request_id, JobStage::Accepted, &mut emit, &cancel)?;
    stage(
        request.request_id,
        JobStage::DecodeStarted,
        &mut emit,
        &cancel,
    )?;
    let mut counted = CountingWriter {
        inner: destination,
        count: 0,
        cap: request.limits.output_bytes,
    };
    let path = io::decode(
        engine,
        source,
        &mut counted,
        request.limits.archive_bytes,
        &OperationLimits {
            memory_bytes: request.limits.memory_bytes,
            output_bytes: request.limits.output_bytes,
            intermediate_bytes: request.limits.intermediate_bytes,
            deadline,
            cancellation: Some(cancel.as_arc()),
        },
    )?;
    stage(
        request.request_id,
        JobStage::DecodeFinished,
        &mut emit,
        &cancel,
    )?;
    stage(
        request.request_id,
        JobStage::OutputWritten,
        &mut emit,
        &cancel,
    )?;
    Ok(JobResult {
        request_id: request.request_id,
        operation: request.operation,
        output_bytes: counted.count,
        selection: None,
        decode_path: Some(
            match path {
                DecodePath::NativeIncremental => "native-incremental",
                DecodePath::NativeCoreBuffered => "native-core-buffered",
                DecodePath::FullFrameBuffered => "full-frame-buffered",
            }
            .into(),
        ),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        core::{self, NativeOptions},
        full_engine::backend_provider::{BackendProvider, TrustedBackendPaths},
    };
    use std::io::Cursor;
    #[derive(Clone)]
    struct Fake;
    impl CandidateExecutor for Fake {
        fn run(
            &self,
            _: &selection::Plan,
            _: &[u8],
            _: &SelectionLimits,
        ) -> Result<Vec<u8>, String> {
            Ok(b"CJ".to_vec())
        }
    }
    fn request() -> JobRequest {
        JobRequest {
            request_id: 7,
            operation: JobOperation::SelectWholeInput,
            profile: JobProfile::Fast,
            limits: JobLimits {
                input_bytes: 9,
                archive_bytes: 9,
                output_bytes: 9,
                memory_bytes: 9,
                intermediate_bytes: 9,
                temporary_bytes: 9,
                workers: 1,
                deadline_millis: None,
            },
            diagnostics: true,
        }
    }
    #[test]
    fn control_round_trip() {
        let r = ControlRecord::Request(request());
        let mut b = Vec::new();
        write_control(&mut b, &r).unwrap();
        assert_eq!(read_control(&mut Cursor::new(b)).unwrap(), r)
    }
    #[test]
    fn rejects_unknown_version_oversize_truncated_and_utf8() {
        let mut b = Vec::new();
        write_control(&mut b, &ControlRecord::Request(request())).unwrap();
        b[4] = 0;
        b[5] = 2;
        assert!(read_control(&mut Cursor::new(b)).is_err());
        let mut h = Vec::from(MAGIC);
        h.extend_from_slice(&JOB_PROTOCOL_VERSION.to_be_bytes());
        h.push(1);
        h.extend_from_slice(&u32::MAX.to_be_bytes());
        assert!(read_control(&mut Cursor::new(h)).is_err());
        assert!(read_control(&mut Cursor::new(vec![0; 3])).is_err());
        let mut p = Buf::default();
        p.u64(1);
        p.u8(0);
        p.text("x").unwrap();
        let mut raw = Vec::from(MAGIC);
        raw.extend_from_slice(&JOB_PROTOCOL_VERSION.to_be_bytes());
        raw.push(5);
        raw.extend_from_slice(&(p.bytes.len() as u32).to_be_bytes());
        raw.extend_from_slice(&p.bytes);
        let at = HEADER + 9;
        raw[at] = 0xff;
        assert!(read_control(&mut Cursor::new(raw)).is_err());
    }
    #[test]
    fn direct_selection_entry_applies_limits_cancel_and_reports_actual_output() {
        let mut r = request();
        r.limits.input_bytes = 3;
        r.limits.archive_bytes = 16;
        r.limits.output_bytes = 16;
        r.limits.memory_bytes = 64 << 20;
        r.limits.intermediate_bytes = 1 << 16;
        r.limits.temporary_bytes = 1 << 16;
        let mut source = Cursor::new(b"abc".to_vec());
        let mut out = Vec::new();
        let mut stages = Vec::new();
        let result =
            execute_select_whole_input(&r, &mut source, &mut out, Fake, CancelToken::new(), |p| {
                stages.push(p.stage)
            })
            .unwrap();
        assert_eq!(result.output_bytes, out.len());
        assert!(result.selection.is_some());
        assert_eq!(stages.last(), Some(&JobStage::OutputWritten));
        let cancelled = CancelToken::new();
        cancelled.cancel();
        assert!(execute_select_whole_input(
            &r,
            &mut Cursor::new(b"a".to_vec()),
            &mut Vec::new(),
            Fake,
            cancelled,
            |_| {}
        )
        .is_err());
    }
    #[test]
    fn decode_entry_counts_actual_native_output_and_finishes_stage() {
        let mut archive = Vec::new();
        core::encode(
            Cursor::new(b"job".to_vec()),
            &mut archive,
            &NativeOptions {
                output_limit: 1024,
                memory_limit: 8 << 20,
                ..NativeOptions::default()
            },
        )
        .unwrap();
        let engine = FullEngine {
            backends: BackendProvider {
                paths: TrustedBackendPaths {
                    cix: "/not-used/cix".into(),
                    paq_libraries: "/not-used/lib".into(),
                    temporary_root: "/not-used/tmp".into(),
                },
            },
            images: None,
            spatial: None,
        };
        let mut r = request();
        r.operation = JobOperation::DecodeArchive;
        r.limits.archive_bytes = 1024;
        r.limits.output_bytes = 32;
        r.limits.memory_bytes = 64 << 20;
        r.limits.intermediate_bytes = 1 << 20;
        let mut out = Vec::new();
        let mut stages = Vec::new();
        let result = execute_decode(
            &r,
            &engine,
            Cursor::new(archive),
            &mut out,
            CancelToken::new(),
            |p| stages.push(p.stage),
        )
        .unwrap();
        assert_eq!(result.output_bytes, out.len());
        assert_eq!(out, b"job");
        assert_eq!(stages.last(), Some(&JobStage::OutputWritten));
    }
}
