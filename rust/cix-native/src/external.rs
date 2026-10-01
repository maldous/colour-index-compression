//! Bounded CIXB1 reference-backend envelope codecs.
use flate2::{bufread::GzDecoder, Compression, GzBuilder};
use sha2::{Digest, Sha256};
use std::ffi::{c_char, c_int, c_uint, c_void, CStr};
use std::io::{Cursor, Read, Write};

pub const MAX_INPUT: usize = 16 * 1024 * 1024;
pub const MAX_PAYLOAD: usize = MAX_INPUT + 1024 * 1024;
const HEADER: usize = 47;

#[link(name = "bz2")]
unsafe extern "C" {
    fn BZ2_bzBuffToBuffCompress(
        dest: *mut c_char,
        dest_len: *mut c_uint,
        source: *mut c_char,
        source_len: c_uint,
        block_size_100k: c_int,
        verbosity: c_int,
        work_factor: c_int,
    ) -> c_int;
    fn BZ2_bzDecompressInit(stream: *mut BzStream, verbosity: c_int, small: c_int) -> c_int;
    fn BZ2_bzDecompress(stream: *mut BzStream) -> c_int;
    fn BZ2_bzDecompressEnd(stream: *mut BzStream) -> c_int;
}
#[repr(C)]
struct BzStream {
    next_in: *mut c_char,
    avail_in: c_uint,
    total_in_lo32: c_uint,
    total_in_hi32: c_uint,
    next_out: *mut c_char,
    avail_out: c_uint,
    total_out_lo32: c_uint,
    total_out_hi32: c_uint,
    state: *mut c_void,
    bzalloc: Option<unsafe extern "C" fn(*mut c_void, c_int, c_int) -> *mut c_void>,
    bzfree: Option<unsafe extern "C" fn(*mut c_void, *mut c_void)>,
    opaque: *mut c_void,
}

#[link(name = "lzma")]
unsafe extern "C" {
    fn lzma_stream_buffer_bound(uncompressed_size: usize) -> usize;
    fn lzma_easy_buffer_encode(
        preset: u32,
        check: u32,
        allocator: *const c_void,
        input: *const u8,
        input_size: usize,
        output: *mut u8,
        output_pos: *mut usize,
        output_size: usize,
    ) -> u32;
    fn lzma_stream_buffer_decode(
        memlimit: *mut u64,
        flags: u32,
        allocator: *const c_void,
        input: *const u8,
        input_pos: *mut usize,
        input_size: usize,
        output: *mut u8,
        output_pos: *mut usize,
        output_size: usize,
    ) -> u32;
}

#[link(name = "zstd")]
unsafe extern "C" {
    fn ZSTD_compressBound(src_size: usize) -> usize;
    fn ZSTD_compress(
        dst: *mut c_void,
        dst_capacity: usize,
        src: *const c_void,
        src_size: usize,
        level: c_int,
    ) -> usize;
    fn ZSTD_decompress(
        dst: *mut c_void,
        dst_capacity: usize,
        src: *const c_void,
        src_size: usize,
    ) -> usize;
    fn ZSTD_findFrameCompressedSize(src: *const c_void, src_size: usize) -> usize;
    fn ZSTD_isError(code: usize) -> u32;
    fn ZSTD_getErrorName(code: usize) -> *const c_char;
}

#[link(name = "brotlienc")]
unsafe extern "C" {
    fn BrotliEncoderMaxCompressedSize(input_size: usize) -> usize;
    fn BrotliEncoderCompress(
        quality: c_int,
        lgwin: c_int,
        mode: c_int,
        input_size: usize,
        input: *const u8,
        encoded_size: *mut usize,
        encoded: *mut u8,
    ) -> c_int;
}
#[link(name = "brotlidec")]
unsafe extern "C" {
    fn BrotliDecoderDecompress(
        encoded_size: usize,
        encoded: *const u8,
        decoded_size: *mut usize,
        decoded: *mut u8,
    ) -> c_int;
}

fn backend_id(name: &str) -> Result<u8, String> {
    match name {
        "gzip" => Ok(1),
        "bzip2" => Ok(2),
        "xz" => Ok(3),
        "zstd" => Ok(4),
        "brotli" => Ok(5),
        _ => Err(format!("unsupported CIXB1 backend: {name}")),
    }
}
fn profile_id(name: &str) -> Result<u8, String> {
    match name {
        "fast" => Ok(1),
        "current" => Ok(2),
        "size" => Ok(3),
        _ => Err(format!("unsupported CIXB1 profile: {name}")),
    }
}
fn check_eligible(backend: &str, profile: &str) -> Result<(), String> {
    let valid = match profile {
        "fast" => matches!(backend, "gzip" | "zstd" | "brotli"),
        "current" | "size" => matches!(backend, "gzip" | "bzip2" | "xz" | "zstd"),
        _ => false,
    };
    if valid {
        Ok(())
    } else {
        Err(format!(
            "CIXB1 backend {backend} is not eligible for profile {profile}"
        ))
    }
}
fn zstd_error(code: usize) -> String {
    unsafe {
        CStr::from_ptr(ZSTD_getErrorName(code))
            .to_string_lossy()
            .into_owned()
    }
}

pub fn encode(backend: &str, profile: &str, input: &[u8]) -> Result<Vec<u8>, String> {
    check_eligible(backend, profile)?;
    if input.len() > MAX_INPUT {
        return Err("CIXB1 input exceeds 16 MiB limit".into());
    }
    let payload = match backend {
        "gzip" => {
            let level = if profile == "fast" { 1 } else { 9 };
            let mut encoder = GzBuilder::new()
                .mtime(0)
                .write(Vec::new(), Compression::new(level));
            encoder.write_all(input).map_err(|e| e.to_string())?;
            encoder.finish().map_err(|e| e.to_string())?
        }
        "bzip2" => {
            let level = if profile == "fast" { 1 } else { 9 };
            let cap = input
                .len()
                .saturating_add(input.len() / 100)
                .saturating_add(601)
                .max(601);
            let mut out = vec![0u8; cap];
            let mut n = u32::try_from(cap).map_err(|_| "bzip2 output bound overflow")?;
            let srcn = u32::try_from(input.len()).map_err(|_| "bzip2 source too large")?;
            let rc = unsafe {
                BZ2_bzBuffToBuffCompress(
                    out.as_mut_ptr().cast(),
                    &mut n,
                    input.as_ptr().cast_mut().cast(),
                    srcn,
                    level,
                    0,
                    30,
                )
            };
            if rc != 0 {
                return Err(format!("bzip2 compressor returned {rc}"));
            }
            out.truncate(n as usize);
            out
        }
        "xz" => {
            let base = match profile {
                "fast" => 0,
                "current" => 6,
                _ => 9,
            };
            let preset = base | if profile == "size" { 1u32 << 31 } else { 0 };
            let cap = unsafe { lzma_stream_buffer_bound(input.len()) };
            let mut out = vec![0u8; cap];
            let mut pos = 0;
            let rc = unsafe {
                lzma_easy_buffer_encode(
                    preset,
                    4,
                    std::ptr::null(),
                    input.as_ptr(),
                    input.len(),
                    out.as_mut_ptr(),
                    &mut pos,
                    out.len(),
                )
            };
            if rc != 0 {
                return Err(format!("xz encoder returned {rc}"));
            }
            out.truncate(pos);
            out
        }
        "zstd" => {
            let level = match profile {
                "fast" => -131072,
                "current" => 3,
                _ => 22,
            };
            let cap = unsafe { ZSTD_compressBound(input.len()) };
            let mut out = vec![0u8; cap];
            let n = unsafe {
                ZSTD_compress(
                    out.as_mut_ptr().cast(),
                    out.len(),
                    input.as_ptr().cast(),
                    input.len(),
                    level,
                )
            };
            if unsafe { ZSTD_isError(n) } != 0 {
                return Err(format!("zstd encode: {}", zstd_error(n)));
            }
            out.truncate(n);
            out
        }
        "brotli" => {
            let cap = unsafe { BrotliEncoderMaxCompressedSize(input.len()) };
            let mut out = vec![0u8; cap];
            let mut n = cap;
            let ok = unsafe {
                BrotliEncoderCompress(
                    0,
                    22,
                    0,
                    input.len(),
                    input.as_ptr(),
                    &mut n,
                    out.as_mut_ptr(),
                )
            };
            if ok == 0 {
                return Err("brotli encoder failed".into());
            }
            out.truncate(n);
            out
        }
        _ => return Err(format!("unsupported CIXB1 backend: {backend}")),
    };
    if payload.len() > MAX_PAYLOAD {
        return Err("CIXB1 payload exceeds bounded limit".into());
    }
    let mut out = Vec::with_capacity(HEADER + payload.len());
    out.extend_from_slice(b"CIXB1");
    out.push(backend_id(backend)?);
    out.push(profile_id(profile)?);
    out.extend_from_slice(&(input.len() as u32).to_le_bytes());
    out.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    out.extend_from_slice(&Sha256::digest(input));
    out.extend_from_slice(&payload);
    Ok(out)
}

pub fn decode(archive: &[u8], memory_limit: usize) -> Result<Vec<u8>, String> {
    if archive.len() < HEADER || &archive[..5] != b"CIXB1" {
        return Err("truncated or invalid CIXB1 header".into());
    }
    let bid = archive[5];
    let profile = archive[6];
    if !(1..=5).contains(&bid) || !(1..=3).contains(&profile) {
        return Err("unsupported CIXB1 backend or profile ID".into());
    }
    let expected = u32::from_le_bytes(archive[7..11].try_into().unwrap()) as usize;
    let size = u32::from_le_bytes(archive[11..15].try_into().unwrap()) as usize;
    if expected > MAX_INPUT
        || size > MAX_PAYLOAD
        || expected.saturating_add(size).saturating_add(HEADER) > memory_limit
    {
        return Err("CIXB1 memory/resource limit exceeded".into());
    }
    if archive.len() != HEADER + size {
        return Err("CIXB1 payload length mismatch".into());
    }
    let payload = &archive[HEADER..];
    let mut output = vec![0u8; expected.saturating_add(1)];
    let written = match bid {
        1 => {
            output.clear();
            let mut decoder = GzDecoder::new(Cursor::new(payload));
            decoder
                .read_to_end(&mut output)
                .map_err(|e| format!("gzip decode: {e}"))?;
            let pos = decoder.get_ref().position() as usize;
            if pos != payload.len() {
                return Err("gzip trailing or concatenated data".into());
            }
            output.len()
        }
        2 => {
            let mut stream = BzStream {
                next_in: payload.as_ptr().cast_mut().cast(),
                avail_in: u32::try_from(payload.len()).map_err(|_| "bzip2 input too large")?,
                total_in_lo32: 0,
                total_in_hi32: 0,
                next_out: output.as_mut_ptr().cast(),
                avail_out: u32::try_from(output.len()).map_err(|_| "bzip2 output too large")?,
                total_out_lo32: 0,
                total_out_hi32: 0,
                state: std::ptr::null_mut(),
                bzalloc: None,
                bzfree: None,
                opaque: std::ptr::null_mut(),
            };
            let init = unsafe { BZ2_bzDecompressInit(&mut stream, 0, 0) };
            if init != 0 {
                return Err(format!("bzip2 init returned {init}"));
            }
            let mut rc;
            loop {
                rc = unsafe { BZ2_bzDecompress(&mut stream) };
                if rc == 4 || rc < 0 || rc == 0 && stream.avail_in == 0 || stream.avail_out == 0 {
                    break;
                }
            }
            let _ = unsafe { BZ2_bzDecompressEnd(&mut stream) };
            if rc != 4 || stream.avail_in != 0 {
                return Err("bzip2 truncated, trailing or invalid data".into());
            }
            stream.total_out_lo32 as usize | ((stream.total_out_hi32 as usize) << 32)
        }
        3 => {
            let mut inpos = 0usize;
            let mut outpos = 0usize;
            let mut memlimit = memory_limit as u64;
            let rc = unsafe {
                lzma_stream_buffer_decode(
                    &mut memlimit,
                    0,
                    std::ptr::null(),
                    payload.as_ptr(),
                    &mut inpos,
                    payload.len(),
                    output.as_mut_ptr(),
                    &mut outpos,
                    output.len(),
                )
            };
            if rc != 0 || inpos != payload.len() {
                return Err(format!("xz invalid/trailing data (status {rc})"));
            }
            outpos
        }
        4 => {
            let frame =
                unsafe { ZSTD_findFrameCompressedSize(payload.as_ptr().cast(), payload.len()) };
            if unsafe { ZSTD_isError(frame) } != 0 || frame != payload.len() {
                return Err("zstd invalid or trailing data".into());
            }
            let n = unsafe {
                ZSTD_decompress(
                    output.as_mut_ptr().cast(),
                    output.len(),
                    payload.as_ptr().cast(),
                    payload.len(),
                )
            };
            if unsafe { ZSTD_isError(n) } != 0 {
                return Err(format!("zstd decode: {}", zstd_error(n)));
            }
            n
        }
        5 => {
            let mut n = output.len();
            let rc = unsafe {
                BrotliDecoderDecompress(
                    payload.len(),
                    payload.as_ptr(),
                    &mut n,
                    output.as_mut_ptr(),
                )
            };
            if rc != 1 {
                return Err("brotli decode failed".into());
            }
            n
        }
        _ => return Err("unknown CIXB1 backend".into()),
    };
    if written != expected {
        return Err(format!(
            "CIXB1 decoded length mismatch: expected {expected}, got {written}"
        ));
    }
    output.truncate(written);
    if Sha256::digest(&output).as_slice() != &archive[15..47] {
        return Err("CIXB1 SHA-256 checksum mismatch".into());
    }
    Ok(output)
}
