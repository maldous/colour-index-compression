//! Bounded, standalone lane-transposition experiment; it is not production code.
use cix_native::{adaptive, huffman, legacy_lz};
use std::{
    env,
    fs::{self, File},
    io::Read,
    time::Instant,
};

const MAGIC: &[u8; 4] = b"NCSL";
const VERSION: u8 = 1;
const HEADER_BYTES: usize = 17;
const LANE_METADATA_BYTES: usize = 9;
const MAX_SOURCE: usize = 4096;
const MAX_ARCHIVE: usize = 32768;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
enum Route {
    Raw = 0,
    Huffman = 1,
    Adaptive = 2,
    LegacyLz = 3,
}
impl Route {
    fn from_id(id: u8) -> Result<Self, String> {
        match id {
            0 => Ok(Self::Raw),
            1 => Ok(Self::Huffman),
            2 => Ok(Self::Adaptive),
            3 => Ok(Self::LegacyLz),
            _ => Err("unknown NCSL route id".into()),
        }
    }
    fn name(self) -> &'static str {
        match self {
            Self::Raw => "raw",
            Self::Huffman => "huffman",
            Self::Adaptive => "adaptive",
            Self::LegacyLz => "legacy-lz",
        }
    }
}
#[derive(Clone)]
struct Lane {
    route: Route,
    decoded_len: usize,
    payload: Vec<u8>,
}
struct Candidate {
    stride: usize,
    transform: u8,
    complete_bytes: usize,
    lanes: Vec<Lane>,
}

fn crc32(data: &[u8]) -> u32 {
    let mut value = !0u32;
    for &byte in data {
        value ^= u32::from(byte);
        for _ in 0..8 {
            value = if value & 1 != 0 {
                (value >> 1) ^ 0xedb8_8320
            } else {
                value >> 1
            };
        }
    }
    !value
}
fn bounded_read(path: &str, cap: usize, label: &str) -> Result<Vec<u8>, String> {
    let meta = fs::metadata(path).map_err(|e| format!("{label} metadata: {e}"))?;
    if !meta.is_file() || meta.len() > cap as u64 {
        return Err(format!("{label} exceeds bound"));
    }
    let mut file = File::open(path).map_err(|e| format!("{label} open: {e}"))?;
    let mut data = Vec::new();
    file.take((cap + 1) as u64)
        .read_to_end(&mut data)
        .map_err(|e| format!("{label} read: {e}"))?;
    if data.len() > cap {
        Err(format!("{label} exceeds bound"))
    } else {
        Ok(data)
    }
}
fn encode_route(route: Route, input: &[u8]) -> Result<Vec<u8>, String> {
    match route {
        Route::Raw => Ok(input.to_vec()),
        Route::Huffman => huffman::encode(input).map_err(|e| e.to_string()),
        Route::Adaptive => adaptive::encode_general(input, 0, 8, &[], 1),
        Route::LegacyLz => Ok(legacy_lz::encode(input, &[], 1)?.payload),
    }
}
fn decode_route(route: Route, payload: &[u8], length: usize) -> Result<Vec<u8>, String> {
    let decoded = match route {
        Route::Raw => {
            if payload.len() != length {
                return Err("raw lane length mismatch".into());
            }
            payload.to_vec()
        }
        Route::Huffman => {
            // huffman::decode allocates from this embedded value; reject it before call.
            if payload.len() < 19 || payload[0] != huffman::VERSION {
                return Err("invalid Huffman lane header".into());
            }
            let declared = u64::from_le_bytes(
                payload[3..11]
                    .try_into()
                    .map_err(|_| "invalid Huffman lane length")?,
            );
            if declared != length as u64 {
                return Err("Huffman embedded lane length mismatch".into());
            }
            huffman::decode(payload).map_err(|e| e.to_string())?
        }
        Route::Adaptive => adaptive::decode_general(payload, length, &[], 1)?,
        Route::LegacyLz => legacy_lz::decode(payload, length, &[], 4096)?,
    };
    if decoded.len() != length {
        return Err("lane decoded length mismatch".into());
    }
    Ok(decoded)
}
fn lane_bytes(input: &[u8], stride: usize, transform: u8, offset: usize) -> Vec<u8> {
    let mut output = Vec::new();
    for index in (offset..input.len()).step_by(stride) {
        output.push(if transform == 1 && offset > 0 {
            input[index].wrapping_sub(input[index - 1])
        } else {
            input[index]
        });
    }
    output
}
fn make_candidate(input: &[u8], stride: usize, transform: u8) -> Result<Candidate, String> {
    if stride == 0 || stride > 8 || (transform == 1 && stride == 1) {
        return Err("invalid candidate".into());
    }
    if input.is_empty() {
        return Ok(Candidate {
            stride: 1,
            transform: 0,
            complete_bytes: HEADER_BYTES,
            lanes: Vec::new(),
        });
    }
    if stride > input.len() {
        return Err("candidate stride exceeds source".into());
    }
    let mut lanes = Vec::with_capacity(stride);
    for offset in 0..stride {
        let bytes = lane_bytes(input, stride, transform, offset);
        let mut best: Option<Lane> = None;
        for route in [Route::Raw, Route::Huffman, Route::Adaptive, Route::LegacyLz] {
            let candidate = Lane {
                route,
                decoded_len: bytes.len(),
                payload: encode_route(route, &bytes)?,
            };
            if best.as_ref().map_or(true, |current| {
                (candidate.payload.len(), candidate.route) < (current.payload.len(), current.route)
            }) {
                best = Some(candidate);
            }
        }
        lanes.push(best.ok_or("missing fixed lane route")?);
    }
    let payload_bytes = lanes.iter().try_fold(0usize, |sum, lane| {
        sum.checked_add(LANE_METADATA_BYTES + lane.payload.len())
            .ok_or("lane size overflow")
    })?;
    Ok(Candidate {
        stride,
        transform,
        complete_bytes: HEADER_BYTES
            .checked_add(payload_bytes)
            .ok_or("archive size overflow")?,
        lanes,
    })
}
fn candidate_parameters(policy: &str, length: usize) -> Result<Vec<(usize, u8)>, String> {
    let limit = length.clamp(1, 8);
    Ok(match policy {
        "auto" => {
            let mut values = vec![(1, 0)];
            for stride in 2..=limit {
                values.extend([(stride, 0), (stride, 1)]);
            }
            values
        }
        "shuffle" => (1..=limit).map(|stride| (stride, 0)).collect(),
        "whole" => vec![(1, 0)],
        _ => return Err("policy must be auto, shuffle, or whole".into()),
    })
}
fn pack(input: &[u8], candidate: &Candidate) -> Result<Vec<u8>, String> {
    let count = candidate.lanes.len();
    if input.is_empty() {
        if candidate.stride != 1 || candidate.transform != 0 || count != 0 {
            return Err("noncanonical empty candidate".into());
        }
    } else if candidate.stride > input.len() || count != candidate.stride {
        return Err("invalid lane candidate".into());
    }
    let mut archive = Vec::with_capacity(candidate.complete_bytes);
    archive.extend_from_slice(MAGIC);
    archive.push(VERSION);
    archive.extend_from_slice(&(input.len() as u32).to_le_bytes());
    archive.extend_from_slice(&crc32(input).to_le_bytes());
    archive.push(candidate.stride as u8);
    archive.push(candidate.transform);
    archive.extend_from_slice(&(count as u16).to_le_bytes());
    for lane in &candidate.lanes {
        archive.push(lane.route as u8);
        archive.extend_from_slice(&(lane.decoded_len as u32).to_le_bytes());
        archive.extend_from_slice(&(lane.payload.len() as u32).to_le_bytes());
        archive.extend_from_slice(&lane.payload);
    }
    if archive.len() != candidate.complete_bytes || archive.len() > MAX_ARCHIVE {
        return Err("archive exceeds bound".into());
    }
    Ok(archive)
}
fn read_u32(data: &[u8], position: &mut usize) -> Result<usize, String> {
    let end = position.checked_add(4).ok_or("u32 offset overflow")?;
    let bytes = data.get(*position..end).ok_or("truncated u32")?;
    *position = end;
    Ok(u32::from_le_bytes(bytes.try_into().map_err(|_| "invalid u32")?) as usize)
}
fn unpack(archive: &[u8]) -> Result<Vec<u8>, String> {
    if archive.len() < HEADER_BYTES
        || archive.len() > MAX_ARCHIVE
        || archive.get(..4) != Some(MAGIC)
        || archive[4] != VERSION
    {
        return Err("invalid NCSL header".into());
    }
    let mut position = 5;
    let source_len = read_u32(archive, &mut position)?;
    let source_crc = read_u32(archive, &mut position)? as u32;
    let stride = *archive.get(position).ok_or("truncated stride")? as usize;
    position += 1;
    let transform = *archive.get(position).ok_or("truncated transform")?;
    position += 1;
    let count_end = position
        .checked_add(2)
        .ok_or("lane count offset overflow")?;
    let lane_count = u16::from_le_bytes(
        archive
            .get(position..count_end)
            .ok_or("truncated lane count")?
            .try_into()
            .map_err(|_| "invalid lane count")?,
    ) as usize;
    position = count_end;
    if source_len > MAX_SOURCE
        || !(1..=8).contains(&stride)
        || transform > 1
        || (transform == 1 && stride == 1)
    {
        return Err("invalid NCSL bounds".into());
    }
    if source_len == 0 {
        if stride != 1 || transform != 0 || lane_count != 0 {
            return Err("noncanonical empty NCSL".into());
        }
    } else if stride > source_len || lane_count != stride {
        return Err("invalid NCSL lane count".into());
    }
    let mut lanes = Vec::with_capacity(lane_count);
    for offset in 0..lane_count {
        let route = Route::from_id(*archive.get(position).ok_or("truncated route")?)?;
        position += 1;
        let declared_len = read_u32(archive, &mut position)?;
        let payload_len = read_u32(archive, &mut position)?;
        let expected_len = (source_len - offset).div_ceil(stride);
        if declared_len != expected_len || declared_len > MAX_SOURCE {
            return Err("invalid declared lane length".into());
        }
        let payload_end = position
            .checked_add(payload_len)
            .ok_or("payload offset overflow")?;
        let payload = archive
            .get(position..payload_end)
            .ok_or("truncated lane payload")?;
        // Validate all declared algebra and byte bounds before any decoder call.
        let decoded = decode_route(route, payload, declared_len)?;
        if decoded.len() != declared_len {
            return Err("lane result length mismatch".into());
        }
        position = payload_end;
        lanes.push(decoded);
    }
    if position != archive.len() {
        return Err("trailing NCSL bytes".into());
    }
    let mut output = vec![0u8; source_len];
    for (offset, lane) in lanes.iter().enumerate() {
        for (row, &value) in lane.iter().enumerate() {
            let index = row * stride + offset;
            output[index] = if transform == 1 && offset > 0 {
                value.wrapping_add(output[index - 1])
            } else {
                value
            };
        }
    }
    if crc32(&output) != source_crc {
        return Err("NCSL source CRC mismatch".into());
    }
    Ok(output)
}
fn encode(policy: &str, input_path: &str, archive_path: &str) -> Result<(), String> {
    let input = bounded_read(input_path, MAX_SOURCE, "input")?;
    let started = Instant::now();
    let mut candidates = Vec::new();
    for (stride, transform) in candidate_parameters(policy, input.len())? {
        candidates.push(make_candidate(&input, stride, transform)?);
    }
    let selected = candidates
        .iter()
        .min_by_key(|candidate| {
            (
                candidate.complete_bytes,
                candidate.stride,
                candidate.transform,
            )
        })
        .ok_or("no candidates")?;
    let archive = pack(&input, selected)?;
    let search_elapsed_ns = started.elapsed().as_nanos();
    if unpack(&archive)? != input {
        return Err("in-process restoration mismatch".into());
    }
    fs::write(archive_path, &archive).map_err(|e| format!("archive write: {e}"))?;
    print!(
        "{{\"source_bytes\":{},\"archive_bytes\":{},\"search_elapsed_ns\":{},\"candidates\":[",
        input.len(),
        archive.len(),
        search_elapsed_ns
    );
    for (index, candidate) in candidates.iter().enumerate() {
        if index != 0 {
            print!(",");
        }
        print!(
            "{{\"stride\":{},\"transform\":{},\"complete_bytes\":{}}}",
            candidate.stride, candidate.transform, candidate.complete_bytes
        );
    }
    print!(
        "],\"selected_stride\":{},\"selected_transform\":{},\"lanes\":[",
        selected.stride, selected.transform
    );
    let mut offset = HEADER_BYTES;
    for (index, lane) in selected.lanes.iter().enumerate() {
        if index != 0 {
            print!(",");
        }
        let total = LANE_METADATA_BYTES + lane.payload.len();
        print!("{{\"archive_offset\":{},\"input_offset\":{},\"stride\":{},\"count\":{},\"route\":\"{}\",\"metadata_bytes\":9,\"payload_bytes\":{},\"total_bytes\":{}}}", offset, index, selected.stride, lane.decoded_len, lane.route.name(), lane.payload.len(), total);
        offset += total;
    }
    println!("]}}");
    Ok(())
}
fn decode(archive_path: &str, output_path: &str) -> Result<(), String> {
    let started = Instant::now();
    let restored = unpack(&bounded_read(archive_path, MAX_ARCHIVE, "archive")?)?;
    fs::write(output_path, &restored).map_err(|e| format!("output write: {e}"))?;
    println!(
        "{{\"restored_bytes\":{},\"decode_elapsed_ns\":{}}}",
        restored.len(),
        started.elapsed().as_nanos()
    );
    Ok(())
}
fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    match args.as_slice() { [command, flag, policy, input, archive] if command == "encode" && flag == "--policy" => encode(policy, input, archive), [command, archive, output] if command == "decode" => decode(archive, output), _ => Err("usage: segmentation_lanes encode --policy auto|shuffle|whole INPUT ARCHIVE | segmentation_lanes decode ARCHIVE OUT".into()) }
}
fn main() {
    if let Err(error) = run() {
        eprintln!("segmentation_lanes: {error}");
        std::process::exit(1);
    }
}
