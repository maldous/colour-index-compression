//! Same-executable job-mode smoke coverage.  It becomes active with root's
//! registration of `job_cli` in `cix`'s product entry point.

use cix_native::full_engine::job_protocol::{self, ControlRecord, JobErrorCode};
use std::{
    fs,
    io::{Cursor, Write},
    process::{Command, Stdio},
    time::{SystemTime, UNIX_EPOCH},
};

struct Fixture {
    root: std::path::PathBuf,
    input: std::path::PathBuf,
    output: std::path::PathBuf,
    library: std::path::PathBuf,
    temporary: std::path::PathBuf,
}

impl Fixture {
    fn new(label: &str) -> Self {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock after epoch")
            .as_nanos();
        let root = std::env::temp_dir().join(format!(
            "cix-job-cli-{label}-{}-{nonce}",
            std::process::id()
        ));
        let library = root.join("private-library");
        let temporary = root.join("temporary");
        fs::create_dir_all(&library).expect("private library directory");
        fs::create_dir_all(&temporary).expect("temporary directory");
        let input = root.join("input.cix");
        fs::write(&input, b"fixture input").expect("fixture input");
        let output = root.join("output.bin");
        Self {
            root,
            input,
            output,
            library,
            temporary,
        }
    }

    fn command(&self) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_cix"));
        command.args([
            "--cix-job-v1",
            "--input",
            self.input.to_str().expect("utf8 input"),
            "--output",
            self.output.to_str().expect("utf8 output"),
            "--private-library-dir",
            self.library.to_str().expect("utf8 library"),
            "--temporary-root",
            self.temporary.to_str().expect("utf8 temporary"),
        ]);
        command
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

fn error_record(bytes: Vec<u8>) -> cix_native::full_engine::job_protocol::JobError {
    let ControlRecord::Error(error) =
        job_protocol::read_control(&mut Cursor::new(bytes)).expect("control error record")
    else {
        panic!("expected error control record");
    };
    error
}

#[test]
fn capabilities_are_a_single_bounded_control_record() {
    let output = Command::new(env!("CARGO_BIN_EXE_cix"))
        .arg("--cix-job-capabilities-v1")
        .output()
        .expect("start cix job capability command");
    assert!(output.status.success());
    assert!(output.stderr.is_empty());
    let mut wire = Cursor::new(output.stdout);
    let record = job_protocol::read_control(&mut wire).expect("bounded job capability record");
    let ControlRecord::Capability(capability) = record else {
        panic!("capability command emitted another record");
    };
    assert!(capability.select_whole_input);
    assert!(capability.decode_archive);
    assert!(capability.data_transport.contains("128 MiB"));
    assert_eq!(wire.position() as usize, wire.get_ref().len());
}

#[test]
fn existing_output_is_never_overwritten_or_staged() {
    let fixture = Fixture::new("no-overwrite");
    fs::write(&fixture.output, b"preserve this").expect("existing output");
    let result = fixture
        .command()
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("start cix job");
    assert!(!result.status.success());
    assert!(result.stderr.is_empty());
    let error = error_record(result.stdout);
    assert_eq!(error.request_id, 0);
    assert_eq!(error.code, JobErrorCode::InvalidRequest);
    assert_eq!(
        fs::read(&fixture.output).expect("existing output"),
        b"preserve this"
    );
    assert!(fs::read_dir(&fixture.root)
        .expect("fixture root")
        .all(|entry| !entry
            .expect("entry")
            .file_name()
            .to_string_lossy()
            .starts_with(".cix-job-")));
}

#[test]
fn malformed_initial_control_never_creates_output_or_temporary() {
    let fixture = Fixture::new("malformed");
    let mut child = fixture
        .command()
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("start cix job");
    child
        .stdin
        .as_mut()
        .expect("child stdin")
        .write_all(b"not a CJB1 control record")
        .expect("malformed request");
    drop(child.stdin.take());
    let result = child.wait_with_output().expect("wait for cix job");
    assert!(!result.status.success());
    assert!(result.stderr.is_empty());
    let error = error_record(result.stdout);
    assert_eq!(error.request_id, 0);
    assert_eq!(error.code, JobErrorCode::Protocol);
    assert!(!fixture.output.exists());
    assert!(fs::read_dir(&fixture.root)
        .expect("fixture root")
        .all(|entry| !entry
            .expect("entry")
            .file_name()
            .to_string_lossy()
            .starts_with(".cix-job-")));
}

#[test]
fn decode_staging_cap_is_admitted_before_output_creation() {
    use cix_native::{
        core::{self, NativeOptions},
        full_engine::job_protocol::{JobLimits, JobOperation, JobProfile, JobRequest},
    };

    let fixture = Fixture::new("staging-cap");
    let source = b"staging cap fixture".repeat(16);
    let archive = core::encode_buffer(&source, &NativeOptions::default()).expect("raw archive");
    fs::write(&fixture.input, &archive).expect("archive input");
    let request = JobRequest {
        request_id: 42,
        operation: JobOperation::DecodeArchive,
        profile: JobProfile::Default,
        limits: JobLimits {
            input_bytes: archive.len(),
            archive_bytes: archive.len(),
            output_bytes: source.len(),
            memory_bytes: 128 << 20,
            intermediate_bytes: 128 << 20,
            temporary_bytes: source.len() - 1,
            workers: 1,
            deadline_millis: None,
        },
        diagnostics: false,
    };
    let mut child = fixture
        .command()
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("start cix job");
    job_protocol::write_control(
        child.stdin.as_mut().expect("child stdin"),
        &ControlRecord::Request(request),
    )
    .expect("write request");
    drop(child.stdin.take());
    let result = child.wait_with_output().expect("wait for cix job");
    assert!(!result.status.success());
    assert!(result.stderr.is_empty());
    let error = error_record(result.stdout);
    assert_eq!(error.request_id, 42);
    assert_eq!(error.code, JobErrorCode::ResourceLimit);
    assert!(!fixture.output.exists());
    assert!(fs::read_dir(&fixture.root)
        .expect("fixture root")
        .all(|entry| !entry
            .expect("entry")
            .file_name()
            .to_string_lossy()
            .starts_with(".cix-job-")));
}

#[test]
fn decode_job_restores_a_raw_archive_to_the_private_output_file() {
    use cix_native::{
        core::{self, NativeOptions},
        full_engine::job_protocol::{JobLimits, JobOperation, JobProfile, JobRequest, JobStage},
    };
    let fixture = Fixture::new("decode");
    let source = b"job protocol raw archive fixture".repeat(32);
    let archive = core::encode_buffer(&source, &NativeOptions::default()).expect("raw archive");
    fs::write(&fixture.input, &archive).expect("archive input");
    let request = JobRequest {
        request_id: 41,
        operation: JobOperation::DecodeArchive,
        profile: JobProfile::Default,
        limits: JobLimits {
            input_bytes: archive.len(),
            archive_bytes: archive.len(),
            output_bytes: source.len(),
            memory_bytes: 128 << 20,
            intermediate_bytes: 128 << 20,
            temporary_bytes: 1 << 20,
            workers: 1,
            deadline_millis: None,
        },
        diagnostics: false,
    };
    let mut child = fixture
        .command()
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("start cix decode job");
    job_protocol::write_control(
        child.stdin.as_mut().expect("child stdin"),
        &ControlRecord::Request(request),
    )
    .expect("write request");
    drop(child.stdin.take());
    let result = child.wait_with_output().expect("wait for cix decode job");
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    assert!(result.stderr.is_empty());
    assert_eq!(fs::read(&fixture.output).expect("restored output"), source);

    let mut wire = Cursor::new(result.stdout);
    let mut saw_output = false;
    let mut final_result = None;
    while (wire.position() as usize) < wire.get_ref().len() {
        match job_protocol::read_control(&mut wire).expect("job control record") {
            ControlRecord::Progress(progress) if progress.stage == JobStage::OutputWritten => {
                saw_output = true
            }
            ControlRecord::Result(value) => final_result = Some(value),
            _ => {}
        }
    }
    let final_result = final_result.expect("job result");
    assert_eq!(final_result.output_bytes, source.len());
    assert!(matches!(
        final_result.decode_path.as_deref(),
        Some("native-incremental" | "native-core-buffered")
    ));
    assert!(saw_output);
}
