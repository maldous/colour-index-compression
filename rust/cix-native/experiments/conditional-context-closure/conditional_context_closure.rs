//! Unregistered COND-CONTEXT-1 experiment driver.
//!
//! This does not alter CIX containers, selectors, or Cargo targets.  A lease
//! holder compiles it explicitly against a frozen `cix_native` rlib.  The
//! outer CIXCTX1 frame stores the selected payload verbatim and CRC-protects
//! the whole frame.  Context lane IDs and lane lengths are inside the native
//! rank payload, where `rank::decode_context_type_classes` validates them.

use cix_native::rank;
use num_bigint::BigUint;
use num_traits::One;
use std::collections::BTreeMap;
use std::{env, fs, io::Read, time::Instant};

const SOURCE_BYTES: usize = 16 * 1024;
const MAX_ARCHIVE: usize = 1024 * 1024;
const HEADER_BYTES: usize = 26; // magic, version, mode, source length, payload length
const CRC_BYTES: usize = 4;

#[derive(Clone, Copy)]
enum Case { Strong, Weak, Absent }

#[derive(Clone, Copy, PartialEq, Eq)]
enum Variant { Global, Context14, Context28, Raw, Best }

impl Case {
    fn parse(value: &str) -> Result<Self, String> {
        match value {
            "strong" => Ok(Self::Strong),
            "weak" => Ok(Self::Weak),
            "absent" => Ok(Self::Absent),
            _ => Err("case must be strong, weak, or absent".into()),
        }
    }
    fn name(self) -> &'static str {
        match self { Self::Strong => "strong", Self::Weak => "weak", Self::Absent => "absent" }
    }
}

impl Variant {
    fn parse(value: &str) -> Result<Self, String> {
        match value {
            "global" => Ok(Self::Global),
            "context-1-4" => Ok(Self::Context14),
            "context-2-8" => Ok(Self::Context28),
            "raw" => Ok(Self::Raw),
            "best" => Ok(Self::Best),
            _ => Err("variant must be global, context-1-4, context-2-8, raw, or best".into()),
        }
    }
    fn name(self) -> &'static str {
        match self {
            Self::Global => "global", Self::Context14 => "context-1-4",
            Self::Context28 => "context-2-8", Self::Raw => "raw", Self::Best => "best",
        }
    }
    fn mode(self) -> Result<u8, String> {
        match self {
            Self::Global => Ok(0), Self::Context14 => Ok(1), Self::Context28 => Ok(2),
            Self::Raw => Ok(3), Self::Best => Err("best has no stored mode".into()),
        }
    }
    fn from_mode(mode: u8) -> Result<Self, String> {
        match mode {
            0 => Ok(Self::Global), 1 => Ok(Self::Context14), 2 => Ok(Self::Context28),
            3 => Ok(Self::Raw), _ => Err("unknown CIXCTX1 mode".into()),
        }
    }
}

fn fixture(case: Case) -> Vec<u8> {
    let mut out = Vec::with_capacity(SOURCE_BYTES);
    match case {
        // Every observed previous-byte context has exactly one following
        // symbol after startup.  Global counts remain four-way balanced.
        Case::Strong => {
            let period = [0u8, 16, 1, 17];
            for index in 0..SOURCE_BYTES { out.push(period[index % period.len()]); }
        }
        // One context has two successors, while the others retain a smaller
        // relationship.  This deliberately weakens, but does not remove,
        // the contextual signal.
        Case::Weak => {
            let period = [0u8, 16, 1, 16, 0, 17, 1, 17];
            for index in 0..SOURCE_BYTES { out.push(period[index % period.len()]); }
        }
        // A deterministic full-byte generator removes a designed causal
        // relation.  Its state and constants are frozen here, not selected
        // from an input name at encode time.
        Case::Absent => {
            let mut state = 0x4d59_5df4_d0f3_3173u64;
            for _ in 0..SOURCE_BYTES {
                state ^= state << 7;
                state ^= state >> 9;
                state = state.wrapping_mul(0x9e37_79b9_7f4a_7c15);
                out.push((state >> 24) as u8);
            }
        }
    }
    out
}

fn crc32(data: &[u8]) -> u32 {
    let mut crc = !0u32;
    for &byte in data {
        crc ^= u32::from(byte);
        for _ in 0..8 { crc = (crc >> 1) ^ (0xedb8_8320 & 0u32.wrapping_sub(crc & 1)); }
    }
    !crc
}

fn put_varint(mut value: usize, out: &mut Vec<u8>) {
    while value >= 128 { out.push((value as u8 & 127) | 128); value >>= 7; }
    out.push(value as u8);
}

fn varint_len(value: usize) -> usize {
    let mut bytes = Vec::new();
    put_varint(value, &mut bytes);
    bytes.len()
}

fn choose(n: usize, k: usize) -> BigUint {
    let k = k.min(n.saturating_sub(k));
    let mut value = BigUint::one();
    for index in 1..=k { value *= n - k + index; value /= index; }
    value
}

fn fixed_bytes(n: usize, k: usize) -> usize {
    let choices = choose(n, k);
    (choices - BigUint::one()).bits().div_ceil(8) as usize
}

fn context_bucket(tail: &[u8], order: usize, bucket_bits: usize) -> usize {
    if order == 1 && bucket_bits >= 8 { return tail.last().copied().unwrap_or(0) as usize; }
    let mut hash = 1_469_598_103_934_665_603u64;
    for &byte in tail { hash ^= u64::from(byte); hash = hash.wrapping_mul(1_099_511_628_211); }
    (hash & ((1u64 << bucket_bits) - 1)) as usize
}

fn context_lanes(data: &[u8], order: usize, bucket_bits: usize) -> BTreeMap<usize, Vec<u8>> {
    let mut lanes = BTreeMap::<usize, Vec<u8>>::new();
    let mut tail = Vec::with_capacity(order);
    for &byte in data {
        let bucket = context_bucket(&tail, order, bucket_bits);
        lanes.entry(bucket).or_default().push(byte);
        tail.push(byte);
        if tail.len() > order { tail.remove(0); }
    }
    lanes
}

#[derive(Default)]
struct Accounting {
    archive_header_bytes: usize,
    archive_crc_bytes: usize,
    payload_bytes: usize,
    raw_payload_bytes: usize,
    context_parameter_bytes: usize,
    active_context_count_bytes: usize,
    active_context_id_bytes: usize,
    lane_length_bytes: usize,
    lane_header_and_sequence_bytes: usize,
    active_contexts: usize,
}

fn account(variant: Variant, payload: &[u8], source: &[u8]) -> Result<Accounting, String> {
    let mut result = Accounting {
        archive_header_bytes: HEADER_BYTES,
        archive_crc_bytes: CRC_BYTES,
        payload_bytes: payload.len(),
        ..Accounting::default()
    };
    match variant {
        Variant::Raw => result.raw_payload_bytes = payload.len(),
        Variant::Global => result.lane_header_and_sequence_bytes = payload.len(),
        Variant::Context14 | Variant::Context28 => {
            let (order, bits) = if variant == Variant::Context14 { (1, 4) } else { (2, 8) };
            let lanes = context_lanes(source, order, bits);
            let q = lanes.len();
            let bucket_count = 1usize << bits;
            if q == 0 || q > bucket_count { return Err("invalid derived context layout".into()); }
            result.context_parameter_bytes = 2;
            result.active_context_count_bytes = varint_len(q);
            result.active_context_id_bytes = if q < bucket_count { fixed_bytes(bucket_count, q) } else { 0 };
            result.lane_length_bytes = if q > 1 { fixed_bytes(source.len() - 1, q - 1) } else { 0 };
            result.active_contexts = q;
            result.lane_header_and_sequence_bytes = lanes.values()
                .map(|lane| rank::encode_type_class(lane).map(|part| part.len()))
                .collect::<Result<Vec<_>, _>>()?
                .into_iter()
                .sum();
            let accounted = result.context_parameter_bytes
                + result.active_context_count_bytes
                + result.active_context_id_bytes
                + result.lane_length_bytes
                + result.lane_header_and_sequence_bytes;
            if accounted != payload.len() { return Err("context payload accounting disagrees with emitted bytes".into()); }
        }
        Variant::Best => return Err("best cannot be accounted directly".into()),
    }
    Ok(result)
}

fn json_accounting(value: &Accounting) -> String {
    format!(
        "{{\"archive_header_bytes\":{},\"archive_crc_bytes\":{},\"payload_bytes\":{},\"raw_payload_bytes\":{},\"context_parameter_bytes\":{},\"active_context_count_bytes\":{},\"active_context_id_bytes\":{},\"lane_length_bytes\":{},\"lane_header_and_sequence_bytes\":{},\"active_contexts\":{}}}",
        value.archive_header_bytes, value.archive_crc_bytes, value.payload_bytes,
        value.raw_payload_bytes, value.context_parameter_bytes, value.active_context_count_bytes,
        value.active_context_id_bytes, value.lane_length_bytes,
        value.lane_header_and_sequence_bytes, value.active_contexts,
    )
}

fn payload(variant: Variant, source: &[u8]) -> Result<Vec<u8>, String> {
    match variant {
        Variant::Global => rank::encode_composition_tiles(source),
        Variant::Context14 => rank::encode_context_type_classes(source, 1, 4, &[]),
        Variant::Context28 => rank::encode_context_type_classes(source, 2, 8, &[]),
        Variant::Raw => Ok(source.to_vec()),
        Variant::Best => Err("best is selected from concrete variants".into()),
    }
}

fn frame(variant: Variant, source: &[u8], payload: &[u8]) -> Result<Vec<u8>, String> {
    let mut out = Vec::with_capacity(HEADER_BYTES + payload.len() + CRC_BYTES);
    out.extend_from_slice(b"CIXCTX1\0");
    out.push(1);
    out.push(variant.mode()?);
    out.extend_from_slice(&(source.len() as u64).to_le_bytes());
    out.extend_from_slice(&(payload.len() as u64).to_le_bytes());
    out.extend_from_slice(payload);
    out.extend_from_slice(&crc32(&out).to_le_bytes());
    if out.len() > MAX_ARCHIVE { return Err("CIXCTX1 archive exceeds experiment bound".into()); }
    Ok(out)
}

fn read_bounded(path: &str) -> Result<Vec<u8>, String> {
    let file = fs::File::open(path).map_err(|error| format!("open archive: {error}"))?;
    if !file.metadata().map_err(|error| format!("archive metadata: {error}"))?.is_file() {
        return Err("archive is not a regular file".into());
    }
    let mut input = Vec::new();
    file.take(MAX_ARCHIVE as u64 + 1).read_to_end(&mut input)
        .map_err(|error| format!("read archive: {error}"))?;
    if input.len() > MAX_ARCHIVE { return Err("archive exceeds experiment bound".into()); }
    Ok(input)
}

fn decode_frame(blob: &[u8]) -> Result<(Variant, Vec<u8>), String> {
    if blob.len() < HEADER_BYTES + CRC_BYTES || &blob[..8] != b"CIXCTX1\0" || blob[8] != 1 {
        return Err("invalid CIXCTX1 header".into());
    }
    let expected_crc = u32::from_le_bytes(blob[blob.len() - CRC_BYTES..].try_into().unwrap());
    if crc32(&blob[..blob.len() - CRC_BYTES]) != expected_crc { return Err("CIXCTX1 CRC mismatch".into()); }
    let variant = Variant::from_mode(blob[9])?;
    let source_len: usize = u64::from_le_bytes(blob[10..18].try_into().unwrap())
        .try_into().map_err(|_| "source length overflow")?;
    let payload_len: usize = u64::from_le_bytes(blob[18..26].try_into().unwrap())
        .try_into().map_err(|_| "payload length overflow")?;
    if source_len > SOURCE_BYTES || payload_len != blob.len() - HEADER_BYTES - CRC_BYTES {
        return Err("CIXCTX1 length mismatch".into());
    }
    let payload = &blob[HEADER_BYTES..blob.len() - CRC_BYTES];
    let restored = match variant {
        Variant::Global => rank::decode_composition_tiles(payload, source_len)?,
        Variant::Context14 => rank::decode_context_type_classes(payload, source_len, &[])?,
        Variant::Context28 => rank::decode_context_type_classes(payload, source_len, &[])?,
        Variant::Raw => payload.to_vec(),
        Variant::Best => unreachable!(),
    };
    if restored.len() != source_len { return Err("CIXCTX1 restored length mismatch".into()); }
    Ok((variant, restored))
}

fn encode(case: Case, requested: Variant, output: &str) -> Result<(), String> {
    let source = fixture(case);
    let started = Instant::now();
    let choices = [Variant::Global, Variant::Context14, Variant::Context28, Variant::Raw];
    let (variant, payload) = if requested == Variant::Best {
        let mut best: Option<(Variant, Vec<u8>)> = None;
        let mut best_size = usize::MAX;
        for candidate in choices {
            let payload = payload(candidate, &source)?;
            let candidate_size = frame(candidate, &source, &payload)?.len();
            if candidate_size < best_size {
                best_size = candidate_size;
                best = Some((candidate, payload));
            }
        }
        best.ok_or("no CIXCTX1 candidates")?
    } else { (requested, payload(requested, &source)?) };
    let accounting = account(variant, &payload, &source)?;
    let archive = frame(variant, &source, &payload)?;
    fs::write(output, &archive).map_err(|error| format!("write archive: {error}"))?;
    println!(
        "{{\"experiment\":\"conditional-context-closure\",\"operation\":\"encode\",\"case\":\"{}\",\"requested_variant\":\"{}\",\"selected_variant\":\"{}\",\"input_bytes\":{},\"complete_archive_bytes\":{},\"complete_archive_encode_ns\":{},\"accounting\":{}}}",
        case.name(), requested.name(), variant.name(), source.len(), archive.len(),
        started.elapsed().as_nanos(), json_accounting(&accounting),
    );
    Ok(())
}

fn decode(input: &str, output: &str) -> Result<(), String> {
    let started = Instant::now();
    let archive = read_bounded(input)?;
    let (variant, restored) = decode_frame(&archive)?;
    // Write only after all frame, CRC, rank, lane and output-length checks.
    fs::write(output, &restored).map_err(|error| format!("write restored: {error}"))?;
    println!(
        "{{\"experiment\":\"conditional-context-closure\",\"operation\":\"decode\",\"selected_variant\":\"{}\",\"complete_archive_bytes\":{},\"restored_bytes\":{},\"complete_archive_decode_ns\":{}}}",
        variant.name(), archive.len(), restored.len(), started.elapsed().as_nanos(),
    );
    Ok(())
}

fn reject(input: &str) -> Result<(), String> {
    if decode_frame(&read_bounded(input)?).is_ok() { return Err("malformed archive was accepted".into()); }
    println!("{{\"experiment\":\"conditional-context-closure\",\"operation\":\"reject\",\"status\":\"rejected\"}}");
    Ok(())
}

fn main() -> Result<(), String> {
    let mut args = env::args().skip(1);
    match args.next().as_deref() {
        Some("generate") => {
            let case = Case::parse(&args.next().ok_or("missing case")?)?;
            let output = args.next().ok_or("missing output")?;
            if args.next().is_some() { return Err("usage: conditional_context_closure generate CASE OUTPUT".into()); }
            fs::write(output, fixture(case)).map_err(|error| format!("write fixture: {error}"))
        }
        Some("encode") => {
            let variant = Variant::parse(&args.next().ok_or("missing variant")?)?;
            let case = Case::parse(&args.next().ok_or("missing case")?)?;
            let output = args.next().ok_or("missing archive output")?;
            if args.next().is_some() { return Err("usage: conditional_context_closure encode VARIANT CASE ARCHIVE".into()); }
            encode(case, variant, &output)
        }
        Some("decode") => {
            let input = args.next().ok_or("missing archive")?;
            let output = args.next().ok_or("missing restored output")?;
            if args.next().is_some() { return Err("usage: conditional_context_closure decode ARCHIVE OUTPUT".into()); }
            decode(&input, &output)
        }
        Some("reject") => {
            let input = args.next().ok_or("missing malformed archive")?;
            if args.next().is_some() { return Err("usage: conditional_context_closure reject ARCHIVE".into()); }
            reject(&input)
        }
        _ => Err("usage: conditional_context_closure generate CASE OUTPUT | encode VARIANT CASE ARCHIVE | decode ARCHIVE OUTPUT | reject ARCHIVE".into()),
    }
}
