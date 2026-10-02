//! Conditional-cost-v1 is an unregistered research driver.  Cargo does not
//! compile it unless the lease holder explicitly copies or links it as an
//! example; it is not part of the CIX archive format or selector.
//!
//! Example lease command (after an immutable release build):
//! `rustc --edition=2021 rust/cix-native/experiments/conditional-cost-v1/conditional_cost_v1.rs \
//!   --extern cix_native=benchmark-work/ptt5-fixed-8439/target/release-lto/libcix_native.rlib \
//!   -L dependency=benchmark-work/ptt5-fixed-8439/target/release-lto/deps \
//!   -o /tmp/conditional-cost-v1`

use cix_native::rank;
use std::env;
use std::fs;
use std::time::Instant;

const TILE: usize = 1024;
const TILES: usize = 16;
const ARCHIVE_HEADER: usize = 26; // magic(8), version(1), coder(1), n(8), payload length(8)
const COUNT_HEADER_BYTES_PER_TILE: usize = 26; // varint(16), C(256,16) rank (11), composition rank (14)
const EXACT_RANK_BITS_PER_TILE: usize = 4034; // ceil(log2(1024!/(64!)^16)); frozen generator only

#[derive(Clone, Copy)]
enum Case { Alternating, Clustered, Periodic, Random }

#[derive(Clone, Copy)]
enum Codec { ExactRank, RemainingCountRange }

impl Codec {
    fn parse(value: &str) -> Result<Self, String> { match value { "exact-rank" => Ok(Self::ExactRank), "remaining-count-range" => Ok(Self::RemainingCountRange), _ => Err("codec must be exact-rank or remaining-count-range".into()) } }
    fn name(self) -> &'static str { match self { Self::ExactRank => "exact-rank", Self::RemainingCountRange => "remaining-count-range" } }
    fn outer_id(self) -> u8 { match self { Self::ExactRank => 2, Self::RemainingCountRange => 5 } }
    fn inner_mode(self) -> u8 { match self { Self::ExactRank => 0, Self::RemainingCountRange => 1 } }
}

impl Case {
    fn parse(value: &str) -> Result<Self, String> {
        match value {
            "alternating" => Ok(Self::Alternating),
            "clustered" => Ok(Self::Clustered),
            "periodic" => Ok(Self::Periodic),
            "random" => Ok(Self::Random),
            _ => Err("case must be alternating, clustered, periodic, or random".into()),
        }
    }
    fn name(self) -> &'static str {
        match self {
            Self::Alternating => "alternating",
            Self::Clustered => "clustered",
            Self::Periodic => "periodic",
            Self::Random => "random",
        }
    }
}

fn case_input(case: Case) -> Vec<u8> {
    // Every 1024-byte tile has 16 symbols with count 64.  Thus the full count
    // metadata is identical across the four orderings.
    let period: [u8; 16] = [0, 5, 10, 15, 4, 9, 14, 3, 8, 13, 2, 7, 12, 1, 6, 11];
    let mut out = Vec::with_capacity(TILE * TILES);
    for tile in 0..TILES {
        match case {
            Case::Alternating => {
                for i in 0..TILE { out.push(((i % 8) * 2 + (i / 8 % 2)) as u8); }
            }
            Case::Clustered => {
                for symbol in 0..16u8 { out.extend(std::iter::repeat(symbol).take(64)); }
            }
            Case::Periodic => {
                for i in 0..TILE { out.push(period[i % period.len()]); }
            }
            Case::Random => {
                // Deterministic Fisher--Yates shuffle of the same multiset;
                // tile is included so no two tiles accidentally share order.
                let start = out.len();
                for symbol in 0..16u8 { out.extend(std::iter::repeat(symbol).take(64)); }
                let mut state = 0xC1A5_0001u64 ^ tile as u64;
                for i in (1..TILE).rev() {
                    state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
                    let j = (state as usize) % (i + 1);
                    out.swap(start + i, start + j);
                }
            }
        }
    }
    out
}

fn validate_histograms(data: &[u8]) -> Result<(), String> {
    if data.len() != TILE * TILES { return Err("unexpected generated length".into()); }
    for tile in data.chunks_exact(TILE) {
        let mut counts = [0usize; 16];
        for &byte in tile {
            let count = counts.get_mut(byte as usize).ok_or("generated symbol outside alphabet")?;
            *count += 1;
        }
        if counts != [64; 16] { return Err("generator does not preserve the frozen histogram".into()); }
    }
    Ok(())
}

fn read_varint(data: &[u8], pos: &mut usize) -> Result<usize, String> {
    let mut value = 0usize;
    for shift in (0..usize::BITS as usize).step_by(7) {
        let byte = *data.get(*pos).ok_or("truncated tile varint")?;
        *pos += 1;
        value |= usize::from(byte & 127).checked_shl(shift as u32).ok_or("tile varint overflow")?;
        if byte < 128 { return Ok(value); }
    }
    Err("oversized tile varint".into())
}

#[derive(Default)]
struct Accounting {
    tile_length_bytes: usize,
    count_header_bytes: usize,
    sequence_mode_bytes: usize,
    sequence_length_bytes: usize,
    sequence_payload_bytes: usize,
    arithmetic_stream_bits: Option<usize>,
    stored_padding_bits: Option<usize>,
}

fn account_payload(payload: &[u8], codec: Codec, source_len: usize) -> Result<Accounting, String> {
    if source_len != TILE * TILES { return Err("unexpected source length for frozen accounting".into()); }
    let mut pos = 0usize;
    let mut result = Accounting::default();
    while pos < payload.len() {
        let before = pos;
        let size = read_varint(payload, &mut pos)?;
        if size > payload.len() - pos { return Err("truncated tile body".into()); }
        let tile = &payload[pos..pos + size];
        if tile.len() <= COUNT_HEADER_BYTES_PER_TILE || tile[COUNT_HEADER_BYTES_PER_TILE] != codec.inner_mode() { return Err("outer coder and tile sequence mode disagree".into()); }
        result.tile_length_bytes += pos - before;
        result.count_header_bytes += COUNT_HEADER_BYTES_PER_TILE;
        result.sequence_mode_bytes += 1;
        match codec {
            Codec::ExactRank => {
                let bytes = EXACT_RANK_BITS_PER_TILE.div_ceil(8);
                if tile.len() != COUNT_HEADER_BYTES_PER_TILE + 1 + bytes { return Err("unexpected canonical-rank tile size".into()); }
                result.sequence_payload_bytes += bytes;
                result.stored_padding_bits = Some(result.stored_padding_bits.unwrap_or(0) + bytes * 8 - EXACT_RANK_BITS_PER_TILE);
            }
            Codec::RemainingCountRange => {
                let mut bit_pos = COUNT_HEADER_BYTES_PER_TILE + 1;
                let bits = read_varint(tile, &mut bit_pos)?;
                if bit_pos + bits.div_ceil(8) != tile.len() { return Err("range bit length contradicts tile length".into()); }
                result.sequence_length_bytes += bit_pos - (COUNT_HEADER_BYTES_PER_TILE + 1);
                result.sequence_payload_bytes += bits.div_ceil(8);
                result.arithmetic_stream_bits = Some(result.arithmetic_stream_bits.unwrap_or(0) + bits);
                result.stored_padding_bits = Some(result.stored_padding_bits.unwrap_or(0) + bits.div_ceil(8) * 8 - bits);
            }
        }
        pos += size;
    }
    if pos != payload.len() || result.count_header_bytes / COUNT_HEADER_BYTES_PER_TILE != TILES { return Err("wrong frozen tile count".into()); }
    Ok(result)
}

fn log2_factorial(n: usize) -> f64 { (1..=n).map(|x| (x as f64).log2()).sum() }
fn ideal_bits() -> f64 { log2_factorial(TILE) - 16.0 * log2_factorial(64) }

fn archive(coder: u8, source_len: usize, payload: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(ARCHIVE_HEADER + payload.len());
    out.extend_from_slice(b"CIXCCV1\0"); out.push(1); out.push(coder);
    out.extend_from_slice(&(source_len as u64).to_le_bytes()); out.extend_from_slice(&(payload.len() as u64).to_le_bytes()); out.extend_from_slice(payload); out
}
fn decode_archive(blob: &[u8]) -> Result<Vec<u8>, String> {
    if blob.len() < ARCHIVE_HEADER || &blob[..8] != b"CIXCCV1\0" || blob[8] != 1 { return Err("invalid experimental archive header".into()); }
    let n = u64::from_le_bytes(blob[10..18].try_into().unwrap()).try_into().map_err(|_| "source length overflow")?;
    let len: usize = u64::from_le_bytes(blob[18..26].try_into().unwrap()).try_into().map_err(|_| "payload length overflow")?;
    if len != blob.len() - ARCHIVE_HEADER { return Err("experimental payload length mismatch".into()); }
    let codec = match blob[9] { 2 => Codec::ExactRank, 5 => Codec::RemainingCountRange, _ => return Err("unknown experimental coder".into()) };
    account_payload(&blob[26..], codec, n)?;
    rank::decode_composition_tiles(&blob[26..], n)
}

fn json_accounting(a: &Accounting) -> String {
    format!("{{\"tile_length_bytes\":{},\"count_header_bytes\":{},\"sequence_mode_bytes\":{},\"sequence_length_bytes\":{},\"sequence_payload_bytes\":{},\"arithmetic_stream_bits\":{},\"stored_padding_bits\":{}}}", a.tile_length_bytes, a.count_header_bytes, a.sequence_mode_bytes, a.sequence_length_bytes, a.sequence_payload_bytes, a.arithmetic_stream_bits.map_or("null".into(), |n| n.to_string()), a.stored_padding_bits.map_or("null".into(), |n| n.to_string()))
}

fn encode(case: Case, codec: Codec, output: &str) -> Result<(), String> {
    let input = case_input(case); validate_histograms(&input)?;
    let start = Instant::now();
    let payload = match codec { Codec::ExactRank => rank::encode_composition_tiles(&input)?, Codec::RemainingCountRange => rank::encode_count_range(&input)? };
    let accounting = account_payload(&payload, codec, input.len())?;
    let stored = archive(codec.outer_id(), input.len(), &payload);
    fs::write(output, &stored).map_err(|e| format!("write archive: {e}"))?;
    println!("{{\"experiment\":\"conditional-cost-v1\",\"operation\":\"encode\",\"case\":\"{}\",\"codec\":\"{}\",\"input_bytes\":{},\"complete_archive_bytes\":{},\"archive_framing_bytes\":{},\"payload_bytes\":{},\"complete_archive_encode_ns\":{},\"ideal_type_class_bits\":{:.6},\"accounting\":{}}}", case.name(), codec.name(), input.len(), stored.len(), ARCHIVE_HEADER, payload.len(), start.elapsed().as_nanos(), ideal_bits() * TILES as f64, json_accounting(&accounting));
    Ok(())
}

fn generate(case: Case, output: &str) -> Result<(), String> {
    let input = case_input(case); validate_histograms(&input)?;
    fs::write(output, input).map_err(|e| format!("write generated input: {e}"))
}

fn decode(input: &str, output: &str) -> Result<(), String> {
    let start = Instant::now();
    let stored = fs::read(input).map_err(|e| format!("read archive: {e}"))?;
    let restored = decode_archive(&stored)?;
    fs::write(output, &restored).map_err(|e| format!("write restored bytes: {e}"))?;
    println!("{{\"experiment\":\"conditional-cost-v1\",\"operation\":\"decode\",\"complete_archive_bytes\":{},\"restored_bytes\":{},\"complete_archive_decode_ns\":{}}}", stored.len(), restored.len(), start.elapsed().as_nanos());
    Ok(())
}

fn main() -> Result<(), String> {
    let mut args = env::args().skip(1);
    match args.next().as_deref() {
        Some("encode") => { let codec = Codec::parse(&args.next().ok_or("missing codec")?)?; let case = Case::parse(&args.next().ok_or("missing case")?)?; let output = args.next().ok_or("missing archive path")?; if args.next().is_some() { Err("usage: conditional_cost_v1 encode CODEC CASE ARCHIVE".into()) } else { encode(case, codec, &output) } }
        Some("decode") => { let input = args.next().ok_or("missing archive path")?; let output = args.next().ok_or("missing restored path")?; if args.next().is_some() { Err("usage: conditional_cost_v1 decode ARCHIVE RESTORED".into()) } else { decode(&input, &output) } }
        Some("generate") => { let case = Case::parse(&args.next().ok_or("missing case")?)?; let output = args.next().ok_or("missing input path")?; if args.next().is_some() { Err("usage: conditional_cost_v1 generate CASE INPUT".into()) } else { generate(case, &output) } }
        _ => Err("usage: conditional_cost_v1 generate CASE INPUT | encode CODEC CASE ARCHIVE | decode ARCHIVE RESTORED".into()),
    }
}
