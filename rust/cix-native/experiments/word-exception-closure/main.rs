//! WEC2 is a deliberately buffered, stand-alone word-exception experiment. It is outside
//! `src/`, is not registered with Cargo, and cannot affect CIX selection or
//! archive formats.  Compile only after the root grants a scheduler lease.
//!
//! `rustc --edition=2021 -O rust/cix-native/experiments/word-exception-closure/main.rs -o /tmp/wec2`

use std::{collections::BTreeMap, env, fs, path::{Path, PathBuf}, process::{Command, Stdio}, time::{Duration, Instant}};

const MAGIC: &[u8; 4] = b"WEC2";
const VERSION: u8 = 2;
const BACKEND_CIXG1: u8 = 0;
const BACKEND_RAW: u8 = 1;
const VARIANT_IDENTITY: u8 = 0;
const VARIANT_PALETTE: u8 = 1;
const ESCAPE: u8 = 16;
const MAX_INPUT: usize = 8 * 1024;
const MAX_REPRESENTATION: usize = 64 * 1024;
const MAX_NESTED_ARCHIVE: usize = 64 * 1024;
const MAX_DRIVER_TEMP: u64 = 2 * 1024 * 1024;
const MAX_NATIVE_WALL_SECONDS: u64 = 180;
const HEADER_BYTES: usize = 34; // magic, version, backend, source/instruction/payload lengths, CRC32
const INSTRUCTION_BYTES: usize = 35; // variant, width, dict count, then four u64 fields

fn crc32(data: &[u8]) -> u32 {
    let mut crc = !0u32;
    for &byte in data {
        crc ^= byte as u32;
        for _ in 0..8 { crc = if crc & 1 != 0 { (crc >> 1) ^ 0xedb8_8320 } else { crc >> 1 }; }
    }
    !crc
}

fn put_u64(out: &mut Vec<u8>, value: u64) { out.extend_from_slice(&value.to_le_bytes()); }
fn take_u64(data: &[u8], pos: &mut usize) -> Result<u64, String> {
    let end = pos.checked_add(8).ok_or("WPV2 length overflow")?;
    let raw: [u8; 8] = data.get(*pos..end).ok_or("truncated WPV2 length")?.try_into().map_err(|_| "invalid WPV2 length")?;
    *pos = end;
    Ok(u64::from_le_bytes(raw))
}

fn checked_len(value: u64, label: &str) -> Result<usize, String> { usize::try_from(value).map_err(|_| format!("WPV2 {label} exceeds host width")) }

struct Bits { bytes: Vec<u8>, current: u8, used: u8 }
impl Bits {
    fn new() -> Self { Self { bytes: Vec::new(), current: 0, used: 0 } }
    fn put(&mut self, value: u8) {
        for shift in (0..5).rev() {
            self.current = (self.current << 1) | ((value >> shift) & 1);
            self.used += 1;
            if self.used == 8 { self.bytes.push(self.current); self.current = 0; self.used = 0; }
        }
    }
    fn finish(mut self) -> Vec<u8> { if self.used != 0 { self.bytes.push(self.current << (8 - self.used)); } self.bytes }
}

struct BitReader<'a> { bytes: &'a [u8], bit: usize }
impl<'a> BitReader<'a> {
    fn get(&mut self) -> Result<u8, String> {
        if self.bit + 5 > self.bytes.len().checked_mul(8).ok_or("WPV2 bit length overflow")? { return Err("truncated WPV2 index stream".into()); }
        let mut value = 0u8;
        for _ in 0..5 { value = (value << 1) | ((self.bytes[self.bit / 8] >> (7 - self.bit % 8)) & 1); self.bit += 1; }
        Ok(value)
    }
}

fn words(input: &[u8], width: usize) -> Result<(Vec<u64>, &[u8]), String> {
    if !matches!(width, 2 | 4 | 8) { return Err("word width must be 2, 4, or 8".into()); }
    let full = input.len() / width;
    let mut result = Vec::with_capacity(full);
    for part in input[..full * width].chunks_exact(width) {
        let mut bytes = [0u8; 8]; bytes[..width].copy_from_slice(part);
        result.push(u64::from_le_bytes(bytes));
    }
    Ok((result, &input[full * width..]))
}
fn append_word(out: &mut Vec<u8>, value: u64, width: usize) { out.extend_from_slice(&value.to_le_bytes()[..width]); }
fn read_word(data: &[u8], pos: &mut usize, width: usize) -> Result<u64, String> {
    let end = pos.checked_add(width).ok_or("WPV2 word length overflow")?;
    let part = data.get(*pos..end).ok_or("truncated WPV2 literal word")?;
    let mut raw = [0u8; 8]; raw[..width].copy_from_slice(part); *pos = end; Ok(u64::from_le_bytes(raw))
}

/// The palette is sorted by descending count and then unsigned word value.
/// BTreeMap makes that tie rule independent of hash iteration and platform.
fn palette(values: &[u64], limit: usize) -> Vec<u64> {
    let mut counts = BTreeMap::<u64, u64>::new();
    for &value in values { *counts.entry(value).or_insert(0) += 1; }
    let mut entries: Vec<(u64, u64)> = counts.into_iter().collect();
    entries.sort_unstable_by(|(left_word, left_count), (right_word, right_count)| right_count.cmp(left_count).then_with(|| left_word.cmp(right_word)));
    entries.into_iter().take(limit).map(|(word, _)| word).collect()
}

fn identity_representation(input: &[u8], width: usize) -> Result<(Vec<u8>, Vec<u8>), String> {
    let (values, tail) = words(input, width)?;
    let mut instruction = Vec::with_capacity(INSTRUCTION_BYTES);
    instruction.extend_from_slice(&[VARIANT_IDENTITY, width as u8, 0]);
    // Identity uses index_len as its raw represented-byte length.  It still
    // serializes all four u64 fields, so its instruction is exactly 35 bytes.
    put_u64(&mut instruction, values.len() as u64); put_u64(&mut instruction, input.len() as u64);
    put_u64(&mut instruction, 0); put_u64(&mut instruction, tail.len() as u64);
    Ok((instruction, input.to_vec()))
}

fn palette_representation(input: &[u8], width: usize, limit: usize) -> Result<(Vec<u8>, Vec<u8>), String> {
    let (values, tail) = words(input, width)?;
    if !matches!(limit, 8 | 16) { return Err("dictionary limit must be 8 or 16".into()); }
    let dictionary = palette(&values, limit);
    let mut indices = Bits::new(); let mut exceptions = Vec::new();
    for &word in &values {
        if let Some(index) = dictionary.iter().position(|&candidate| candidate == word) { indices.put(index as u8); }
        else { indices.put(ESCAPE); append_word(&mut exceptions, word, width); }
    }
    let indices = indices.finish();
    let exception_count = exceptions.len() / width;
    let mut instruction = Vec::with_capacity(INSTRUCTION_BYTES);
    instruction.extend_from_slice(&[VARIANT_PALETTE, width as u8, dictionary.len() as u8]);
    put_u64(&mut instruction, values.len() as u64); put_u64(&mut instruction, indices.len() as u64);
    put_u64(&mut instruction, exception_count as u64); put_u64(&mut instruction, tail.len() as u64);
    let mut payload = Vec::with_capacity(dictionary.len() * width + indices.len() + exceptions.len() + tail.len());
    for word in dictionary { append_word(&mut payload, word, width); }
    payload.extend_from_slice(&indices); payload.extend_from_slice(&exceptions); payload.extend_from_slice(tail);
    Ok((instruction, payload))
}

fn restore_representation(instruction: &[u8], payload: &[u8]) -> Result<Vec<u8>, String> {
    if instruction.len() != INSTRUCTION_BYTES { return Err("invalid WPV2 instruction length".into()); }
    let variant = instruction[0]; let width = instruction[1] as usize; let dictionary_count = instruction[2] as usize;
    if !matches!(width, 2 | 4 | 8) || dictionary_count > 16 { return Err("invalid WPV2 word settings".into()); }
    let mut ip = 3; let word_count = checked_len(take_u64(instruction, &mut ip)?, "word count")?;
    let index_len = checked_len(take_u64(instruction, &mut ip)?, "index length")?;
    let exception_count = checked_len(take_u64(instruction, &mut ip)?, "exception count")?;
    let tail_len = checked_len(take_u64(instruction, &mut ip)?, "tail length")?;
    if ip != instruction.len() || tail_len >= width || input_len(word_count, width, tail_len)? > MAX_INPUT { return Err("invalid WPV2 instruction fields".into()); }
    if variant == VARIANT_IDENTITY {
        if dictionary_count != 0 || index_len != input_len(word_count, width, tail_len)? || exception_count != 0 || payload.len() != index_len { return Err("invalid WPV2 identity representation".into()); }
        return Ok(payload.to_vec());
    }
    if variant != VARIANT_PALETTE { return Err("unknown WPV2 variant".into()); }
    let dict_bytes = dictionary_count.checked_mul(width).ok_or("WPV2 dictionary overflow")?;
    let exception_bytes = exception_count.checked_mul(width).ok_or("WPV2 exception overflow")?;
    let expected_indices = word_count.checked_mul(5).ok_or("WPV2 index bit overflow")?.div_ceil(8);
    if index_len != expected_indices || payload.len() != dict_bytes.checked_add(index_len).and_then(|n| n.checked_add(exception_bytes)).and_then(|n| n.checked_add(tail_len)).ok_or("WPV2 payload overflow")? { return Err("WPV2 payload length mismatch".into()); }
    let mut p = 0; let mut dictionary = Vec::with_capacity(dictionary_count);
    for _ in 0..dictionary_count { dictionary.push(read_word(payload, &mut p, width)?); }
    let index_end = p + index_len; let mut reader = BitReader { bytes: &payload[p..index_end], bit: 0 }; p = index_end;
    let mut output = Vec::with_capacity(input_len(word_count, width, tail_len)?); let mut used_exceptions = 0usize;
    for _ in 0..word_count {
        let index = reader.get()?;
        let word = if index == ESCAPE { used_exceptions += 1; read_word(payload, &mut p, width)? }
        else { *dictionary.get(index as usize).ok_or("WPV2 palette index outside dictionary")? };
        append_word(&mut output, word, width);
    }
    if used_exceptions != exception_count || p + tail_len != payload.len() { return Err("WPV2 exception or tail mismatch".into()); }
    output.extend_from_slice(&payload[p..]); Ok(output)
}
fn input_len(words: usize, width: usize, tail: usize) -> Result<usize, String> { words.checked_mul(width).and_then(|n| n.checked_add(tail)).ok_or("WPV2 restored length overflow".into()) }
fn represented_len(instruction: &[u8]) -> Result<usize, String> {
    if instruction.len() != INSTRUCTION_BYTES { return Err("invalid WPV2 instruction length".into()); }
    let variant = instruction[0]; let width = instruction[1] as usize; let dictionary_count = instruction[2] as usize;
    if !matches!(width, 2 | 4 | 8) || dictionary_count > 16 { return Err("invalid WPV2 word settings".into()); }
    let mut p = 3; let word_count = checked_len(take_u64(instruction, &mut p)?, "word count")?;
    let index_len = checked_len(take_u64(instruction, &mut p)?, "index length")?;
    let exception_count = checked_len(take_u64(instruction, &mut p)?, "exception count")?;
    let tail_len = checked_len(take_u64(instruction, &mut p)?, "tail length")?;
    if p != instruction.len() || tail_len >= width { return Err("invalid WPV2 instruction fields".into()); }
    let restored = input_len(word_count, width, tail_len)?;
    let represented = match variant {
        VARIANT_IDENTITY if dictionary_count == 0 && exception_count == 0 && index_len == restored => index_len,
        VARIANT_PALETTE => {
            let expected_indices = word_count.checked_mul(5).ok_or("WPV2 index bit overflow")?.div_ceil(8);
            if index_len != expected_indices { return Err("WPV2 palette index length mismatch".into()); }
            dictionary_count.checked_mul(width).and_then(|n| n.checked_add(index_len)).and_then(|n| exception_count.checked_mul(width).and_then(|e| n.checked_add(e))).and_then(|n| n.checked_add(tail_len)).ok_or("WPV2 representation length overflow")?
        }
        _ => return Err("invalid WPV2 variant instruction fields".into()),
    };
    if represented > MAX_REPRESENTATION { return Err("WPV2 represented length exceeds cap".into()); }
    Ok(represented)
}

fn frame(backend: u8, source_len: usize, instruction: &[u8], payload: &[u8]) -> Result<Vec<u8>, String> {
    if !matches!(backend, BACKEND_CIXG1 | BACKEND_RAW) || instruction.len() != INSTRUCTION_BYTES { return Err("invalid WPV2 frame settings".into()); }
    let mut covered = Vec::with_capacity(instruction.len() + payload.len()); covered.extend_from_slice(instruction); covered.extend_from_slice(payload);
    let mut out = Vec::with_capacity(HEADER_BYTES + covered.len()); out.extend_from_slice(MAGIC); out.push(VERSION); out.push(backend);
    put_u64(&mut out, source_len as u64); put_u64(&mut out, instruction.len() as u64); put_u64(&mut out, payload.len() as u64); out.extend_from_slice(&crc32(&covered).to_le_bytes()); out.extend_from_slice(&covered); Ok(out)
}
fn unframe(archive: &[u8]) -> Result<(u8, usize, &[u8], &[u8]), String> {
    if archive.len() < HEADER_BYTES || archive.get(..4) != Some(MAGIC) || archive[4] != VERSION { return Err("not WPV2 version 2".into()); }
    let backend = archive[5]; if !matches!(backend, BACKEND_CIXG1 | BACKEND_RAW) { return Err("unknown WPV2 backend".into()); }
    let mut p = 6; let source_len = checked_len(take_u64(archive, &mut p)?, "source length")?; let instruction_len = checked_len(take_u64(archive, &mut p)?, "instruction length")?; let payload_len = checked_len(take_u64(archive, &mut p)?, "payload length")?;
    let crc = u32::from_le_bytes(archive.get(p..p + 4).ok_or("truncated WPV2 CRC")?.try_into().map_err(|_| "invalid WPV2 CRC")?); p += 4;
    if source_len > MAX_INPUT || instruction_len != INSTRUCTION_BYTES || payload_len > MAX_NESTED_ARCHIVE || p.checked_add(instruction_len).and_then(|n| n.checked_add(payload_len)) != Some(archive.len()) { return Err("WPV2 frame length mismatch".into()); }
    let instruction = &archive[p..p + instruction_len]; let payload = &archive[p + instruction_len..];
    if crc32(&archive[p..]) != crc { return Err("WPV2 CRC mismatch".into()); }
    let restored_len = { let mut q = 3; let width = instruction[1] as usize; let words = checked_len(take_u64(instruction, &mut q)?, "word count")?; let _index = take_u64(instruction, &mut q)?; let _exceptions = take_u64(instruction, &mut q)?; let tail = checked_len(take_u64(instruction, &mut q)?, "tail length")?; input_len(words, width, tail)? };
    if restored_len != source_len { return Err("WPV2 instruction source length disagrees with outer frame".into()); }
    let declared_representation = represented_len(instruction)?;
    if backend == BACKEND_RAW && payload.len() != declared_representation { return Err("WPV2 raw payload length disagrees with instruction".into()); }
    Ok((backend, source_len, instruction, payload))
}

fn run_native(program: &Path, args: &[&str], time_log: &Path, output_limit: usize) -> Result<(Duration, u64), String> {
    let started = Instant::now();
    let fsize = format!("--fsize={output_limit}:{output_limit}");
    let wall = format!("{MAX_NATIVE_WALL_SECONDS}s");
    let status = Command::new("/usr/bin/time").args(["-v", "-o"]).arg(time_log).arg("--").arg("/usr/bin/timeout").args(["--preserve-status", &wall, "/usr/bin/prlimit"]).arg(&fsize).arg("--").arg(program).args(args).stdout(Stdio::null()).stderr(Stdio::null()).status().map_err(|e| e.to_string())?;
    if !status.success() { return Err(format!("native backend exited {status}")); }
    let log = fs::read_to_string(time_log).map_err(|e| e.to_string())?;
    let kib = log.lines().find_map(|line| line.strip_prefix("\tMaximum resident set size (kbytes): ").and_then(|n| n.trim().parse::<u64>().ok())).ok_or("GNU time did not report RSS")?;
    Ok((started.elapsed(), kib * 1024))
}
fn native_encode(cix: &Path, input: &Path, output: &Path, log: &Path) -> Result<(Duration, u64), String> {
    let input = input.to_str().ok_or("non-UTF8 input path")?; let output = output.to_str().ok_or("non-UTF8 output path")?;
    run_native(cix, &["-k", "-f", "--threads", "1", "--memory", "512MiB", "--format", "cixg1", "--profile", "fast", "-o", output, input], log, MAX_NESTED_ARCHIVE)
}
fn native_decode(uncix: &Path, input: &Path, output: &Path, log: &Path, expected_output: usize) -> Result<(Duration, u64), String> {
    let input = input.to_str().ok_or("non-UTF8 input path")?; let output = output.to_str().ok_or("non-UTF8 output path")?;
    run_native(uncix, &["-k", "-f", "--memory", "512MiB", "-o", output, input], log, expected_output)
}
fn quote_json(value: &str) -> String { format!("\"{}\"", value.replace('\\', "\\\\").replace('\"', "\\\"").replace('\n', "\\n")) }
fn sha256(path: &Path) -> Result<String, String> { let output = Command::new("sha256sum").arg(path).output().map_err(|e| e.to_string())?; if !output.status.success() { return Err(format!("sha256sum failed: {}", path.display())); } String::from_utf8(output.stdout).map_err(|e| e.to_string())?.split_whitespace().next().map(str::to_owned).ok_or("missing SHA-256".into()) }

fn next_random(state: &mut u64) -> u64 { *state ^= *state << 13; *state ^= *state >> 7; *state ^= *state << 17; *state }
fn fixture(name: &str) -> Result<Vec<u8>, String> {
    let mut out = Vec::with_capacity(MAX_INPUT); let mut state = 0x9e37_79b9_7f4a_7c15;
    match name {
        "strong" => { let values: Vec<u64> = (0..8).map(|_| next_random(&mut state)).collect(); for i in 0..1024 { out.extend_from_slice(&values[i % 8].to_le_bytes()); } }
        "weak" => { let top: Vec<u64> = (0..16).map(|_| next_random(&mut state)).collect(); for i in 0..896 { out.extend_from_slice(&top[i % 16].to_le_bytes()); } for _ in 0..128 { out.extend_from_slice(&next_random(&mut state).to_le_bytes()); } }
        "absent" => for _ in 0..1024 { out.extend_from_slice(&next_random(&mut state).to_le_bytes()); },
        _ => return Err("fixture must be strong, weak, or absent".into()),
    }
    Ok(out)
}

fn decode_archive(archive: &Path, output: &Path, uncix: &Path) -> Result<(), String> {
    let stored = fs::read(archive).map_err(|e| e.to_string())?; let (backend, source_len, instruction, payload) = unframe(&stored)?;
    let expected_representation = represented_len(instruction)?;
    let represented = if backend == BACKEND_RAW { payload.to_vec() } else {
        let nested = output.with_extension("wpv2.nested.cix"); let plain = output.with_extension("wpv2.nested.plain"); fs::write(&nested, payload).map_err(|e| e.to_string())?;
        native_decode(uncix, &nested, &plain, &output.with_extension("wpv2.decode.time"), expected_representation)?;
        if fs::metadata(&plain).map_err(|e| e.to_string())?.len() != expected_representation as u64 { return Err("WPV2 nested decode output length mismatch".into()); }
        fs::read(plain).map_err(|e| e.to_string())?
    };
    if represented.len() != expected_representation { return Err("WPV2 represented length mismatch".into()); }
    let restored = restore_representation(instruction, &represented)?;
    if restored.len() != source_len { return Err("WPV2 restored source length mismatch".into()); }
    fs::write(output, restored).map_err(|e| e.to_string())?; Ok(())
}

fn dir_bytes(path: &Path) -> Result<u64, String> {
    let mut total = 0u64;
    for entry in fs::read_dir(path).map_err(|e| e.to_string())? { let entry = entry.map_err(|e| e.to_string())?; let meta = entry.metadata().map_err(|e| e.to_string())?; total = total.checked_add(if meta.is_dir() { dir_bytes(&entry.path())? } else { meta.len() }).ok_or("WPV2 temporary-byte overflow")?; }
    Ok(total)
}
fn check_temp(path: &Path) -> Result<u64, String> { let total = dir_bytes(path)?; if total > MAX_DRIVER_TEMP { return Err("WPV2 driver temporary cap exceeded".into()); } Ok(total) }

fn encode(variant: &str, width: usize, limit: usize, input: &Path, archive: &Path, report: &Path, cix: &Path, uncix: &Path) -> Result<(), String> {
    if !matches!(width, 2 | 4) { return Err("R2 permits word widths 2 or 4 only".into()); }
    let source = fs::read(input).map_err(|e| e.to_string())?; if source.len() > MAX_INPUT { return Err("WPV2 initial screen input exceeds 8KiB".into()); }
    let (instruction, representation) = match variant { "identity" if limit == 0 => identity_representation(&source, width)?, "palette" => palette_representation(&source, width, limit)?, _ => return Err("identity requires limit 0; palette requires 8 or 16".into()) };
    if representation.len() > MAX_REPRESENTATION || represented_len(&instruction)? != representation.len() { return Err("WPV2 representation cap or instruction mismatch".into()); }
    // A report is one frozen row. Its own sibling scratch directory retains
    // every child time receipt without a later fixture overwriting it.
    let scratch = report.with_extension("wpv2.scratch"); fs::create_dir_all(&scratch).map_err(|e| e.to_string())?;
    let represented_file = scratch.join(format!("{variant}.represented")); let nested = scratch.join(format!("{variant}.cix")); let nested_plain = scratch.join(format!("{variant}.nested.plain")); fs::write(&represented_file, &representation).map_err(|e| e.to_string())?;
    // Do not use transformed size to skip this encode: a later CIX stage can still recover it.
    let encode_stats = native_encode(cix, &represented_file, &nested, &scratch.join(format!("{variant}.encode.time")))?;
    if fs::metadata(&nested).map_err(|e| e.to_string())?.len() > MAX_NESTED_ARCHIVE as u64 { return Err("WPV2 nested archive cap exceeded".into()); }
    let nested_bytes = fs::read(&nested).map_err(|e| e.to_string())?;
    let decode_stats = native_decode(uncix, &nested, &nested_plain, &scratch.join(format!("{variant}.decode.time")), representation.len())?;
    if fs::metadata(&nested_plain).map_err(|e| e.to_string())?.len() != representation.len() as u64 { return Err("WPV2 nested decode output length mismatch".into()); }
    let native_plain = fs::read(&nested_plain).map_err(|e| e.to_string())?;
    if restore_representation(&instruction, &native_plain)? != source { return Err("nested CIXG1 round-trip failed".into()); }
    let native_frame = frame(BACKEND_CIXG1, source.len(), &instruction, &nested_bytes)?;
    let raw_frame = frame(BACKEND_RAW, source.len(), &instruction, &representation)?;
    let native_candidate = archive.with_extension("wpv2.cixg1"); fs::write(&native_candidate, &native_frame).map_err(|e| e.to_string())?;
    let selected_native = native_frame.len() <= raw_frame.len(); fs::write(archive, if selected_native { &native_frame } else { &raw_frame }).map_err(|e| e.to_string())?;
    let exe = env::current_exe().map_err(|e| e.to_string())?;
    let native_fresh = archive.with_extension("wpv2.cixg1.fresh.restored"); let native_status = Command::new(&exe).args(["decode", native_candidate.to_str().ok_or("non-UTF8 native archive path")?, native_fresh.to_str().ok_or("non-UTF8 native restore path")?, uncix.to_str().ok_or("non-UTF8 uncix path")?]).status().map_err(|e| e.to_string())?;
    let native_fresh_ok = native_status.success() && fs::read(&native_fresh).map_err(|e| e.to_string())? == source;
    if !native_fresh_ok { return Err("fresh native WPV2+CIXG1 archive-only decode failed".into()); }
    let selected_fresh = archive.with_extension("wpv2.selected.fresh.restored"); let selected_status = Command::new(exe).args(["decode", archive.to_str().ok_or("non-UTF8 archive path")?, selected_fresh.to_str().ok_or("non-UTF8 selected restore path")?, uncix.to_str().ok_or("non-UTF8 uncix path")?]).status().map_err(|e| e.to_string())?;
    let selected_fresh_ok = selected_status.success() && fs::read(&selected_fresh).map_err(|e| e.to_string())? == source;
    if !selected_fresh_ok { return Err("fresh selected WPV2 archive-only decode failed".into()); }
    let temporary_bytes = check_temp(&scratch)?;
    let dict_count = instruction[2]; let exceptions = u64::from_le_bytes(instruction[19..27].try_into().unwrap());
    let source_hash = sha256(input)?; let cix_hash = sha256(cix)?; let uncix_hash = sha256(uncix)?; let driver_hash = sha256(Path::new(file!()))?;
    let row = format!("{{\"experiment\":\"word-exception-closure-r2\",\"variant\":{},\"width\":{},\"dictionary_limit\":{},\"input_sha256\":{},\"cix_sha256\":{},\"uncix_sha256\":{},\"driver_sha256\":{},\"source_bytes\":{},\"representation_bytes\":{},\"dictionary_entries\":{},\"exception_words\":{},\"instruction_bytes\":{},\"outer_header_bytes\":{},\"nested_cixg1_bytes\":{},\"complete_cixg1_bytes\":{},\"complete_raw_fallback_bytes\":{},\"selected_backend\":{},\"selected_complete_bytes\":{},\"native_candidate_path\":{},\"native_candidate_fresh_archive_only_decode\":{},\"selected_candidate_fresh_archive_only_decode\":{},\"driver_temporary_bytes\":{},\"encode_ns\":{},\"decode_ns\":{},\"encode_peak_rss_bytes_gnu_time\":{},\"decode_peak_rss_bytes_gnu_time\":{}}}\n", quote_json(variant), width, limit, quote_json(&source_hash), quote_json(&cix_hash), quote_json(&uncix_hash), quote_json(&driver_hash), source.len(), representation.len(), dict_count, exceptions, instruction.len(), HEADER_BYTES, nested_bytes.len(), native_frame.len(), raw_frame.len(), quote_json(if selected_native { "cixg1" } else { "raw" }), if selected_native { native_frame.len() } else { raw_frame.len() }, quote_json(&native_candidate.display().to_string()), native_fresh_ok, selected_fresh_ok, temporary_bytes, encode_stats.0.as_nanos(), decode_stats.0.as_nanos(), encode_stats.1, decode_stats.1);
    fs::write(report, row).map_err(|e| e.to_string())?; Ok(())
}

fn main() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("generate") if args.len() == 4 => fs::write(&args[3], fixture(&args[2])?).map_err(|e| e.to_string()),
        Some("decode") if args.len() == 5 => decode_archive(Path::new(&args[2]), Path::new(&args[3]), Path::new(&args[4])),
        Some("encode") if args.len() == 10 => { let width = args[3].parse::<usize>().map_err(|_| "word width must be an integer")?; let limit = args[4].parse::<usize>().map_err(|_| "dictionary limit must be an integer")?; encode(&args[2], width, limit, Path::new(&args[5]), Path::new(&args[6]), Path::new(&args[7]), Path::new(&args[8]), Path::new(&args[9])) }
        Some("--self-describe") if args.len() == 2 => { println!("WEC2: buffered identity or input-derived top-8/top-16 dictionary; widths 2/4; five-bit indices and raw escape words; CRC covers instruction and payload; CIXG1 FAST control plus raw fallback."); Ok(()) }
        _ => Err("usage: wec2 generate strong|weak|absent OUTPUT | wec2 encode identity WIDTH 0 INPUT ARCHIVE REPORT CIX UNCIX | wec2 encode palette WIDTH 8|16 INPUT ARCHIVE REPORT CIX UNCIX | wec2 decode ARCHIVE OUTPUT UNCIX".into()),
    }
}
