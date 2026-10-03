//! Stand-alone, frozen RSL1 experiment driver.  Deliberately outside src/: it
//! cannot change CIX selection or its on-disk formats.
//!
//! Compile only under a scheduler lease, for example:
//! rustc --edition=2021 -O experiments/representation-search-v1/main.rs -o /tmp/rsl1
//! The driver delegates coding to a supplied, immutable `cix` / `uncix` pair.

use std::{env, fs, io::{self, Read, Write}, path::{Path, PathBuf}, process::{Child, Command, Stdio}, sync::mpsc, thread, time::{Duration, Instant}};

const MAGIC: &[u8; 4] = b"RSL1";
const VERSION: u8 = 2;
const MAX_DEPTH: usize = 2;
const MAX_INPUT: u64 = 64 * 1024 * 1024;
const MAX_TRANSFORM_BYTES: u64 = 128 * 1024 * 1024;
const SCREEN_INPUT: u64 = 8 * 1024;
const MAX_TEMP: u64 = 3_000_000_000;
const MAX_ARCHIVE: u64 = MAX_TRANSFORM_BYTES + 64;
const MAX_BACKEND_FILE_BLOCKS: u64 = MAX_TRANSFORM_BYTES / 512;
const MAX_CHILD_WALL: Duration = Duration::from_secs(60);
const PIPE_QUEUE: usize = 4;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Op { Identity, Transpose(u8), Delta(u8), Xor(u8), Residual(u8), Literal }

impl Op {
    fn encoded(self) -> (u8, u8) { match self {
        Self::Identity => (0, 0), Self::Transpose(n) => (1, n), Self::Delta(n) => (2, n),
        Self::Xor(n) => (3, n), Self::Residual(n) => (4, n), Self::Literal => (5, 0),
    }}
    fn name(self) -> String { match self {
        Self::Identity => "identity".into(), Self::Transpose(n) => format!("transpose-{n}"),
        Self::Delta(n) => format!("mod-delta-{n}"), Self::Xor(n) => format!("xor-{n}"),
        Self::Residual(n) => format!("previous-stride-residual-{n}"), Self::Literal => "literal".into(),
    }}
    fn from_encoded(tag: u8, arg: u8) -> Result<Self, String> { match (tag, arg) {
        (0, 0) => Ok(Self::Identity), (1, 2 | 4 | 8 | 16) => Ok(Self::Transpose(arg)),
        (2, 1 | 4 | 8 | 16) => Ok(Self::Delta(arg)), (3, 1 | 4 | 8 | 16) => Ok(Self::Xor(arg)),
        (4, 1 | 4 | 8 | 16) => Ok(Self::Residual(arg)), (5, 0) => Ok(Self::Literal),
        _ => Err("invalid RSL1 operation".into()),
    }}
}

fn apply(op: Op, input: &[u8]) -> Vec<u8> { match op {
    Op::Identity | Op::Literal => input.to_vec(),
    Op::Transpose(lanes) => {
        let lanes = lanes as usize; let mut out = Vec::with_capacity(input.len());
        for lane in 0..lanes { for i in (lane..input.len()).step_by(lanes) { out.push(input[i]); } }
        out
    }
    Op::Delta(lag) | Op::Residual(lag) => {
        let lag = lag as usize; input.iter().enumerate().map(|(i, &b)| b.wrapping_sub(if i < lag { 0 } else { input[i - lag] })).collect()
    }
    Op::Xor(lag) => { let lag = lag as usize; input.iter().enumerate().map(|(i, &b)| b ^ if i < lag { 0 } else { input[i - lag] }).collect() }
}}

fn invert(op: Op, input: &[u8], original_len: usize) -> Result<Vec<u8>, String> { match op {
    Op::Identity | Op::Literal => Ok(input.to_vec()),
    Op::Transpose(lanes) => {
        let lanes = lanes as usize; let mut out = vec![0; original_len]; let mut p = 0;
        for lane in 0..lanes { for i in (lane..original_len).step_by(lanes) { out[i] = *input.get(p).ok_or("short transpose")?; p += 1; } }
        if p != input.len() { return Err("long transpose".into()); } Ok(out)
    }
    Op::Delta(lag) | Op::Residual(lag) => {
        let lag = lag as usize; let mut out = Vec::with_capacity(input.len());
        for (i, &b) in input.iter().enumerate() { out.push(b.wrapping_add(if i < lag { 0 } else { out[i - lag] })); } Ok(out)
    }
    Op::Xor(lag) => { let lag = lag as usize; let mut out = Vec::with_capacity(input.len()); for (i, &b) in input.iter().enumerate() { out.push(b ^ if i < lag { 0 } else { out[i - lag] }); } Ok(out) }
}}

fn transform(program: &[Op], input: &[u8]) -> Vec<u8> { program.iter().fold(input.to_vec(), |bytes, &op| apply(op, &bytes)) }
fn restore(program: &[Op], payload: &[u8], original_len: usize) -> Result<Vec<u8>, String> {
    let mut bytes = payload.to_vec(); for &op in program.iter().rev() { bytes = invert(op, &bytes, original_len)?; } Ok(bytes)
}

fn put_u64(out: &mut Vec<u8>, value: u64) { out.extend_from_slice(&value.to_le_bytes()); }
fn put_u32(out: &mut Vec<u8>, value: u32) { out.extend_from_slice(&value.to_le_bytes()); }
fn take_u64(data: &[u8], pos: &mut usize) -> Result<u64, String> { let end = pos.checked_add(8).ok_or("RSL1 length overflow")?; let b: [u8; 8] = data.get(*pos..end).ok_or("truncated RSL1 length")?.try_into().map_err(|_| "bad RSL1 length")?; *pos = end; Ok(u64::from_le_bytes(b)) }
fn take_u32(data: &[u8], pos: &mut usize) -> Result<u32, String> { let end = pos.checked_add(4).ok_or("RSL1 CRC overflow")?; let b: [u8; 4] = data.get(*pos..end).ok_or("truncated RSL1 CRC")?.try_into().map_err(|_| "bad RSL1 CRC")?; *pos = end; Ok(u32::from_le_bytes(b)) }
fn crc32(data: &[u8]) -> u32 { let mut crc = !0u32; for &byte in data { crc ^= byte as u32; for _ in 0..8 { crc = (crc >> 1) ^ (0xedb8_8320 & 0u32.wrapping_sub(crc & 1)); } } !crc }
fn read_limited(path: &Path, limit: u64, label: &str) -> Result<Vec<u8>, String> { let file = fs::File::open(path).map_err(|e| e.to_string())?; let meta = file.metadata().map_err(|e| e.to_string())?; if !meta.is_file() || meta.len() > limit { return Err(format!("{label} exceeds byte limit")); } let mut data = Vec::with_capacity(meta.len() as usize); file.take(limit.checked_add(1).ok_or("byte limit overflow")?).read_to_end(&mut data).map_err(|e| e.to_string())?; if data.len() as u64 > limit { return Err(format!("{label} exceeds byte limit")); } Ok(data) }
fn frame(program: &[Op], backend: u8, source_len: usize, coded: &[u8]) -> Result<Vec<u8>, String> {
    if program.len() > MAX_DEPTH { return Err("RSL1 depth bound".into()); }
    if backend > 1 { return Err("invalid RSL1 backend".into()); }
    let mut out = Vec::with_capacity(4 + 1 + 1 + 1 + 8 + 8 + program.len() * 2 + coded.len());
    out.extend_from_slice(MAGIC); out.push(VERSION); out.push(program.len() as u8); out.push(backend); put_u64(&mut out, source_len as u64); put_u64(&mut out, coded.len() as u64);
    for &op in program { let (tag, arg) = op.encoded(); out.push(tag); out.push(arg); } out.extend_from_slice(coded); let checksum = crc32(&out); put_u32(&mut out, checksum); Ok(out)
}
fn unframe(archive: &[u8]) -> Result<(Vec<Op>, u8, usize, &[u8]), String> {
    if archive.len() as u64 > MAX_ARCHIVE { return Err("RSL1 archive byte cap".into()); }
    if archive.get(..4) != Some(MAGIC) || archive.get(4) != Some(&VERSION) { return Err("not RSL1 version 2".into()); }
    let count = *archive.get(5).ok_or("truncated RSL1")? as usize; if count > MAX_DEPTH { return Err("RSL1 depth bound".into()); }
    let backend = *archive.get(6).ok_or("truncated RSL1 backend")?; if backend > 1 { return Err("unsupported RSL1 backend".into()); } let mut p = 7; let source_len = usize::try_from(take_u64(archive, &mut p)?).map_err(|_| "source too long")?; let coded_len = usize::try_from(take_u64(archive, &mut p)?).map_err(|_| "coded too long")?; if source_len as u64 > MAX_INPUT || coded_len as u64 > MAX_TRANSFORM_BYTES { return Err("RSL1 length cap".into()); }
    let mut ops = Vec::with_capacity(count); for _ in 0..count { ops.push(Op::from_encoded(*archive.get(p).ok_or("truncated opcode")?, *archive.get(p + 1).ok_or("truncated op argument")?)?); p += 2; }
    let end = p.checked_add(coded_len).ok_or("RSL1 coded length overflow")?; let crc_end = end.checked_add(4).ok_or("RSL1 CRC length overflow")?; if crc_end != archive.len() { return Err("RSL1 coded length mismatch".into()); } let mut crc_pos = end; let stored = take_u32(archive, &mut crc_pos)?; if stored != crc32(&archive[..end]) { return Err("RSL1 CRC mismatch".into()); } if backend == 1 && ops != vec![Op::Literal] { return Err("raw fallback must be literal".into()); } Ok((ops, backend, source_len, &archive[7 + 16 + count * 2..end]))
}

fn candidates() -> Vec<Vec<Op>> {
    let atoms = [Op::Identity, Op::Literal, Op::Transpose(2), Op::Transpose(4), Op::Transpose(8), Op::Transpose(16), Op::Delta(1), Op::Delta(4), Op::Delta(8), Op::Delta(16), Op::Xor(1), Op::Xor(4), Op::Xor(8), Op::Xor(16), Op::Residual(1), Op::Residual(4), Op::Residual(8), Op::Residual(16)];
    let mut out: Vec<Vec<Op>> = atoms.iter().copied().map(|x| vec![x]).collect();
    // Complete declared depth-two Cartesian product.  No size estimate or expansion rule prunes it.
    for first in atoms { for second in atoms { if !matches!(first, Op::Literal) && !matches!(second, Op::Literal) { out.push(vec![first, second]); } } } out
}
fn screen_candidates() -> Vec<Vec<Op>> { vec![
    vec![Op::Identity], vec![Op::Literal], vec![Op::Transpose(4)], vec![Op::Delta(1)],
    vec![Op::Delta(4)], vec![Op::Xor(1)], vec![Op::Xor(4)], vec![Op::Residual(1)],
    vec![Op::Residual(4)], vec![Op::Transpose(4), Op::Delta(4)],
    vec![Op::Delta(4), Op::Transpose(4)], vec![Op::Xor(4), Op::Transpose(4)],
] }
fn program_text(program: &[Op]) -> String { program.iter().map(|x| x.name()).collect::<Vec<_>>().join("+") }
fn quote_json(s: &str) -> String { format!("\"{}\"", s.replace('\\', "\\\\").replace('\"', "\\\"").replace('\n', "\\n")) }
fn sha256(path: &Path) -> Result<String, String> { let output = Command::new("sha256sum").arg(path).output().map_err(|e| e.to_string())?; if !output.status.success() { return Err(format!("sha256sum failed for {}", path.display())); } String::from_utf8(output.stdout).map_err(|e| e.to_string())?.split_whitespace().next().map(str::to_owned).ok_or_else(|| "missing sha256".to_string()) }
fn toolchain() -> Result<String, String> { let output = Command::new("rustc").arg("--version").output().map_err(|e| e.to_string())?; if !output.status.success() { return Err("rustc --version failed".into()); } Ok(String::from_utf8(output.stdout).map_err(|e| e.to_string())?.trim().to_owned()) }
fn git_revision() -> Result<String, String> { let output = Command::new("git").args(["rev-parse", "HEAD"]).output().map_err(|e| e.to_string())?; if !output.status.success() { return Err("git rev-parse HEAD failed".into()); } Ok(String::from_utf8(output.stdout).map_err(|e| e.to_string())?.trim().to_owned()) }
fn dir_bytes(path: &Path) -> io::Result<u64> { let mut n = 0; for entry in fs::read_dir(path)? { let entry = entry?; let meta = entry.metadata()?; if meta.is_dir() { n += dir_bytes(&entry.path())?; } else { n += meta.len(); } } Ok(n) }
fn kill_wait(child: &mut Child) { let group = format!("-{}", child.id()); let _ = Command::new("/bin/kill").args(["-TERM", "--", &group]).status(); thread::sleep(Duration::from_secs(1)); let _ = Command::new("/bin/kill").args(["-KILL", "--", &group]).status(); let _ = child.wait(); }
fn timed(program: &Path, args: Vec<std::ffi::OsString>, time_log: &Path, stdout: Stdio) -> Result<Child, String> { Command::new("setsid").arg("/usr/bin/time").args(["-v", "-o"]).arg(time_log).arg("--").arg("/usr/bin/timeout").args(["--foreground", "--kill-after=1s", "60s"]).arg(program).args(args).stdout(stdout).stderr(Stdio::null()).spawn().map_err(|e| e.to_string()) }
fn run(command: Command, time_log: &Path) -> Result<(Duration, u64), String> { let program = PathBuf::from(command.get_program()); let args: Vec<_> = command.get_args().map(|x| x.to_os_string()).collect(); let start = Instant::now(); let mut child = timed(&program, args, time_log, Stdio::null())?; let status = loop { match child.try_wait() { Ok(Some(status)) => break status, Ok(None) => {}, Err(error) => { kill_wait(&mut child); return Err(error.to_string()); } } if start.elapsed() > MAX_CHILD_WALL { kill_wait(&mut child); return Err("native child wall-time limit exceeded".into()); } thread::sleep(Duration::from_millis(5)); }; if !status.success() { return Err(format!("native coder exited {status}")); } let log = fs::read_to_string(time_log).map_err(|e| e.to_string())?; let kib = log.lines().find_map(|line| line.strip_prefix("\tMaximum resident set size (kbytes): ").and_then(|v| v.trim().parse::<u64>().ok())).ok_or("GNU time did not report maximum RSS")?; Ok((start.elapsed(), kib * 1024)) }
fn code(cix: &Path, input: &Path, output: &Path, profile: &str, time_log: &Path) -> Result<(Duration, u64), String> { let mut c = Command::new("/bin/sh"); c.arg("-c").arg("ulimit -f \"$1\"; shift; exec \"$@\"").arg("rsl1-file-limit").arg(MAX_BACKEND_FILE_BLOCKS.to_string()).arg(cix).args(["-k", "-f", "--threads", "1", "--memory", "512MiB", "--format", "cixg1", "--profile", profile, "-o"]).arg(output).arg(input); run(c, time_log) }
fn decode(uncix: &Path, input: &Path, output: &Path, expected_bytes: usize, time_log: &Path) -> Result<(Duration, u64), String> {
    let start = Instant::now(); let args = vec!["-c".into(), "--memory".into(), "512MiB".into(), input.as_os_str().to_os_string()]; let mut child = timed(uncix, args, time_log, Stdio::piped())?;
    let mut source = match child.stdout.take() { Some(source) => source, None => { kill_wait(&mut child); return Err("missing decoder stdout".into()); } }; let (sender, receiver) = mpsc::sync_channel(PIPE_QUEUE); let reader = thread::spawn(move || { loop { let mut buffer = vec![0u8; 8192]; match source.read(&mut buffer) { Ok(0) => break, Ok(n) => { buffer.truncate(n); if sender.send(Ok(buffer)).is_err() { break; } }, Err(error) => { let _ = sender.send(Err(error)); break; } } } }); let mut file = match fs::File::create(output) { Ok(file) => file, Err(error) => { kill_wait(&mut child); drop(receiver); let _ = reader.join(); return Err(error.to_string()); } }; let mut total = 0usize;
    loop { let remaining = MAX_CHILD_WALL.checked_sub(start.elapsed()).ok_or("native decoder wall-time limit exceeded"); let message = match remaining { Ok(remaining) => receiver.recv_timeout(remaining), Err(error) => { kill_wait(&mut child); drop(receiver); let _ = reader.join(); return Err(error.into()); } }; match message { Ok(Ok(buffer)) => { total = match total.checked_add(buffer.len()) { Some(total) => total, None => { kill_wait(&mut child); drop(receiver); let _ = reader.join(); return Err("decoded length overflow".into()); } }; if total > expected_bytes { kill_wait(&mut child); drop(receiver); let _ = reader.join(); return Err("decoded output exceeds stored source length".into()); } if let Err(error) = file.write_all(&buffer) { kill_wait(&mut child); drop(receiver); let _ = reader.join(); return Err(error.to_string()); } }, Ok(Err(error)) => { kill_wait(&mut child); drop(receiver); let _ = reader.join(); return Err(error.to_string()); }, Err(mpsc::RecvTimeoutError::Timeout) => { kill_wait(&mut child); drop(receiver); let _ = reader.join(); return Err("native decoder wall-time limit exceeded".into()); }, Err(mpsc::RecvTimeoutError::Disconnected) => break } }
    drop(receiver); let _ = reader.join(); let status = loop { match child.try_wait() { Ok(Some(status)) => break status, Ok(None) => {}, Err(error) => { kill_wait(&mut child); return Err(error.to_string()); } } if start.elapsed() > MAX_CHILD_WALL { kill_wait(&mut child); return Err("native decoder wall-time limit exceeded".into()); } thread::sleep(Duration::from_millis(5)); }; if !status.success() { return Err(format!("native decoder exited {status}")); } if total != expected_bytes { return Err("decoded output length differs from stored source length".into()); } let log = fs::read_to_string(time_log).map_err(|e| e.to_string())?; let kib = log.lines().find_map(|line| line.strip_prefix("\tMaximum resident set size (kbytes): ").and_then(|v| v.trim().parse::<u64>().ok())).ok_or("GNU time did not report maximum RSS")?; Ok((start.elapsed(), kib * 1024))
}

fn main() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.len() == 2 && args[1] == "--self-describe" { println!("RSL1 v2: screen=12 FAST candidates at 8KiB; full=307 candidates; depth<=2; CRC-protected frame; 64MiB full cap; native CIXG1 plus raw literal fallback."); return Ok(()); }
    if args.len() == 5 && args[1] == "decode" { let archive = read_limited(Path::new(&args[2]), MAX_ARCHIVE, "RSL1 archive")?; let (program, backend, source_len, payload) = unframe(&archive)?; let plain = if backend == 1 { payload.to_vec() } else { let native_archive = PathBuf::from(&args[3]).with_extension("rsl1-payload.cix"); let native = PathBuf::from(&args[3]).with_extension("rsl1-native"); fs::write(&native_archive, payload).map_err(|e| e.to_string())?; decode(Path::new(&args[4]), &native_archive, &native, source_len, &native.with_extension("time"))?; read_limited(&native, source_len as u64, "decoded native payload")? }; let restored = restore(&program, &plain, source_len)?; if restored.len() != source_len { return Err("outer decoded length mismatch".into()); } fs::write(&args[3], restored).map_err(|e| e.to_string())?; return Ok(()); }
    if args.len() != 8 { return Err("usage: rsl1 screen|full INPUT OUTPUT REPORT CIX UNCIX fast|default|size".into()); }
    let mode = &args[1]; let input = PathBuf::from(&args[2]); let output = PathBuf::from(&args[3]); let report = PathBuf::from(&args[4]); let cix = PathBuf::from(&args[5]); let uncix = PathBuf::from(&args[6]); let profile = &args[7];
    if !matches!(profile.as_str(), "fast" | "default" | "size") { return Err("profile must be fast, default, or size".into()); }
    if !matches!(mode.as_str(), "screen" | "full") { return Err("mode must be screen or full".into()); } if mode == "screen" && profile != "fast" { return Err("the frozen screen only permits fast".into()); }
    let source = read_limited(&input, MAX_INPUT, "input")?; if mode == "screen" && source.len() as u64 > SCREEN_INPUT { return Err("screen input exceeds frozen 8KiB cap".into()); }
    let root = report.parent().ok_or("report needs a parent")?; fs::create_dir_all(root).map_err(|e| e.to_string())?; let scratch = root.join("rsl1-scratch"); fs::create_dir_all(&scratch).map_err(|e| e.to_string())?;
    let driver = PathBuf::from(file!()); let lock = PathBuf::from("rust/cix-native/Cargo.lock"); let mut rows = format!("{{\"record\":\"binding\",\"source_revision\":{},\"input_sha256\":{},\"cix_sha256\":{},\"uncix_sha256\":{},\"driver_sha256\":{},\"cargo_lock_sha256\":{},\"rustc\":{},\"measurement_note\":\"GNU time RSS is native child only; transform process memory is intentionally separate and unmeasured\"}}\n", quote_json(&git_revision()?), quote_json(&sha256(&input)?), quote_json(&sha256(&cix)?), quote_json(&sha256(&uncix)?), quote_json(&sha256(&driver)?), quote_json(&sha256(&lock)?), quote_json(&toolchain()?)); let mut best: Option<(Vec<u8>, Vec<Op>, usize)> = None;
    let set = if mode == "screen" { screen_candidates() } else { candidates() }; let candidate_count = set.len();
    for (i, program) in set.into_iter().enumerate() {
        let transformed = transform(&program, &source); let transformed_bytes = transformed.len(); if transformed_bytes as u64 > MAX_TRANSFORM_BYTES { return Err("transform cap exceeded".into()); }
        let raw = scratch.join(format!("{i:03}.raw")); let coded = scratch.join(format!("{i:03}.cix")); fs::write(&raw, &transformed).map_err(|e| e.to_string())?;
        let temp_before = dir_bytes(&scratch).map_err(|e| e.to_string())?; let (backend, payload, encode_time, encode_peak, decode_time, decode_peak) = if program == vec![Op::Literal] { ("raw", transformed, Duration::ZERO, 0, Duration::ZERO, 0) } else { let et = code(&cix, &raw, &coded, profile, &scratch.join(format!("{i:03}.encode.time")))?; let native = read_limited(&coded, MAX_TRANSFORM_BYTES, "nested CIX archive")?; let restored_native = scratch.join(format!("{i:03}.restored-native")); let dt = decode(&uncix, &coded, &restored_native, source.len(), &scratch.join(format!("{i:03}.decode.time")))?; ("cixg1", native, et.0, et.1, dt.0, dt.1) }; let archive = frame(&program, if backend == "raw" { 1 } else { 0 }, source.len(), &payload)?;
        let native_plain = if backend == "raw" { payload.clone() } else { read_limited(&scratch.join(format!("{i:03}.restored-native")), source.len() as u64, "decoded candidate")? }; let restored = restore(&program, &native_plain, source.len())?; if restored != source { return Err(format!("round-trip failure for candidate {i}")); }
        let temp_peak = dir_bytes(&scratch).map_err(|e| e.to_string())?.max(temp_before); if temp_peak > MAX_TEMP { return Err("RSL1 temporary-space cap exceeded".into()); } let text = program_text(&program);
        rows.push_str(&format!("{{\"candidate\":{i},\"program\":{},\"backend\":{},\"nested_archive\":{},\"transformed_bytes\":{},\"backend_payload_bytes\":{},\"instruction_bytes\":{},\"complete_bytes\":{},\"encode_ns\":{},\"decode_ns\":{},\"encode_peak_bytes_gnu_time\":{},\"decode_peak_bytes_gnu_time\":{},\"temporary_bytes\":{},\"verified\":true}}\n", quote_json(&text), quote_json(backend), quote_json(&coded.display().to_string()), transformed_bytes, payload.len(), archive.len()-payload.len(), archive.len(), encode_time.as_nanos(), decode_time.as_nanos(), encode_peak, decode_peak, temp_peak));
        let archive_len = archive.len(); if best.as_ref().map(|b| archive_len < b.2).unwrap_or(true) { best = Some((archive, program, archive_len)); }
    }
    let (archive, program, bytes) = best.ok_or("empty candidate set")?; fs::write(&output, archive).map_err(|e| e.to_string())?; let archive_restored = scratch.join("selected.archive-only.restored"); let status = Command::new(env::current_exe().map_err(|e| e.to_string())?).args(["decode", output.to_str().ok_or("non-utf8 output")?, archive_restored.to_str().ok_or("non-utf8 restore")?, uncix.to_str().ok_or("non-utf8 uncix")?]).status().map_err(|e| e.to_string())?; if !status.success() || read_limited(&archive_restored, source.len() as u64, "archive-only restoration")? != source { return Err("fresh archive-only RSL1 decode failed".into()); } rows.push_str(&format!("{{\"selected\":{},\"complete_bytes\":{},\"candidate_set\":{},\"mode\":{},\"fresh_archive_only_decode\":true,\"selection\":\"minimum complete serialized RSL1 bytes; first declared candidate breaks ties\"}}\n", quote_json(&program_text(&program)), bytes, candidate_count, quote_json(mode))); fs::write(report, rows).map_err(|e| e.to_string())?; Ok(())
}
