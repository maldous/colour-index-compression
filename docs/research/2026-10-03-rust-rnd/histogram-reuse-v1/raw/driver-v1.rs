//! Unregistered histogram-reuse-v1 research prototype. It wraps CIXCCV1
//! archives only; it does not change CIX production containers or selectors.
//! The dependency is the already-built cix_native rlib plus Rust std only.

use cix_native::rank;
use num_bigint::BigUint;
use num_traits::{One, Zero};
use std::{env, fs, io::Read};

const CIXCC_HEADER: usize = 26;
const MAX_ARCHIVE: usize = 1024 * 1024;
const MAX_PACKED: usize = MAX_ARCHIVE + 64 * 1024;
const MAX_TILES: usize = 1024;

#[derive(Default)]
struct PackStats { literals: usize, references: usize, header_bytes_saved: usize }

fn put_varint(mut value: usize, out: &mut Vec<u8>) { while value >= 128 { out.push((value as u8 & 127) | 128); value >>= 7; } out.push(value as u8); }
fn varint_len(value: usize) -> usize { let mut out = Vec::new(); put_varint(value, &mut out); out.len() }
fn read_varint(data: &[u8], pos: &mut usize) -> Result<usize, String> {
    let start = *pos; let mut value = 0usize;
    for shift in (0..usize::BITS as usize).step_by(7) {
        let byte = *data.get(*pos).ok_or("truncated varint")?; *pos += 1;
        value |= usize::from(byte & 127).checked_shl(shift as u32).ok_or("varint overflow")?;
        if byte < 128 { let mut canonical = Vec::new(); put_varint(value, &mut canonical); return if data[start..*pos] == canonical { Ok(value) } else { Err("noncanonical varint".into()) }; }
    }
    Err("oversized varint".into())
}
fn crc32(data: &[u8]) -> u32 { let mut crc = !0u32; for &byte in data { crc ^= u32::from(byte); for _ in 0..8 { crc = (crc >> 1) ^ (0xedb88320 & (0u32.wrapping_sub(crc & 1))); } } !crc }
fn take<'a>(data: &'a [u8], pos: &mut usize, n: usize) -> Result<&'a [u8], String> { let end = pos.checked_add(n).ok_or("offset overflow")?; let out = data.get(*pos..end).ok_or("truncated archive")?; *pos = end; Ok(out) }
fn choose(n: usize, k: usize) -> BigUint { if k > n { return BigUint::zero(); } let mut value = BigUint::one(); for i in 1..=k.min(n-k) { value *= n - k.min(n-k) + i; value /= i; } value }
fn fixed_width(n: usize, k: usize) -> usize { let value = choose(n, k); if value.is_zero() { return 0; } (value - BigUint::one()).bits() as usize }
fn cix_header_len(tile: &[u8], tile_n: usize) -> Result<usize, String> {
    let mut pos = 0usize; let m = read_varint(tile, &mut pos)?;
    if m == 0 || m > 256 || m > tile_n { return Err("invalid active symbol count".into()); }
    if m < 256 { pos = pos.checked_add(fixed_width(256, m).div_ceil(8)).ok_or("histogram header overflow")?; }
    if m > 1 { pos = pos.checked_add(fixed_width(tile_n - 1, m - 1).div_ceil(8)).ok_or("histogram header overflow")?; }
    if pos >= tile.len() { return Err("CIXCC tile lacks sequence body".into()); }
    Ok(pos)
}
fn cixcc_source_len(header: &[u8]) -> Result<usize, String> {
    if header.len() != CIXCC_HEADER || &header[..8] != b"CIXCCV1\0" || header[8] != 1 || !matches!(header[9], 2 | 5) { return Err("unsupported CIXCCV1 archive".into()); }
    let n: usize = u64::from_le_bytes(header[10..18].try_into().unwrap()).try_into().map_err(|_| "CIXCC source length overflow")?;
    if n == 0 || n > MAX_ARCHIVE || n % 1024 != 0 { return Err("CIXCC bounded length violation".into()); } Ok(n)
}
fn read_bounded(path: &str, maximum: usize) -> Result<Vec<u8>, String> {
    let mut file = fs::File::open(path).map_err(|e| e.to_string())?;
    if !file.metadata().map_err(|e| e.to_string())?.is_file() { return Err("input is not a regular file".into()); }
    let mut bytes = Vec::new();
    file.take(maximum as u64 + 1).read_to_end(&mut bytes).map_err(|e| e.to_string())?;
    if bytes.len() > maximum { return Err("input exceeds bounded archive limit".into()); }
    Ok(bytes)
}

fn parse_cixcc(blob: &[u8]) -> Result<(&[u8], Vec<(&[u8], &[u8], &[u8])>), String> {
    if blob.len() < CIXCC_HEADER { return Err("truncated CIXCCV1 archive".into()); }
    let n = cixcc_source_len(&blob[..CIXCC_HEADER])?;
    let payload_len: usize = u64::from_le_bytes(blob[18..26].try_into().unwrap()).try_into().map_err(|_| "CIXCC payload length overflow")?;
    if payload_len != blob.len() - CIXCC_HEADER || n == 0 || n > MAX_ARCHIVE || n % 1024 != 0 { return Err("CIXCC bounded length violation".into()); }
    let mut pos = CIXCC_HEADER; let mut tiles = Vec::new();
    while pos < blob.len() {
        if tiles.len() == MAX_TILES { return Err("too many CIXCC tiles".into()); }
        let begin = pos; let size = read_varint(blob, &mut pos)?; let prefix_end = pos; let tile = take(blob, &mut pos, size)?;
        let header_len = cix_header_len(tile, 1024)?;
        let expected_mode = if blob[9] == 2 { 0 } else { 1 };
        if tile[header_len] != expected_mode { return Err("CIXCC outer coder and inner sequence mode disagree".into()); }
        tiles.push((&blob[begin..prefix_end], &tile[..header_len], &tile[header_len..]));
    }
    if tiles.len() != n / 1024 { return Err("CIXCC tile count contradicts source length".into()); }
    Ok((&blob[..CIXCC_HEADER], tiles))
}

fn native_decode(blob: &[u8]) -> Result<Vec<u8>, String> {
    let (_, _) = parse_cixcc(blob)?;
    let n: usize = u64::from_le_bytes(blob[10..18].try_into().unwrap()).try_into().map_err(|_| "CIXCC source length overflow")?;
    rank::decode_composition_tiles(&blob[CIXCC_HEADER..], n)
}

fn pack(native: &[u8]) -> Result<(Vec<u8>, PackStats), String> {
    let (native_header, tiles) = parse_cixcc(native)?;
    let mut out = Vec::with_capacity(native.len()); out.extend_from_slice(b"CIXHRV1\0"); out.push(1); out.extend_from_slice(&(native.len() as u64).to_le_bytes()); out.extend_from_slice(&crc32(native).to_le_bytes()); out.extend_from_slice(native_header); put_varint(tiles.len(), &mut out);
    let mut dictionary: Vec<&[u8]> = Vec::new(); let mut stats = PackStats::default();
    for (length_prefix, header, sequence) in tiles {
        if let Some(id) = dictionary.iter().position(|candidate| *candidate == header) {
            out.push(1); out.extend_from_slice(length_prefix); put_varint(id, &mut out); out.extend_from_slice(sequence);
            stats.references += 1; stats.header_bytes_saved += header.len().saturating_sub(varint_len(id));
        } else {
            if dictionary.len() == MAX_TILES { return Err("histogram dictionary exceeds bound".into()); }
            out.push(0); out.extend_from_slice(length_prefix); out.extend_from_slice(header); out.extend_from_slice(sequence);
            dictionary.push(header); stats.literals += 1;
        }
    }
    let envelope_crc = crc32(&out); out.extend_from_slice(&envelope_crc.to_le_bytes()); if out.len() > MAX_PACKED { return Err("histogram-reuse archive exceeds bound".into()); } Ok((out, stats))
}

fn unpack(blob: &[u8]) -> Result<Vec<u8>, String> {
    if blob.len() > MAX_PACKED { return Err("histogram-reuse archive exceeds bound".into()); }
    if blob.len() < 8 + 1 + 8 + 4 + CIXCC_HEADER + 4 || &blob[..8] != b"CIXHRV1\0" || blob[8] != 1 { return Err("unsupported histogram-reuse archive".into()); }
    let stored_envelope_crc = u32::from_le_bytes(blob[blob.len() - 4..].try_into().unwrap());
    if crc32(&blob[..blob.len() - 4]) != stored_envelope_crc { return Err("CIXHRV1 envelope CRC mismatch".into()); }
    // Everything below is bounded to the verified body. The trailing CRC is
    // never available to a tag, varint, header, reference, or sequence read.
    let blob = &blob[..blob.len() - 4];
    let original_len: usize = u64::from_le_bytes(blob[9..17].try_into().unwrap()).try_into().map_err(|_| "original length overflow")?;
    let expected_crc = u32::from_le_bytes(blob[17..21].try_into().unwrap());
    if original_len > MAX_ARCHIVE { return Err("original archive exceeds bound".into()); }
    let native_header = &blob[21..21 + CIXCC_HEADER]; let source_len = cixcc_source_len(native_header)?; let mut pos = 21 + CIXCC_HEADER; let count = read_varint(blob, &mut pos)?;
    if count == 0 || count > MAX_TILES || count != source_len / 1024 { return Err("invalid histogram-reuse tile count".into()); }
    let mut native = Vec::with_capacity(original_len); native.extend_from_slice(native_header); let mut dictionary: Vec<Vec<u8>> = Vec::new();
    for _ in 0..count {
        let tag = *blob.get(pos).ok_or("truncated histogram-reuse tag")?; pos += 1;
        let length_start = pos; let tile_len = read_varint(blob, &mut pos)?; let length_prefix = &blob[length_start..pos];
        let header = match tag {
            0 => { let header_len = cix_header_len(&blob[pos..], 1024)?; let h = take(blob, &mut pos, header_len)?.to_vec(); dictionary.push(h); dictionary.last().unwrap().as_slice() }
            1 => { let id = read_varint(blob, &mut pos)?; dictionary.get(id).ok_or("histogram reference outside dictionary")?.as_slice() }
            _ => return Err("invalid histogram-reuse tag".into()),
        };
        if tile_len <= header.len() { return Err("invalid reconstructed tile size".into()); }
        let sequence = take(blob, &mut pos, tile_len - header.len())?;
        let growth = length_prefix.len().checked_add(header.len()).and_then(|v| v.checked_add(sequence.len())).ok_or("reconstructed archive growth overflow")?;
        if growth > original_len.saturating_sub(native.len()) { return Err("reconstructed archive exceeds declared length".into()); }
        native.extend_from_slice(length_prefix); native.extend_from_slice(header); native.extend_from_slice(sequence);
    }
    if pos != blob.len() || native.len() != original_len || crc32(&native) != expected_crc { return Err("reconstructed native archive length or CRC mismatch".into()); }
    // Archive-only proof: reconstruction occurs before this call; the native
    // decoder receives exactly the reconstructed standalone CIXCCV1 bytes.
    native_decode(&native)?;
    Ok(native)
}

fn fixture(kind: &str) -> Result<Vec<u8>, String> {
    let mut source = Vec::with_capacity(16 * 1024);
    for tile in 0..16usize {
        let delta = match kind { "identical" => 0, "weak" => (tile / 2) as isize, "absent" => tile as isize, _ => return Err("fixture must be identical, weak, or absent".into()) };
        let mut counts = [64usize; 16]; counts[0] = (64isize + delta) as usize; counts[1] = (64isize - delta) as usize;
        for (symbol, &count) in counts.iter().enumerate() { source.extend(std::iter::repeat(symbol as u8).take(count)); }
    }
    let payload = rank::encode_composition_tiles(&source)?; let mut native = Vec::with_capacity(CIXCC_HEADER + payload.len()); native.extend_from_slice(b"CIXCCV1\0"); native.push(1); native.push(2); native.extend_from_slice(&(source.len() as u64).to_le_bytes()); native.extend_from_slice(&(payload.len() as u64).to_le_bytes()); native.extend_from_slice(&payload); Ok(native)
}

fn main() -> Result<(), String> {
    let mut args = env::args().skip(1); let op = args.next().ok_or("usage: histogram_reuse_v1 fixture KIND NATIVE | pack NATIVE HRV | unpack HRV NATIVE")?;
    match op.as_str() {
        "fixture" => { let kind = args.next().ok_or("missing fixture kind")?; let output = args.next().ok_or("missing native output")?; if args.next().is_some() { return Err("usage: histogram_reuse_v1 fixture KIND NATIVE".into()); } fs::write(output, fixture(&kind)?).map_err(|e| e.to_string())?; }
        "pack" => { let input = args.next().ok_or("missing native input")?; let output = args.next().ok_or("missing HRV output")?; if args.next().is_some() { return Err("usage: histogram_reuse_v1 pack NATIVE HRV".into()); } let native = read_bounded(&input, MAX_ARCHIVE)?; let (packed, stats) = pack(&native)?; fs::write(output, &packed).map_err(|e| e.to_string())?; println!("{{\"native_bytes\":{},\"histogram_reuse_bytes\":{},\"literals\":{},\"references\":{},\"header_bytes_saved_before_wrapper\":{},\"delta_bytes\":{}}}", native.len(), packed.len(), stats.literals, stats.references, stats.header_bytes_saved, packed.len() as isize - native.len() as isize); }
        "unpack" => { let input = args.next().ok_or("missing HRV input")?; let output = args.next().ok_or("missing native output")?; if args.next().is_some() { return Err("usage: histogram_reuse_v1 unpack HRV NATIVE".into()); } let native = unpack(&read_bounded(&input, MAX_PACKED)?)?; fs::write(output, native).map_err(|e| e.to_string())?; }
        _ => return Err("usage: histogram_reuse_v1 fixture KIND NATIVE | pack NATIVE HRV | unpack HRV NATIVE".into()),
    } Ok(())
}
