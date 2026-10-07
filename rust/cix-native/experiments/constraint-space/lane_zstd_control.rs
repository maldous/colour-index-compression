//! Native libzstd 1.5.5 strong-control reference for a fixed lane mapping.
//! This investigation file is generic software only and is not a candidate
//! production archive, selector, or decoder path.

use std::{
    env,
    ffi::{c_int, c_uint, c_void},
    fs::{self, File},
    io::Read,
    time::Instant,
};

const MAGIC: &[u8; 4] = b"ZSC1";
const VERSION: u8 = 1;
const HEADER_BYTES: usize = 21;
const MAX_SOURCE: usize = 4096;
const MAX_ARCHIVE: usize = 32768;
const ZSTD_LEVEL: c_int = 19;

// libzstd 1.5.5 is provided by the host.  The compression destination is
// ZSTD_compressBound(input.len()), and decompression writes only into the
// exactly header-declared source length after all framing is validated.
#[link(name = "zstd")]
unsafe extern "C" {
    fn ZSTD_compressBound(src_size: usize) -> usize;
    fn ZSTD_compress(
        dst: *mut c_void,
        dst_capacity: usize,
        src: *const c_void,
        src_size: usize,
        compression_level: c_int,
    ) -> usize;
    fn ZSTD_decompress(
        dst: *mut c_void,
        dst_capacity: usize,
        src: *const c_void,
        compressed_size: usize,
    ) -> usize;
    fn ZSTD_isError(code: usize) -> c_uint;
    fn ZSTD_findFrameCompressedSize(src: *const c_void, src_size: usize) -> usize;
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
    let metadata = fs::metadata(path).map_err(|error| format!("{label} metadata: {error}"))?;
    if !metadata.is_file() || metadata.len() > cap as u64 {
        return Err(format!("{label} exceeds bound"));
    }
    let mut file = File::open(path).map_err(|error| format!("{label} open: {error}"))?;
    let mut data = Vec::new();
    file.take((cap + 1) as u64)
        .read_to_end(&mut data)
        .map_err(|error| format!("{label} read: {error}"))?;
    if data.len() > cap {
        Err(format!("{label} exceeds bound"))
    } else {
        Ok(data)
    }
}

fn zstd_compress(input: &[u8]) -> Result<Vec<u8>, String> {
    let bound = unsafe { ZSTD_compressBound(input.len()) };
    if unsafe { ZSTD_isError(bound) } != 0 || bound > MAX_ARCHIVE - HEADER_BYTES {
        return Err("zstd compression bound exceeds archive bound".into());
    }
    let mut output = vec![0u8; bound];
    let written = unsafe {
        ZSTD_compress(
            output.as_mut_ptr().cast(),
            output.len(),
            input.as_ptr().cast(),
            input.len(),
            ZSTD_LEVEL,
        )
    };
    if unsafe { ZSTD_isError(written) } != 0 || written > output.len() {
        return Err("zstd compression failed".into());
    }
    output.truncate(written);
    Ok(output)
}

fn zstd_decompress(frame: &[u8], output_len: usize) -> Result<Vec<u8>, String> {
    let frame_len = unsafe { ZSTD_findFrameCompressedSize(frame.as_ptr().cast(), frame.len()) };
    if unsafe { ZSTD_isError(frame_len) } != 0 || frame_len != frame.len() {
        return Err("ZSC1 requires exactly one complete zstd frame".into());
    }
    let mut output = vec![0u8; output_len];
    let written = unsafe {
        ZSTD_decompress(
            output.as_mut_ptr().cast(),
            output.len(),
            frame.as_ptr().cast(),
            frame.len(),
        )
    };
    if unsafe { ZSTD_isError(written) } != 0 || written != output_len {
        return Err("zstd decoded length mismatch".into());
    }
    Ok(output)
}

fn transform(input: &[u8], stride: usize, transform: u8) -> Vec<u8> {
    let mut output = Vec::with_capacity(input.len());
    for offset in 0..stride {
        for index in (offset..input.len()).step_by(stride) {
            output.push(if transform == 1 && offset > 0 {
                input[index].wrapping_sub(input[index - 1])
            } else {
                input[index]
            });
        }
    }
    output
}

fn inverse(
    transposed: &[u8],
    source_len: usize,
    stride: usize,
    transform: u8,
) -> Result<Vec<u8>, String> {
    if transposed.len() != source_len {
        return Err("transposed length mismatch".into());
    }
    let mut output = vec![0u8; source_len];
    let mut position = 0usize;
    for offset in 0..stride {
        let count = (source_len - offset).div_ceil(stride);
        let end = position
            .checked_add(count)
            .ok_or("lane position overflow")?;
        for (row, &value) in transposed
            .get(position..end)
            .ok_or("truncated lane stream")?
            .iter()
            .enumerate()
        {
            let index = row * stride + offset;
            output[index] = if transform == 1 && offset > 0 {
                value.wrapping_add(output[index - 1])
            } else {
                value
            };
        }
        position = end;
    }
    if position != transposed.len() {
        return Err("trailing lane stream".into());
    }
    Ok(output)
}

fn validate_parameters(
    source_len: usize,
    stride: usize,
    transform: u8,
    lane_count: usize,
) -> Result<(), String> {
    if !(1..=8).contains(&stride) || transform > 1 || (transform == 1 && stride == 1) {
        return Err("invalid ZSC1 transform parameters".into());
    }
    if source_len == 0 {
        if stride != 1 || transform != 0 || lane_count != 0 {
            return Err("noncanonical empty ZSC1".into());
        }
    } else if stride > source_len || lane_count != stride {
        return Err("invalid ZSC1 lane count".into());
    }
    Ok(())
}

fn pack(input: &[u8], stride: usize, transform_kind: u8) -> Result<Vec<u8>, String> {
    let lane_count = if input.is_empty() { 0 } else { stride };
    validate_parameters(input.len(), stride, transform_kind, lane_count)?;
    let payload = zstd_compress(&transform(input, stride, transform_kind))?;
    let total = HEADER_BYTES
        .checked_add(payload.len())
        .ok_or("archive size overflow")?;
    if total > MAX_ARCHIVE || payload.len() > u32::MAX as usize {
        return Err("archive exceeds bound".into());
    }
    let mut archive = Vec::with_capacity(total);
    archive.extend_from_slice(MAGIC);
    archive.push(VERSION);
    archive.extend_from_slice(&(input.len() as u32).to_le_bytes());
    archive.extend_from_slice(&crc32(input).to_le_bytes());
    archive.push(stride as u8);
    archive.push(transform_kind);
    archive.extend_from_slice(&(lane_count as u16).to_le_bytes());
    archive.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    archive.extend_from_slice(&payload);
    Ok(archive)
}

fn read_u32(data: &[u8], position: &mut usize) -> Result<usize, String> {
    let end = position.checked_add(4).ok_or("u32 offset overflow")?;
    let value = u32::from_le_bytes(
        data.get(*position..end)
            .ok_or("truncated u32")?
            .try_into()
            .map_err(|_| "invalid u32")?,
    ) as usize;
    *position = end;
    Ok(value)
}

fn unpack(archive: &[u8]) -> Result<Vec<u8>, String> {
    if archive.len() < HEADER_BYTES
        || archive.len() > MAX_ARCHIVE
        || archive.get(..4) != Some(MAGIC)
        || archive[4] != VERSION
    {
        return Err("invalid ZSC1 header".into());
    }
    let mut position = 5;
    let source_len = read_u32(archive, &mut position)?;
    let source_crc = read_u32(archive, &mut position)? as u32;
    let stride = *archive.get(position).ok_or("truncated stride")? as usize;
    position += 1;
    let transform_kind = *archive.get(position).ok_or("truncated transform")?;
    position += 1;
    let count_end = position.checked_add(2).ok_or("lane count overflow")?;
    let lane_count = u16::from_le_bytes(
        archive
            .get(position..count_end)
            .ok_or("truncated lane count")?
            .try_into()
            .map_err(|_| "invalid lane count")?,
    ) as usize;
    position = count_end;
    let compressed_len = read_u32(archive, &mut position)?;
    if source_len > MAX_SOURCE {
        return Err("ZSC1 source exceeds bound".into());
    }
    validate_parameters(source_len, stride, transform_kind, lane_count)?;
    let payload_end = position
        .checked_add(compressed_len)
        .ok_or("compressed length overflow")?;
    let payload = archive
        .get(position..payload_end)
        .ok_or("truncated zstd frame")?;
    if payload_end != archive.len() {
        return Err("trailing ZSC1 bytes".into());
    }
    let transposed = zstd_decompress(payload, source_len)?;
    let output = inverse(&transposed, source_len, stride, transform_kind)?;
    if crc32(&output) != source_crc {
        return Err("ZSC1 source CRC mismatch".into());
    }
    Ok(output)
}

fn parse_stride(value: &str) -> Result<usize, String> {
    match value.parse::<usize>() {
        Ok(stride @ 1..=8) => Ok(stride),
        _ => Err("stride must be 1 through 8".into()),
    }
}
fn parse_transform(value: &str) -> Result<u8, String> {
    match value {
        "0" => Ok(0),
        "1" => Ok(1),
        _ => Err("transform must be 0 or 1".into()),
    }
}

fn encode(
    stride: usize,
    transform_kind: u8,
    input_path: &str,
    archive_path: &str,
) -> Result<(), String> {
    let input = bounded_read(input_path, MAX_SOURCE, "input")?;
    validate_parameters(
        input.len(),
        stride,
        transform_kind,
        if input.is_empty() { 0 } else { stride },
    )?;
    let started = Instant::now();
    let archive = pack(&input, stride, transform_kind)?;
    if unpack(&archive)? != input {
        return Err("in-process restoration mismatch".into());
    }
    let elapsed_ns = started.elapsed().as_nanos();
    fs::write(archive_path, &archive).map_err(|error| format!("archive write: {error}"))?;
    println!("{{\"sourcebytes\":{},\"archivebytes\":{},\"modelbytes\":21,\"payloadbytes\":{},\"timens\":{},\"stride\":{},\"transform\":{}}}", input.len(), archive.len(), archive.len() - HEADER_BYTES, elapsed_ns, stride, transform_kind);
    Ok(())
}

fn decode(archive_path: &str, output_path: &str) -> Result<(), String> {
    let output = unpack(&bounded_read(archive_path, MAX_ARCHIVE, "archive")?)?;
    fs::write(output_path, output).map_err(|error| format!("output write: {error}"))
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    match args.as_slice() {
        [command, stride_flag, stride, transform_flag, transform_kind, input, archive] if command == "encode" && stride_flag == "--stride" && transform_flag == "--transform" => encode(parse_stride(stride)?, parse_transform(transform_kind)?, input, archive),
        [command, archive, output] if command == "decode" => decode(archive, output),
        _ => Err("usage: lane_zstd_control encode --stride 1..8 --transform 0|1 INPUT ARC | lane_zstd_control decode ARC OUT".into()),
    }
}
fn main() {
    if let Err(error) = run() {
        eprintln!("lane_zstd_control: {error}");
        std::process::exit(1);
    }
}
