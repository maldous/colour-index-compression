//! Public CLI checks for automatic, bounded whole-archive BEST selection.

use std::fs;
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};

static SERIAL: AtomicUsize = AtomicUsize::new(0);

struct TempPath(std::path::PathBuf);

impl TempPath {
    fn new(suffix: &str) -> Self {
        let serial = SERIAL.fetch_add(1, Ordering::Relaxed);
        Self(std::env::temp_dir().join(format!(
            "cix-auto-best-{}-{serial}-{suffix}",
            std::process::id()
        )))
    }
}

impl Drop for TempPath {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

fn cix(args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_cix"))
        .args(args)
        .output()
        .expect("run cix")
}

fn uncix(archive: &std::path::Path) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_uncix"))
        .args(["-c", archive.to_str().expect("UTF-8 temp path")])
        .output()
        .expect("run uncix")
}

#[test]
fn named_best_compares_complete_archives_and_fresh_cli_decodes() {
    let input = TempPath::new("input");
    let archive = TempPath::new("archive.cix");
    let mut source = Vec::new();
    for _ in 0..512 {
        source.extend_from_slice(b"The quick brown fox jumps over the lazy dog. ");
    }
    fs::write(&input.0, &source).expect("write input");
    let output = cix(&[
        "--best",
        "--threads",
        "2",
        "--memory",
        "512MiB",
        "--verbose",
        "-o",
        archive.0.to_str().expect("UTF-8 temp path"),
        input.0.to_str().expect("UTF-8 temp path"),
    ]);
    assert!(
        output.status.success(),
        "BEST failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("whole_archive=yes"), "{stderr}");
    for descriptor in cix_native::external::best_candidates() {
        let candidate = descriptor.id;
        assert!(
            stderr.contains(&format!("packaging_candidate={candidate}"))
                || stderr.contains(&format!("{candidate} (")),
            "BEST neither evaluated nor reported {candidate}: {stderr}"
        );
    }
    let bytes = fs::read(&archive.0).expect("archive exists");
    let selected = stderr
        .split("selected=")
        .nth(1)
        .and_then(|tail| tail.split_whitespace().next())
        .expect("BEST selected candidate");
    if let Some(descriptor) = cix_native::external::best_candidates()
        .iter()
        .find(|descriptor| descriptor.id == selected)
    {
        assert!(bytes.starts_with(b"CIXB1"), "CIXB1 archive magic");
        assert_eq!(
            bytes,
            descriptor
                .full_archive_encode(&source)
                .expect("direct complete selected CIXB1 archive"),
            "BEST selected exact complete CIXB1 archive"
        );
    } else {
        assert!(
            selected == "cixg2:native-auto",
            "unknown BEST winner {selected}"
        );
        assert!(bytes.starts_with(b"CIXG2"), "native winner magic");
    }
    let restored = uncix(&archive.0);
    assert!(
        restored.status.success(),
        "fresh decoder failed: {}",
        String::from_utf8_lossy(&restored.stderr)
    );
    assert_eq!(restored.stdout, source);
}

#[test]
fn canonical_direct_bzip2_is_a_deterministic_complete_cixb1_archive() {
    let source = b"canonical bzip2 CIXB1 fixture\n".repeat(256);
    let first =
        cix_native::external::encode("bzip2", "size", &source).expect("direct bzip2 archive");
    let second = cix_native::external::encode("bzip2", "size", &source)
        .expect("repeat direct bzip2 archive");
    assert_eq!(first, second, "canonical direct bzip2 bytes");
    assert_eq!(&first[..5], b"CIXB1");
    assert_eq!(first[5], 2, "CIXB1 bzip2 backend identifier");
    assert_eq!(first[6], 3, "CIXB1 size profile identifier");
}

#[test]
fn streaming_best_reports_whole_archive_exclusion_and_stays_framed() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_cix"))
        .args(["--best", "--stream", "--verbose", "-c", "-"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn cix");
    use std::io::Write;
    child
        .stdin
        .take()
        .expect("stdin")
        .write_all(b"stream-only fixture")
        .expect("write input");
    let output = child.wait_with_output().expect("collect cix");
    assert!(
        output.status.success(),
        "streaming BEST failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stdout.starts_with(b"CIXG"));
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("whole_archive=no"),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
}
