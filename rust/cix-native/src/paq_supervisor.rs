//! CIX-owned parent for the private, same-CIX PAQ worker protocol.
//!
//! This module deliberately launches the CIX executable's versioned internal
//! worker switch, never an upstream PAQ executable, shell, Python process, or
//! PATH-resolved command. It supervises one worker only; aggregate candidate
//! scheduling and aggregate memory admission remain the full-engine parent's
//! responsibility.

use crate::limits;
use crate::paq_bridge::PaqVariant;
use std::ffi::OsString;
use std::fmt;
use std::fs;
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use crate::paq_worker::SWITCH;

const POLL_INTERVAL: Duration = Duration::from_millis(10);
const TEMP_ATTEMPTS: u32 = 256;
static TEMP_SEQUENCE: AtomicU64 = AtomicU64::new(0);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PaqOperation {
    Encode,
    Decode,
}

impl PaqOperation {
    fn argument(self) -> &'static str {
        match self {
            Self::Encode => "encode",
            Self::Decode => "decode",
        }
    }
}

/// Validated PAQ level representation. It never accepts an upstream option
/// string from an untrusted caller.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PaqLevel {
    pub number: u8,
    pub lstm: bool,
}

impl PaqLevel {
    pub fn argument(self) -> Result<OsString, PaqSupervisorError> {
        if self.number > 12 {
            return Err(PaqSupervisorError::InvalidRequest(
                "PAQ level must be 0 through 12",
            ));
        }
        Ok(format!("-{}{}", self.number, if self.lstm { "L" } else { "" }).into())
    }
}

/// Explicit product-owned locations. Neither path is inferred from PATH,
/// current working directory, environment variables, or a third-party tool.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PaqWorkerPaths {
    pub cix_executable: PathBuf,
    pub private_library_directory: PathBuf,
    pub temporary_root: PathBuf,
}

/// One isolated worker request. Limits are per worker and must already be
/// admitted by the caller's aggregate scheduler before calling [`run`].
#[derive(Clone, Debug)]
pub struct PaqWorkerRequest {
    pub paths: PaqWorkerPaths,
    pub variant: PaqVariant,
    pub operation: PaqOperation,
    pub input: PathBuf,
    pub input_limit_bytes: u64,
    pub output_limit_bytes: u64,
    /// Maximum bytes this parent may allocate for the returned result. The
    /// aggregate scheduler reserves this concurrently with the worker's own
    /// admitted memory and diagnostic buffers before calling [`run`].
    pub parent_result_limit_bytes: usize,
    pub memory_limit_bytes: u64,
    pub level: PaqLevel,
    pub lstm_layers: u8,
    pub joint_discount_mode: Option<u8>,
    pub deadline: Option<Instant>,
    pub cancellation: Option<Arc<AtomicBool>>,
    /// Cap for each diagnostic pipe. Excess data is drained and discarded so
    /// a verbose worker cannot deadlock on a full pipe.
    pub diagnostic_limit_bytes: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CapturedStream {
    pub bytes: Vec<u8>,
    pub truncated: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PaqWorkerResult {
    pub output: Vec<u8>,
    pub stdout: CapturedStream,
    pub stderr: CapturedStream,
}

#[derive(Debug)]
pub enum PaqSupervisorError {
    InvalidRequest(&'static str),
    InputTooLarge {
        actual: u64,
        limit: u64,
    },
    Cancelled,
    DeadlineExceeded,
    Interrupted,
    Context(String),
    Spawn(io::Error),
    Wait(io::Error),
    Capture(io::Error),
    Exit {
        status: ExitStatus,
        stdout: CapturedStream,
        stderr: CapturedStream,
    },
    OutputTooLarge {
        actual: u64,
        limit: u64,
    },
    ResultAllocation {
        requested: usize,
    },
    OutputUnavailable(io::Error),
    Cleanup(io::Error),
}

impl fmt::Display for PaqSupervisorError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidRequest(message) => f.write_str(message),
            Self::InputTooLarge { actual, limit } => {
                write!(
                    f,
                    "PAQ input is {actual} bytes, above its {limit}-byte limit"
                )
            }
            Self::Cancelled => f.write_str("PAQ worker cancelled"),
            Self::DeadlineExceeded => f.write_str("PAQ worker deadline exceeded"),
            Self::Interrupted => f.write_str("PAQ worker interrupted"),
            Self::Context(message) => write!(f, "PAQ worker context stopped: {message}"),
            Self::Spawn(error) => write!(f, "cannot start private CIX PAQ worker: {error}"),
            Self::Wait(error) => write!(f, "cannot wait for private CIX PAQ worker: {error}"),
            Self::Capture(error) => write!(f, "cannot capture PAQ worker diagnostics: {error}"),
            Self::Exit { status, .. } => write!(f, "private CIX PAQ worker failed: {status}"),
            Self::OutputTooLarge { actual, limit } => {
                write!(
                    f,
                    "PAQ output is {actual} bytes, above its {limit}-byte limit"
                )
            }
            Self::ResultAllocation { requested } => write!(
                f,
                "cannot reserve {requested} bytes for the PAQ parent result"
            ),
            Self::OutputUnavailable(error) => {
                write!(f, "PAQ worker output is unavailable: {error}")
            }
            Self::Cleanup(error) => write!(f, "cannot remove PAQ temporary output: {error}"),
        }
    }
}

impl std::error::Error for PaqSupervisorError {}

/// Launch one bounded private worker and return its complete temporary output.
///
/// The output lives only in a private, newly-created directory and is removed
/// on every normal, failed, cancelled, expired, or dropped execution path.
pub fn run(request: &PaqWorkerRequest) -> Result<PaqWorkerResult, PaqSupervisorError> {
    validate(request)?;
    check_stop(request)?;
    let mut temporary = TemporaryOutput::create(&request.paths.temporary_root)?;
    let mut command = Command::new(&request.paths.cix_executable);
    command
        .arg(SWITCH)
        .arg(variant_argument(request.variant))
        .arg(request.operation.argument())
        .arg(&request.paths.private_library_directory)
        .arg(&request.input)
        .arg(temporary.path())
        .arg(request.memory_limit_bytes.to_string())
        .arg(request.output_limit_bytes.to_string())
        .arg(request.level.argument()?)
        .arg(request.lstm_layers.to_string())
        .arg(joint_argument(request.joint_discount_mode))
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        // The worker repeats this defence before dlopen. Keeping it here
        // ensures inherited research/model settings cannot affect startup.
        .env_clear()
        .env("LC_ALL", "C")
        .env("OMP_NUM_THREADS", "1");
    if let Some(mode) = request.joint_discount_mode {
        command.env("CIX_JOINT_DISCOUNT", mode.to_string());
    }
    let mut child = ChildCleanup::new(command.spawn().map_err(PaqSupervisorError::Spawn)?);
    let stdout = child.take_stdout()?;
    let stderr = child.take_stderr()?;
    // Readers start before polling the child: both pipes are continuously
    // drained, including after the retained transcript reaches its cap.
    let stdout_reader = capture_thread(stdout, request.diagnostic_limit_bytes);
    let stderr_reader = capture_thread(stderr, request.diagnostic_limit_bytes);
    let status = loop {
        match check_stop(request) {
            Ok(()) => {}
            Err(error) => {
                let (stdout, stderr) = child.terminate_and_collect(stdout_reader, stderr_reader)?;
                return Err(with_diagnostics(error, stdout, stderr));
            }
        }
        if let Some(status) = child.try_wait()? {
            break status;
        }
        thread::sleep(POLL_INTERVAL);
    };
    child.disarm();
    let stdout = finish_capture(stdout_reader)?;
    let stderr = finish_capture(stderr_reader)?;
    if !status.success() {
        return Err(PaqSupervisorError::Exit {
            status,
            stdout,
            stderr,
        });
    }
    let metadata = fs::metadata(temporary.path()).map_err(PaqSupervisorError::OutputUnavailable)?;
    if metadata.len() > request.output_limit_bytes {
        return Err(PaqSupervisorError::OutputTooLarge {
            actual: metadata.len(),
            limit: request.output_limit_bytes,
        });
    }
    let output = read_result(temporary.path(), metadata.len(), request)?;
    temporary.cleanup()?;
    Ok(PaqWorkerResult {
        output,
        stdout,
        stderr,
    })
}

fn with_diagnostics(
    error: PaqSupervisorError,
    _stdout: CapturedStream,
    _stderr: CapturedStream,
) -> PaqSupervisorError {
    // Cancellation/deadline are typed independently of diagnostics. The
    // temporary directory still drops after child reaping; callers can log the
    // streams only for process-exit failures where they are part of the error.
    error
}

fn validate(request: &PaqWorkerRequest) -> Result<(), PaqSupervisorError> {
    for path in [
        &request.paths.cix_executable,
        &request.paths.private_library_directory,
        &request.paths.temporary_root,
        &request.input,
    ] {
        if !path.is_absolute() {
            return Err(PaqSupervisorError::InvalidRequest(
                "PAQ supervisor paths must be absolute",
            ));
        }
    }
    if !request.paths.cix_executable.is_file() {
        return Err(PaqSupervisorError::InvalidRequest(
            "private CIX executable must be a regular file",
        ));
    }
    if !request.paths.private_library_directory.is_dir() {
        return Err(PaqSupervisorError::InvalidRequest(
            "private PAQ library directory must exist",
        ));
    }
    validate_private_temporary_root(&request.paths.temporary_root)?;
    let input = fs::metadata(&request.input).map_err(PaqSupervisorError::OutputUnavailable)?;
    if !input.is_file() {
        return Err(PaqSupervisorError::InvalidRequest(
            "PAQ input must be a regular file",
        ));
    }
    for (value, description) in [
        (request.input_limit_bytes, "PAQ input limit"),
        (request.output_limit_bytes, "PAQ output limit"),
        (request.memory_limit_bytes, "PAQ memory limit"),
    ] {
        if value == 0 || value > i64::MAX as u64 {
            return Err(PaqSupervisorError::InvalidRequest(description));
        }
    }
    if request.parent_result_limit_bytes == 0
        || request.output_limit_bytes > request.parent_result_limit_bytes as u64
    {
        return Err(PaqSupervisorError::InvalidRequest(
            "PAQ output limit must fit the caller-reserved parent result limit",
        ));
    }
    if input.len() > request.input_limit_bytes {
        return Err(PaqSupervisorError::InputTooLarge {
            actual: input.len(),
            limit: request.input_limit_bytes,
        });
    }
    request.level.argument()?;
    if !(1..=5).contains(&request.lstm_layers) {
        return Err(PaqSupervisorError::InvalidRequest(
            "PAQ LSTM layer count must be 1 through 5",
        ));
    }
    if request.joint_discount_mode.is_some_and(|mode| mode > 3) {
        return Err(PaqSupervisorError::InvalidRequest(
            "PAQ joint-discount mode must be 0 through 3",
        ));
    }
    if request.variant != PaqVariant::JointDiscount && request.joint_discount_mode.is_some() {
        return Err(PaqSupervisorError::InvalidRequest(
            "PAQ joint-discount mode requires the joint-discount variant",
        ));
    }
    if request.diagnostic_limit_bytes == 0 {
        return Err(PaqSupervisorError::InvalidRequest(
            "PAQ diagnostic capture limit must be non-zero",
        ));
    }
    Ok(())
}

fn read_result(
    path: &Path,
    metadata_len: u64,
    request: &PaqWorkerRequest,
) -> Result<Vec<u8>, PaqSupervisorError> {
    if metadata_len > request.parent_result_limit_bytes as u64 {
        return Err(PaqSupervisorError::OutputTooLarge {
            actual: metadata_len,
            limit: request.parent_result_limit_bytes as u64,
        });
    }
    let capacity =
        usize::try_from(metadata_len).map_err(|_| PaqSupervisorError::OutputTooLarge {
            actual: metadata_len,
            limit: request.parent_result_limit_bytes as u64,
        })?;
    let mut output = Vec::new();
    output
        .try_reserve_exact(capacity)
        .map_err(|_| PaqSupervisorError::ResultAllocation {
            requested: capacity,
        })?;
    let file = fs::File::open(path).map_err(PaqSupervisorError::OutputUnavailable)?;
    // This is beneath a private directory, but retain a strict read bound if
    // an unexpected writer changes the file after the metadata check.
    file.take(metadata_len.saturating_add(1))
        .read_to_end(&mut output)
        .map_err(PaqSupervisorError::OutputUnavailable)?;
    if output.len() > capacity {
        return Err(PaqSupervisorError::OutputTooLarge {
            actual: output.len() as u64,
            limit: request.parent_result_limit_bytes as u64,
        });
    }
    Ok(output)
}

fn check_stop(request: &PaqWorkerRequest) -> Result<(), PaqSupervisorError> {
    if request
        .cancellation
        .as_ref()
        .is_some_and(|token| token.load(Ordering::Acquire))
    {
        return Err(PaqSupervisorError::Cancelled);
    }
    if request
        .deadline
        .is_some_and(|deadline| Instant::now() >= deadline)
    {
        return Err(PaqSupervisorError::DeadlineExceeded);
    }
    match limits::check() {
        Ok(()) => Ok(()),
        Err(message) if message == limits::INTERRUPTED_ERROR => {
            Err(PaqSupervisorError::Interrupted)
        }
        Err(message) if message == limits::CANCELLED_ERROR => Err(PaqSupervisorError::Cancelled),
        Err(message) if message == limits::DEADLINE_ERROR => {
            Err(PaqSupervisorError::DeadlineExceeded)
        }
        Err(message) => Err(PaqSupervisorError::Context(message)),
    }
}

fn variant_argument(variant: PaqVariant) -> &'static str {
    match variant {
        PaqVariant::V215 => "v215",
        PaqVariant::V216 => "v216",
        PaqVariant::JointDiscount => "joint-discount",
        PaqVariant::StoreState => "store-state",
    }
}

fn joint_argument(mode: Option<u8>) -> &'static str {
    match mode {
        None => "none",
        Some(0) => "0",
        Some(1) => "1",
        Some(2) => "2",
        Some(3) => "3",
        Some(_) => unreachable!("validated joint-discount mode"),
    }
}

fn capture_thread<R: Read + Send + 'static>(
    reader: R,
    cap: usize,
) -> JoinHandle<io::Result<CapturedStream>> {
    thread::spawn(move || {
        let mut reader = reader;
        let mut saved = Vec::with_capacity(cap.min(8192));
        let mut buffer = [0u8; 8192];
        let mut truncated = false;
        loop {
            let count = reader.read(&mut buffer)?;
            if count == 0 {
                return Ok(CapturedStream {
                    bytes: saved,
                    truncated,
                });
            }
            let remaining = cap.saturating_sub(saved.len());
            let kept = remaining.min(count);
            saved.extend_from_slice(&buffer[..kept]);
            truncated |= kept != count;
        }
    })
}

fn finish_capture(
    handle: JoinHandle<io::Result<CapturedStream>>,
) -> Result<CapturedStream, PaqSupervisorError> {
    handle
        .join()
        .map_err(|_| PaqSupervisorError::Capture(io::Error::other("diagnostic reader panicked")))?
        .map_err(PaqSupervisorError::Capture)
}

struct ChildCleanup {
    child: Option<Child>,
}

impl ChildCleanup {
    fn new(child: Child) -> Self {
        Self { child: Some(child) }
    }
    fn try_wait(&mut self) -> Result<Option<ExitStatus>, PaqSupervisorError> {
        self.child
            .as_mut()
            .expect("child remains armed")
            .try_wait()
            .map_err(PaqSupervisorError::Wait)
    }
    fn take_stdout(&mut self) -> Result<std::process::ChildStdout, PaqSupervisorError> {
        self.child
            .as_mut()
            .expect("child remains armed")
            .stdout
            .take()
            .ok_or(PaqSupervisorError::InvalidRequest(
                "worker stdout pipe unavailable",
            ))
    }
    fn take_stderr(&mut self) -> Result<std::process::ChildStderr, PaqSupervisorError> {
        self.child
            .as_mut()
            .expect("child remains armed")
            .stderr
            .take()
            .ok_or(PaqSupervisorError::InvalidRequest(
                "worker stderr pipe unavailable",
            ))
    }
    fn disarm(&mut self) {
        self.child.take();
    }
    fn terminate_and_collect(
        &mut self,
        stdout: JoinHandle<io::Result<CapturedStream>>,
        stderr: JoinHandle<io::Result<CapturedStream>>,
    ) -> Result<(CapturedStream, CapturedStream), PaqSupervisorError> {
        if let Some(mut child) = self.child.take() {
            // kill may race a normal exit; either way wait reaps the child.
            if let Err(error) = child.kill() {
                if error.kind() != io::ErrorKind::InvalidInput {
                    return Err(PaqSupervisorError::Wait(error));
                }
            }
            child.wait().map_err(PaqSupervisorError::Wait)?;
        }
        Ok((finish_capture(stdout)?, finish_capture(stderr)?))
    }
}

impl Drop for ChildCleanup {
    fn drop(&mut self) {
        if let Some(mut child) = self.child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

struct TemporaryOutput {
    directory: Option<PathBuf>,
    output: PathBuf,
}

impl TemporaryOutput {
    fn create(root: &Path) -> Result<Self, PaqSupervisorError> {
        validate_private_temporary_root(root)?;
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|_| PaqSupervisorError::InvalidRequest("system clock before Unix epoch"))?
            .as_nanos();
        for attempt in 0..TEMP_ATTEMPTS {
            let sequence = TEMP_SEQUENCE.fetch_add(1, Ordering::Relaxed);
            let directory = root.join(format!(
                ".cix-paq-{nanos}-{}-{sequence}-{attempt}",
                std::process::id()
            ));
            match create_private_directory(&directory) {
                Ok(()) => {
                    let output = directory.join("output");
                    return Ok(Self {
                        directory: Some(directory),
                        output,
                    });
                }
                Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
                Err(error) => return Err(PaqSupervisorError::OutputUnavailable(error)),
            }
        }
        Err(PaqSupervisorError::InvalidRequest(
            "cannot create unique PAQ temporary directory",
        ))
    }
    fn path(&self) -> &Path {
        &self.output
    }
    fn cleanup(&mut self) -> Result<(), PaqSupervisorError> {
        if let Some(directory) = self.directory.take() {
            fs::remove_dir_all(directory).map_err(PaqSupervisorError::Cleanup)?;
        }
        Ok(())
    }
}

#[cfg(unix)]
pub(crate) fn validate_private_temporary_root(root: &Path) -> Result<(), PaqSupervisorError> {
    use std::os::unix::fs::MetadataExt;

    let effective_uid = unsafe { libc::geteuid() };
    for ancestor in root.ancestors() {
        let metadata =
            fs::symlink_metadata(ancestor).map_err(PaqSupervisorError::OutputUnavailable)?;
        if metadata.file_type().is_symlink() || !metadata.is_dir() {
            return Err(PaqSupervisorError::InvalidRequest(
                "PAQ temporary root and every ancestor must be real directories",
            ));
        }
        let mode = metadata.mode();
        let owner = metadata.uid();
        if owner != effective_uid && owner != 0 {
            return Err(PaqSupervisorError::InvalidRequest(
                "PAQ temporary root has an untrusted ancestor owner",
            ));
        }
        // A sticky /tmp is still a shared namespace, so do not accept any
        // group/other-writable ancestor rather than relying on sticky-bit rules.
        if mode & 0o022 != 0 {
            return Err(PaqSupervisorError::InvalidRequest(
                "PAQ temporary root has a group/other-writable ancestor",
            ));
        }
    }
    let metadata = fs::symlink_metadata(root).map_err(PaqSupervisorError::OutputUnavailable)?;
    if metadata.uid() != effective_uid
        || metadata.mode() & 0o077 != 0
        || metadata.mode() & 0o700 != 0o700
    {
        return Err(PaqSupervisorError::InvalidRequest(
            "PAQ temporary root must be owned by this user and mode 0700",
        ));
    }
    Ok(())
}

#[cfg(not(unix))]
pub(crate) fn validate_private_temporary_root(_: &Path) -> Result<(), PaqSupervisorError> {
    Err(PaqSupervisorError::InvalidRequest(
        "PAQ supervisor temporary directories require a verified Unix private root",
    ))
}

#[cfg(unix)]
pub(crate) fn create_private_directory(path: &Path) -> io::Result<()> {
    use std::ffi::CString;
    use std::os::unix::ffi::OsStrExt;

    let text = CString::new(path.as_os_str().as_bytes())
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "NUL temporary path"))?;
    if unsafe { libc::mkdir(text.as_ptr(), 0o700) } == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

#[cfg(not(unix))]
fn create_private_directory(_: &Path) -> io::Result<()> {
    Err(io::Error::new(
        io::ErrorKind::Unsupported,
        "PAQ supervisor requires Unix private directory creation",
    ))
}

impl Drop for TemporaryOutput {
    fn drop(&mut self) {
        let _ = self.cleanup();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    struct IntegrationPaths {
        executable: PathBuf,
        libraries: PathBuf,
        work_root: PathBuf,
    }

    impl IntegrationPaths {
        /// Opt-in only. Supplying any but not every setting is a configuration
        /// failure, never a skipped lifecycle test.
        fn from_environment() -> Option<Self> {
            let executable = std::env::var_os("CIX_TEST_EXECUTABLE");
            let libraries = std::env::var_os("CIX_TEST_PAQ_LIBDIR");
            let work_root = std::env::var_os("CIX_TEST_PAQ_WORKROOT");
            match (executable, libraries, work_root) {
                (None, None, None) => None,
                (Some(executable), Some(libraries), Some(work_root)) => Some(Self {
                    executable: executable.into(),
                    libraries: libraries.into(),
                    work_root: work_root.into(),
                }),
                _ => panic!(
                    "set CIX_TEST_EXECUTABLE, CIX_TEST_PAQ_LIBDIR and CIX_TEST_PAQ_WORKROOT together"
                ),
            }
        }

        fn assert_staged(&self) {
            assert!(self.executable.is_absolute() && self.executable.is_file());
            assert!(self.libraries.is_absolute() && self.libraries.is_dir());
            assert!(self.work_root.is_absolute());
            validate_private_temporary_root(&self.work_root)
                .expect("test PAQ work root must be owned private mode 0700");
        }
    }

    struct TestDirectory(PathBuf);
    impl Drop for TestDirectory {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    fn private_test_directory(root: &Path, label: &str) -> TestDirectory {
        let path = root.join(format!(
            ".cix-parent-test-{label}-{}-{}",
            std::process::id(),
            TEMP_SEQUENCE.fetch_add(1, Ordering::Relaxed)
        ));
        create_private_directory(&path).expect("create private parent test directory");
        TestDirectory(path)
    }

    fn request(
        paths: &IntegrationPaths,
        variant: PaqVariant,
        operation: PaqOperation,
        input: PathBuf,
        input_limit: u64,
        output_limit: u64,
    ) -> PaqWorkerRequest {
        PaqWorkerRequest {
            paths: PaqWorkerPaths {
                cix_executable: paths.executable.clone(),
                private_library_directory: paths.libraries.clone(),
                temporary_root: paths.work_root.clone(),
            },
            variant,
            operation,
            input,
            input_limit_bytes: input_limit,
            output_limit_bytes: output_limit,
            parent_result_limit_bytes: usize::try_from(output_limit).unwrap(),
            memory_limit_bytes: 1 << 30,
            level: PaqLevel {
                number: 1,
                lstm: false,
            },
            lstm_layers: 1,
            joint_discount_mode: None,
            deadline: None,
            cancellation: None,
            diagnostic_limit_bytes: 64 << 10,
        }
    }

    fn assert_no_worker_directories(root: &Path) {
        for entry in fs::read_dir(root).expect("read private PAQ work root") {
            let entry = entry.expect("read private PAQ work-root entry");
            assert!(
                !entry.file_name().to_string_lossy().starts_with(".cix-paq-"),
                "supervisor left worker directory: {}",
                entry.path().display()
            );
        }
    }

    #[test]
    fn level_and_variant_arguments_are_closed_sets() {
        assert_eq!(
            PaqLevel {
                number: 12,
                lstm: true
            }
            .argument()
            .unwrap(),
            "-12L"
        );
        assert!(PaqLevel {
            number: 13,
            lstm: false
        }
        .argument()
        .is_err());
        assert_eq!(variant_argument(PaqVariant::StoreState), "store-state");
        assert_eq!(joint_argument(Some(3)), "3");
    }

    #[test]
    fn diagnostic_capture_drains_beyond_the_retained_cap() {
        let captured = capture_thread(Cursor::new(b"0123456789".to_vec()), 4)
            .join()
            .unwrap()
            .unwrap();
        assert_eq!(captured.bytes, b"0123");
        assert!(captured.truncated);
    }

    #[cfg(unix)]
    fn private_test_root(label: &str) -> PathBuf {
        // A source checkout may have group-writable ancestors. Keep the
        // positive lifecycle tests under the explicitly supplied private test
        // root, or the user's home, without weakening the product's policy.
        let base = std::env::var_os("CIX_TEST_PAQ_WORKROOT")
            .or_else(|| std::env::var_os("HOME"))
            .map(PathBuf::from)
            .expect("PAQ tests require a private CIX_TEST_PAQ_WORKROOT or HOME");
        let root = base.join(format!(
            ".cix-paq-supervisor-{label}-{}",
            std::process::id()
        ));
        create_private_directory(&root).unwrap();
        validate_private_temporary_root(&root).unwrap();
        root
    }

    #[cfg(unix)]
    #[test]
    fn temporary_output_cleanup_removes_private_directory() {
        let root = private_test_root("cleanup");
        let mut temporary = TemporaryOutput::create(&root).unwrap();
        let directory = temporary.directory.clone().unwrap();
        fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(temporary.path())
            .unwrap();
        temporary.cleanup().unwrap();
        assert!(!directory.exists());
        fs::remove_dir(&root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn private_root_rejects_a_symlink_and_keeps_shared_temp_out_of_scope() {
        use std::os::unix::fs::symlink;

        let root = private_test_root("symlink");
        let link = root
            .parent()
            .unwrap()
            .join(format!(".cix-paq-supervisor-link-{}", std::process::id()));
        symlink(&root, &link).unwrap();
        assert!(validate_private_temporary_root(&link).is_err());
        fs::remove_file(&link).unwrap();
        fs::remove_dir(&root).unwrap();
    }

    #[test]
    fn result_read_never_allocates_past_parent_reservation() {
        let path = std::env::current_dir()
            .unwrap()
            .join(format!(".cix-paq-result-{}", std::process::id()));
        fs::write(&path, b"12345").unwrap();
        let request = PaqWorkerRequest {
            paths: PaqWorkerPaths {
                cix_executable: PathBuf::from("/unused"),
                private_library_directory: PathBuf::from("/unused"),
                temporary_root: PathBuf::from("/unused"),
            },
            variant: PaqVariant::V215,
            operation: PaqOperation::Encode,
            input: PathBuf::from("/unused"),
            input_limit_bytes: 1,
            output_limit_bytes: 4,
            parent_result_limit_bytes: 4,
            memory_limit_bytes: 1,
            level: PaqLevel {
                number: 1,
                lstm: false,
            },
            lstm_layers: 1,
            joint_discount_mode: None,
            deadline: None,
            cancellation: None,
            diagnostic_limit_bytes: 1,
        };
        assert!(matches!(
            read_result(&path, 5, &request),
            Err(PaqSupervisorError::OutputTooLarge {
                actual: 5,
                limit: 4
            })
        ));
        fs::remove_file(path).unwrap();
    }

    /// This test is intentionally disabled unless root stages a fresh CIX
    /// executable, all four CIX-built PAQ DSOs, and a verified private work
    /// root. These environment variables are test-only and never enter the
    /// product request API or runtime environment policy.
    #[cfg(unix)]
    #[test]
    fn opt_in_parent_lifecycle_exercises_all_packaged_variants() {
        let Some(paths) = IntegrationPaths::from_environment() else {
            return;
        };
        paths.assert_staged();
        let directory = private_test_directory(&paths.work_root, "lifecycle");
        let source: Vec<u8> = (0..2112)
            .map(|index| ((index * 37) ^ (index >> 3) ^ 0x5a) as u8)
            .collect();
        let input = directory.0.join("source.bin");
        fs::write(&input, &source).unwrap();
        let variants = [
            PaqVariant::V215,
            PaqVariant::V216,
            PaqVariant::JointDiscount,
            PaqVariant::StoreState,
        ];
        for variant in variants {
            let encoded = run(&request(
                &paths,
                variant,
                PaqOperation::Encode,
                input.clone(),
                source.len() as u64,
                16 << 20,
            ))
            .unwrap_or_else(|error| panic!("{variant:?} parent encode failed: {error}"));
            let archive = directory.0.join(format!("{variant:?}.paq"));
            fs::write(&archive, &encoded.output).unwrap();
            let decoded = run(&request(
                &paths,
                variant,
                PaqOperation::Decode,
                archive,
                encoded.output.len() as u64,
                source.len() as u64,
            ))
            .unwrap_or_else(|error| panic!("{variant:?} fresh parent decode failed: {error}"));
            assert_eq!(decoded.output, source, "{variant:?} parent round trip");
            assert_no_worker_directories(&paths.work_root);
        }

        let capped = request(
            &paths,
            PaqVariant::V215,
            PaqOperation::Encode,
            input.clone(),
            source.len() as u64,
            1,
        );
        assert!(
            run(&capped).is_err(),
            "one-byte output cap must not report a successful PAQ encode"
        );
        assert_no_worker_directories(&paths.work_root);

        let mut cancelled = request(
            &paths,
            PaqVariant::V216,
            PaqOperation::Encode,
            input.clone(),
            source.len() as u64,
            16 << 20,
        );
        cancelled.cancellation = Some(Arc::new(AtomicBool::new(true)));
        assert!(matches!(
            run(&cancelled),
            Err(PaqSupervisorError::Cancelled)
        ));
        assert_no_worker_directories(&paths.work_root);

        let mut expired = request(
            &paths,
            PaqVariant::StoreState,
            PaqOperation::Encode,
            input,
            source.len() as u64,
            16 << 20,
        );
        expired.deadline = Some(Instant::now());
        assert!(matches!(
            run(&expired),
            Err(PaqSupervisorError::DeadlineExceeded)
        ));
        assert_no_worker_directories(&paths.work_root);
    }
}
