//! Versioned persistent native-backend streaming.
//!
//! `CIXZ1` is deliberately separate from CIXG1/CIXG2.  A CIXG frame is an
//! independently decoded route payload, whereas this format carries pieces of
//! one zstd frame and its decoder state across blocks.  Each source block is
//! still bounded, flushed as a complete CIX frame before EOF, and protected by
//! a per-block hash.  The final zstd epilogue is stored in the CIX footer, so
//! the stream remains incrementally decodable and its complete integrity is
//! only accepted after that footer is consumed.

use super::*;
use sha2::{Digest, Sha256};
use std::ffi::{c_char, c_int, c_void, CStr};
use std::io::{Read, Write};
use std::time::{Duration, Instant};

pub(super) const MAGIC: &[u8; 5] = b"CIXZ1";
const ROUTE_ZSTD: u8 = 11;
const ROUTE_RAW: u8 = 0;
const ROUTE_ZSTD_RESET: u8 = 12;
const ROUTE_CIXG: u8 = 13;
// A zstd streaming flush can contain framing and a partly buffered block in
// addition to the 64 KiB application block.  This is an explicit allocation
// cap, not an estimate of compressed size.
const STREAM_SLACK: usize = 256 * 1024;
// After an explicit zstd flush, ending the active frame only needs its small
// frame epilogue. Reserve this fixed charge while comparing an open persistent
// frame with closed raw/CIXG candidates; the actual footer remains checked.
// With checksums disabled and every data block flushed, Zstd finishes with
// one empty last-block header (3 bytes). Enforce this native-format invariant
// when materializing tails so selection charges the exact closing cost.
const FINALIZATION_COST: usize = 3;
const FRAME_PREFIX_COST: usize = 41;
const ZSTD_MAX_WINDOW: usize = 1 << 27;

/// A decoder must never let a nested archive turn its advertised outer block
/// length into an allocation.  This writer retains at most the descriptor's
/// promised bytes and makes `write_all` fail before growing its backing Vec.
/// It is deliberately local to CIXZ1: CIXG's ordinary decoder remains a
/// general stream decoder, while this embedding has a strict outer bound.
struct CappedWriter {
    bytes: Vec<u8>,
    limit: usize,
}

impl CappedWriter {
    fn new(limit: usize) -> Self {
        Self {
            bytes: Vec::with_capacity(limit),
            limit,
        }
    }

    fn into_inner(self) -> Vec<u8> {
        self.bytes
    }
}

impl Write for CappedWriter {
    fn write(&mut self, input: &[u8]) -> std::io::Result<usize> {
        let remaining = self.limit.saturating_sub(self.bytes.len());
        if input.len() > remaining {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "nested CIXG output exceeds CIXZ1 source descriptor",
            ));
        }
        self.bytes.extend_from_slice(input);
        Ok(input.len())
    }

    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}

#[repr(C)]
struct ZstdInBuffer {
    src: *const c_void,
    size: usize,
    pos: usize,
}

#[repr(C)]
struct ZstdOutBuffer {
    dst: *mut c_void,
    size: usize,
    pos: usize,
}

enum ZstdCStream {}
enum ZstdDStream {}

#[link(name = "zstd")]
unsafe extern "C" {
    fn ZSTD_createCStream() -> *mut ZstdCStream;
    fn ZSTD_freeCStream(stream: *mut ZstdCStream) -> usize;
    fn ZSTD_initCStream(stream: *mut ZstdCStream, level: c_int) -> usize;
    fn ZSTD_CCtx_setParameter(stream: *mut ZstdCStream, parameter: c_int, value: c_int) -> usize;
    fn ZSTD_compressStream2(
        stream: *mut ZstdCStream,
        output: *mut ZstdOutBuffer,
        input: *mut ZstdInBuffer,
        directive: c_int,
    ) -> usize;
    fn ZSTD_createDStream() -> *mut ZstdDStream;
    fn ZSTD_freeDStream(stream: *mut ZstdDStream) -> usize;
    fn ZSTD_initDStream(stream: *mut ZstdDStream) -> usize;
    fn ZSTD_DCtx_setParameter(stream: *mut ZstdDStream, parameter: c_int, value: c_int) -> usize;
    fn ZSTD_decompressStream(
        stream: *mut ZstdDStream,
        output: *mut ZstdOutBuffer,
        input: *mut ZstdInBuffer,
    ) -> usize;
    fn ZSTD_isError(code: usize) -> u32;
    fn ZSTD_getErrorName(code: usize) -> *const c_char;
    fn ZSTD_estimateCStreamSize(level: c_int) -> usize;
    fn ZSTD_estimateDStreamSize(window_size: usize) -> usize;
}

fn zstd_error(code: usize) -> String {
    unsafe {
        CStr::from_ptr(ZSTD_getErrorName(code))
            .to_string_lossy()
            .into_owned()
    }
}

fn checked(code: usize, operation: &str) -> Result<usize, String> {
    if unsafe { ZSTD_isError(code) } != 0 {
        Err(format!("zstd {operation}: {}", zstd_error(code)))
    } else {
        Ok(code)
    }
}

struct Compressor(*mut ZstdCStream);
impl Compressor {
    fn new(level: c_int) -> Result<Self, String> {
        let stream = unsafe { ZSTD_createCStream() };
        if stream.is_null() {
            return Err("zstd could not allocate a streaming compressor".into());
        }
        if let Err(error) = checked(
            unsafe { ZSTD_initCStream(stream, level) },
            "stream initialization",
        ) {
            unsafe { ZSTD_freeCStream(stream) };
            return Err(error);
        }
        // ZSTD_c_checksumFlag: CIX owns frame and whole-stream SHA-256.
        if let Err(error) = checked(
            unsafe { ZSTD_CCtx_setParameter(stream, 201, 0) },
            "checksum policy",
        ) {
            unsafe { ZSTD_freeCStream(stream) };
            return Err(error);
        }
        Ok(Self(stream))
    }

    fn flush(&mut self, input: &[u8]) -> Result<Vec<u8>, String> {
        // ZSTD_e_flush.  The state remains live after every CIX frame.
        self.process(input, 1)
    }

    fn finish(&mut self) -> Result<Vec<u8>, String> {
        // ZSTD_e_end writes the frame epilogue. It belongs in the CIX footer.
        let tail = self.process(&[], 2)?;
        if tail.len() != FINALIZATION_COST {
            return Err("zstd closing bytes differ from exact selector accounting".into());
        }
        Ok(tail)
    }

    fn process(&mut self, input: &[u8], directive: c_int) -> Result<Vec<u8>, String> {
        let cap = input
            .len()
            .checked_add(STREAM_SLACK)
            .ok_or("zstd frame output capacity overflow")?;
        let mut collected = Vec::with_capacity(cap);
        let mut source = ZstdInBuffer {
            src: input.as_ptr().cast(),
            size: input.len(),
            pos: 0,
        };
        loop {
            check_interrupted()?;
            let mut chunk = [0u8; 64 * 1024];
            let mut output = ZstdOutBuffer {
                dst: chunk.as_mut_ptr().cast(),
                size: chunk.len(),
                pos: 0,
            };
            let remaining = checked(
                unsafe { ZSTD_compressStream2(self.0, &mut output, &mut source, directive) },
                "stream compression",
            )?;
            collected.extend_from_slice(&chunk[..output.pos]);
            if collected.len() > cap {
                return Err("zstd streaming frame exceeds bounded output allowance".into());
            }
            if source.pos == source.size && remaining == 0 {
                return Ok(collected);
            }
            if output.pos == 0 && source.pos == source.size && remaining != 0 {
                return Err("zstd streaming flush made no progress".into());
            }
        }
    }
}
impl Drop for Compressor {
    fn drop(&mut self) {
        unsafe { ZSTD_freeCStream(self.0) };
    }
}

struct Decompressor(*mut ZstdDStream);
impl Decompressor {
    fn new() -> Result<Self, String> {
        let stream = unsafe { ZSTD_createDStream() };
        if stream.is_null() {
            return Err("zstd could not allocate a streaming decoder".into());
        }
        // ZSTD_d_windowLogMax = 100. Refuse frames whose window would exceed
        // the 128 MiB admission used by `required_memory`.
        if let Err(error) = checked(
            unsafe { ZSTD_DCtx_setParameter(stream, 100, 27) },
            "decoder window limit",
        ) {
            unsafe { ZSTD_freeDStream(stream) };
            return Err(error);
        }
        if let Err(error) = checked(
            unsafe { ZSTD_initDStream(stream) },
            "stream decoder initialization",
        ) {
            unsafe { ZSTD_freeDStream(stream) };
            return Err(error);
        }
        Ok(Self(stream))
    }

    fn decode_block(&mut self, payload: &[u8], expected: usize) -> Result<Vec<u8>, String> {
        let mut source = ZstdInBuffer {
            src: payload.as_ptr().cast(),
            size: payload.len(),
            pos: 0,
        };
        let mut restored = vec![0u8; expected];
        let mut produced = 0usize;
        let mut stream_ended = false;
        while source.pos < source.size {
            check_interrupted()?;
            if produced == restored.len() {
                return Err("zstd frame produced more bytes than its CIX descriptor".into());
            }
            let mut output = ZstdOutBuffer {
                dst: unsafe { restored.as_mut_ptr().add(produced) }.cast(),
                size: restored.len() - produced,
                pos: 0,
            };
            let before = source.pos;
            let remaining = checked(
                unsafe { ZSTD_decompressStream(self.0, &mut output, &mut source) },
                "stream decompression",
            )?;
            stream_ended |= remaining == 0;
            produced += output.pos;
            if before == source.pos && output.pos == 0 {
                return Err("zstd decoder made no progress in a frame".into());
            }
        }
        if produced != expected {
            return Err(format!(
                "zstd frame decoded {produced} bytes but CIX descriptor requires {expected}"
            ));
        }
        if stream_ended {
            return Err("zstd stream ended before the CIXZ1 footer".into());
        }
        Ok(restored)
    }

    fn finish(&mut self, payload: &[u8]) -> Result<(), String> {
        let mut source = ZstdInBuffer {
            src: payload.as_ptr().cast(),
            size: payload.len(),
            pos: 0,
        };
        loop {
            check_interrupted()?;
            let mut scratch = [0u8; 1];
            let mut output = ZstdOutBuffer {
                dst: scratch.as_mut_ptr().cast(),
                size: scratch.len(),
                pos: 0,
            };
            let before = source.pos;
            let remaining = checked(
                unsafe { ZSTD_decompressStream(self.0, &mut output, &mut source) },
                "stream footer decompression",
            )?;
            if output.pos != 0 {
                return Err("zstd footer unexpectedly decoded source bytes".into());
            }
            if source.pos == source.size && remaining == 0 {
                return Ok(());
            }
            if before == source.pos {
                return Err("truncated zstd stream footer".into());
            }
        }
    }
}
impl Drop for Decompressor {
    fn drop(&mut self) {
        unsafe { ZSTD_freeDStream(self.0) };
    }
}

fn level_for(effort: u8) -> c_int {
    if effort >= 9 {
        22
    } else {
        3
    }
}

pub(super) fn required_memory(block: u32) -> usize {
    let native = native_memory().unwrap_or(usize::MAX);
    (block as usize)
        // Input, bounded nested CIXG archive, current zstd payload and
        // confirmation payload. Twelve blocks leaves room for CIXG's framed
        // 8*n maximum plus all live application buffers.
        .saturating_mul(12)
        .saturating_add(STREAM_SLACK.saturating_mul(2))
        // A persistent candidate is represented by two independently advanced
        // contexts. This avoids unsupported copying/snapshotting of a live
        // zstd stream while permitting current-state comparisons.
        .saturating_add(native.saturating_mul(2))
}

fn decoder_memory() -> Result<usize, String> {
    checked(
        unsafe { ZSTD_estimateDStreamSize(ZSTD_MAX_WINDOW) },
        "stream decoder memory estimate",
    )
}

fn native_memory() -> Result<usize, String> {
    let encoder = checked(
        unsafe { ZSTD_estimateCStreamSize(level_for(9)) },
        "stream memory estimate",
    )?;
    let decoder = checked(
        unsafe { ZSTD_estimateDStreamSize(ZSTD_MAX_WINDOW) },
        "stream decoder memory estimate",
    )?;
    // Encoder and decoder run in separate processes, but making the public
    // stream admission cover the larger one keeps `--memory` authoritative
    // for either operation. Application buffers are charged by the caller.
    Ok(encoder.max(decoder))
}

/// A one-block exact trial of the persistent stream, including the zstd frame
/// epilogue that would be stored in the CIX footer.  The caller compares this
/// against its incumbent's complete first-frame cost before committing the
/// input stream to a stateful backend.
pub(super) fn probe_payload(input: &[u8], level: u8) -> Result<usize, String> {
    let mut compressor = Compressor::new(level_for(level))?;
    let data = compressor.flush(input)?;
    let tail = compressor.finish()?;
    data.len()
        .checked_add(tail.len())
        .ok_or("zstd probe size overflow".into())
}

pub(super) fn read_probe<R: Read>(
    src: &mut R,
    block: u32,
    input_fd: i32,
    flush_interval: Option<Duration>,
) -> Result<(Vec<u8>, bool), String> {
    read_block(src, block as usize, input_fd, flush_interval)
}

fn native_cixg_candidate(data: &[u8], memory: usize, workers: usize) -> Result<Vec<u8>, String> {
    // This is a complete bounded CIXG2 subarchive, not an estimator. Its
    // header, frame and footer are retained inside the outer route payload so
    // a later CIXZ1 decoder has every native route decision available.
    let mut archive = Vec::new();
    super::encode_with_strategy(
        std::io::Cursor::new(data),
        &mut archive,
        u32::try_from(data.len()).map_err(|_| "CIXG nested source overflow")?,
        9,
        None,
        "hybrid",
        false,
        "cixg2",
        -1,
        None,
        memory,
        workers.max(1),
        false,
        false,
        "candidates",
    )?;
    if !matches!(archive.get(..5), Some(b"CIXG1") | Some(b"CIXG2")) {
        return Err("nested native candidate did not produce CIXG".into());
    }
    Ok(archive)
}

fn resource_omission(error: &str) -> bool {
    error == crate::limits::DEADLINE_ERROR
        || error.contains(crate::limits::DEADLINE_ERROR)
        || error.contains("memory budget")
        || error.contains("memory reservation")
        || error.contains("exceed --memory")
        || error.contains("input/profiler buffers exceed --memory")
        || error.contains("block needs about")
}

fn write_reset<W: Write>(
    dst: &mut W,
    compressors: &mut Option<(Compressor, Compressor)>,
    active_segment: &mut bool,
) -> Result<(), String> {
    let Some((_, mut compressor)) = compressors.take() else {
        return Ok(());
    };
    if !*active_segment {
        return Ok(());
    }
    let tail = compressor.finish()?;
    if tail.len() > STREAM_SLACK {
        return Err("zstd reset footer exceeds bounded allowance".into());
    }
    put_frame(
        dst,
        ROUTE_ZSTD_RESET,
        0,
        u32::try_from(tail.len()).map_err(|_| "zstd reset footer overflow")?,
        &[0u8; 32],
    )
    .map_err(ioerr)?;
    dst.write_all(&tail).map_err(ioerr)?;
    dst.flush().map_err(ioerr)?;
    *active_segment = false;
    Ok(())
}

/// Encode a selected persistent zstd CIXZ1 stream. This function does not
/// choose the route: its caller must have made a bounded probe first.
pub(super) fn encode<R: Read, W: Write>(
    mut src: R,
    mut dst: W,
    first: Vec<u8>,
    first_eof: bool,
    block: u32,
    level: u8,
    input_fd: i32,
    flush_interval: Option<Duration>,
    memory: usize,
    workers: usize,
    explain: bool,
    verbose: bool,
) -> Result<(), String> {
    if required_memory(block) > memory {
        return Err("persistent zstd stream exceeds --memory".into());
    }
    let mut compressors: Option<(Compressor, Compressor)> = None;
    let mut active_zstd_segment = false;
    dst.write_all(MAGIC).map_err(ioerr)?;
    dst.write_all(&block.to_le_bytes()).map_err(ioerr)?;
    dst.write_all(&0u32.to_le_bytes()).map_err(ioerr)?;
    let mut whole = Sha256::new();
    let mut total = 0u64;
    let mut frames = 0u64;
    let mut next = Some((first, first_eof));
    loop {
        let (data, eof) = match next.take() {
            Some(value) => value,
            None => read_block(&mut src, block as usize, input_fd, flush_interval)?,
        };
        if data.is_empty() {
            if eof {
                break;
            }
            continue;
        }
        let native_state = native_memory()?;
        // `read_block` retains its allocation at the configured block size
        // after an idle flush.  Reserve against that capacity, rather than
        // the short logical frame, before admitting a nested encoder.
        let block_reservation = block as usize;
        let native_budget = memory.checked_sub(
            native_state
                .saturating_mul(2)
                .saturating_add(block_reservation.saturating_mul(12))
                .saturating_add(STREAM_SLACK.saturating_mul(2)),
        );
        let (native, native_omission) = match native_budget {
            None => (
                None,
                Some("CIXG candidate omitted: stream reservation exhausts --memory".into()),
            ),
            Some(nested_memory) => match native_cixg_candidate(&data, nested_memory, workers) {
                Ok(candidate) => (Some(candidate), None),
                Err(error) if resource_omission(&error) => (None, Some(error)),
                Err(error) => return Err(error),
            },
        };
        // Keep two contexts in the same committed state. One materialises the
        // candidate; the other is advanced only after zstd wins. This is a
        // supported state-preservation scheme, unlike copying an active zstd
        // stream context.
        let had_active_zstd = active_zstd_segment;
        if compressors.is_none() {
            compressors = Some((
                Compressor::new(level_for(level))?,
                Compressor::new(level_for(level))?,
            ));
        }
        let zstd_payload = compressors.as_mut().unwrap().0.flush(&data)?;
        let reset_allowance = had_active_zstd
            .then_some(FRAME_PREFIX_COST.saturating_add(FINALIZATION_COST))
            .unwrap_or(0);
        let native_len = native.as_ref().map_or(usize::MAX, |payload| {
            payload.len().saturating_add(reset_allowance)
        });
        let raw_len = data.len().saturating_add(reset_allowance);
        let zstd_cost = zstd_payload.len().saturating_add(FINALIZATION_COST);
        let selected = if zstd_cost <= raw_len && zstd_cost <= native_len {
            ROUTE_ZSTD
        } else if native_len <= raw_len {
            ROUTE_CIXG
        } else {
            ROUTE_RAW
        };
        if explain {
            eprintln!(
                "cix: CIXZ1 region source={} candidates=[raw:{}B,zstd-persistent:{}B,cixg:{}] transition_allowance={}B selected={}",
                data.len(), raw_len, zstd_cost, native.as_ref().map_or_else(|| format!("omitted:{}", native_omission.as_deref().unwrap_or("unknown")), |v| format!("{}B", v.len().saturating_add(reset_allowance))), reset_allowance,
                match selected { ROUTE_ZSTD => "zstd-persistent", ROUTE_CIXG => "cixg2", _ => "raw" }
            );
        }
        if selected == ROUTE_RAW {
            write_reset(&mut dst, &mut compressors, &mut active_zstd_segment)?;
            let hash: [u8; 32] = Sha256::digest(&data).into();
            put_frame(
                &mut dst,
                ROUTE_RAW,
                u32::try_from(data.len()).map_err(|_| "raw source block overflow")?,
                u32::try_from(data.len()).map_err(|_| "raw payload block overflow")?,
                &hash,
            )
            .map_err(ioerr)?;
            dst.write_all(&data).map_err(ioerr)?;
            dst.flush().map_err(ioerr)?;
            whole.update(&data);
            total = total
                .checked_add(data.len() as u64)
                .ok_or("input length overflow")?;
            frames += 1;
            if eof {
                break;
            }
            continue;
        }
        if selected == ROUTE_CIXG {
            write_reset(&mut dst, &mut compressors, &mut active_zstd_segment)?;
            let payload = native.expect("selected native candidate is present");
            if payload.len() > data.len().saturating_mul(8).saturating_add(8192) {
                return Err("nested CIXG candidate exceeds bounded frame allowance".into());
            }
            let hash: [u8; 32] = Sha256::digest(&data).into();
            put_frame(
                &mut dst,
                ROUTE_CIXG,
                u32::try_from(data.len()).map_err(|_| "CIXG source block overflow")?,
                u32::try_from(payload.len()).map_err(|_| "CIXG payload block overflow")?,
                &hash,
            )
            .map_err(ioerr)?;
            dst.write_all(&payload).map_err(ioerr)?;
            dst.flush().map_err(ioerr)?;
            whole.update(&data);
            total = total
                .checked_add(data.len() as u64)
                .ok_or("input length overflow")?;
            frames += 1;
            if eof {
                break;
            }
            continue;
        }
        if zstd_payload.len() > data.len().saturating_add(STREAM_SLACK) {
            return Err("zstd streaming payload exceeds bounded frame allowance".into());
        }
        // The native archive lost this comparison; release it before the
        // second zstd payload is materialised for state confirmation.
        drop(native);
        let confirmation = compressors.as_mut().unwrap().1.flush(&data)?;
        if confirmation != zstd_payload {
            return Err("zstd duplicate persistent contexts diverged".into());
        }
        active_zstd_segment = true;
        let hash: [u8; 32] = Sha256::digest(&data).into();
        put_frame(
            &mut dst,
            ROUTE_ZSTD,
            u32::try_from(data.len()).map_err(|_| "zstd source block overflow")?,
            u32::try_from(zstd_payload.len()).map_err(|_| "zstd payload block overflow")?,
            &hash,
        )
        .map_err(ioerr)?;
        dst.write_all(&zstd_payload).map_err(ioerr)?;
        dst.flush().map_err(ioerr)?;
        whole.update(&data);
        total = total
            .checked_add(data.len() as u64)
            .ok_or("input length overflow")?;
        frames += 1;
        if eof {
            break;
        }
    }
    let tail = match compressors {
        Some((mut compressor, _)) if active_zstd_segment => compressor.finish()?,
        None => Vec::new(),
        Some(_) => Vec::new(),
    };
    if tail.len() > STREAM_SLACK {
        return Err("zstd stream footer exceeds bounded allowance".into());
    }
    let hash: [u8; 32] = whole.finalize().into();
    put_frame(
        &mut dst,
        END,
        0,
        u32::try_from(tail.len()).map_err(|_| "zstd footer overflow")?,
        &hash,
    )
    .map_err(ioerr)?;
    dst.write_all(&tail).map_err(ioerr)?;
    dst.flush().map_err(ioerr)?;
    if verbose {
        eprintln!(
            "cix: effort={} format=CIXZ1 backend=zstd-persistent frames={} source_bytes={} zstd_workers=1 native_candidate_workers={} memory_reservation={}",
            effort_display_name(level), frames, total, workers, required_memory(block)
        );
    }
    Ok(())
}

fn read_block<R: Read>(
    src: &mut R,
    block: usize,
    input_fd: i32,
    flush_interval: Option<Duration>,
) -> Result<(Vec<u8>, bool), String> {
    let mut bytes = vec![0u8; block];
    let mut filled = 0usize;
    let mut since: Option<Instant> = None;
    loop {
        let timeout = since.zip(flush_interval).and_then(|(start, interval)| {
            let left = interval.saturating_sub(start.elapsed());
            (left > Duration::ZERO).then_some(left)
        });
        if since
            .zip(flush_interval)
            .is_some_and(|(start, interval)| start.elapsed() >= interval)
        {
            bytes.truncate(filled);
            return Ok((bytes, false));
        }
        match read_poll(src, &mut bytes[filled..], input_fd, timeout)? {
            Some(0) => {
                bytes.truncate(filled);
                return Ok((bytes, true));
            }
            Some(n) => {
                filled += n;
                since.get_or_insert_with(Instant::now);
                if filled == block {
                    return Ok((bytes, false));
                }
            }
            None if filled != 0 => {
                bytes.truncate(filled);
                return Ok((bytes, false));
            }
            None => {}
        }
    }
}

/// Decode the remainder after `main` has already consumed the five-byte
/// CIXZ1 magic.  Data reaches `dst` frame-by-frame; an atomic file caller
/// therefore only replaces its destination after the footer is verified.
pub(super) fn decode<R: Read, W: Write>(
    mut src: R,
    mut dst: W,
    verify_only: bool,
    list: bool,
    input_fd: i32,
    memory: usize,
) -> Result<(), String> {
    let mut header = [0u8; 8];
    read_exact_poll(&mut src, &mut header, input_fd)?;
    let block = u32::from_le_bytes(header[..4].try_into().unwrap());
    let reserved = u32::from_le_bytes(header[4..].try_into().unwrap());
    if block == 0 || block > MAX_BLOCK || reserved != 0 {
        return Err("invalid CIXZ1 header".into());
    }
    if decoder_memory()?
        .saturating_add((block as usize).saturating_mul(12))
        .saturating_add(STREAM_SLACK)
        > memory
    {
        return Err("persistent zstd decoder exceeds --memory".into());
    }
    let mut decoder: Option<Decompressor> = None;
    let mut whole = Sha256::new();
    let mut total = 0u64;
    let mut frames = 0u64;
    loop {
        let mut route = [0u8; 1];
        read_exact_poll(&mut src, &mut route, input_fd)?;
        let source_len = read_u32(&mut src, input_fd)? as usize;
        let payload_len = read_u32(&mut src, input_fd)? as usize;
        let mut expected_hash = [0u8; 32];
        read_exact_poll(&mut src, &mut expected_hash, input_fd)?;
        if route[0] == END {
            if source_len != 0 || payload_len > STREAM_SLACK {
                return Err("invalid CIXZ1 footer descriptor".into());
            }
            // The encoder has a proved fixed zstd epilogue after a flushed
            // active segment.  An inactive stream has no epilogue at all.
            let expected_tail = if decoder.is_some() {
                FINALIZATION_COST
            } else {
                0
            };
            if payload_len != expected_tail {
                return Err("invalid CIXZ1 footer epilogue length".into());
            }
            let mut tail = vec![0u8; payload_len];
            read_exact_poll(&mut src, &mut tail, input_fd)?;
            match decoder.take() {
                Some(mut decoder) => decoder.finish(&tail)?,
                None if tail.is_empty() => {}
                None => {
                    return Err("CIXZ1 footer has a zstd epilogue without an active stream".into())
                }
            }
            if expected_hash != <[u8; 32]>::from(whole.finalize()) {
                return Err("CIXZ1 whole-stream checksum mismatch".into());
            }
            let mut extra = [0u8; 1];
            loop {
                match read_poll(&mut src, &mut extra, input_fd, None)? {
                    Some(0) => break,
                    Some(_) => return Err("trailing bytes after CIXZ1 footer".into()),
                    None => continue,
                }
            }
            if !verify_only {
                dst.flush().map_err(ioerr)?;
            }
            if list {
                eprintln!(
                    "CIXZ1 stream: backend=zstd-persistent frames={frames} decoded {total} bytes"
                );
            }
            return Ok(());
        }
        if route[0] == ROUTE_ZSTD_RESET {
            if source_len != 0 || payload_len != FINALIZATION_COST || expected_hash != [0u8; 32] {
                return Err("invalid CIXZ1 zstd reset frame".into());
            }
            let mut tail = vec![0u8; payload_len];
            read_exact_poll(&mut src, &mut tail, input_fd)?;
            decoder
                .take()
                .ok_or("CIXZ1 zstd reset without active stream")?
                .finish(&tail)?;
            continue;
        }
        if !matches!(route[0], ROUTE_ZSTD | ROUTE_RAW | ROUTE_CIXG)
            || source_len == 0
            || source_len > block as usize
        {
            return Err("invalid CIXZ1 frame descriptor".into());
        }
        if (route[0] == ROUTE_ZSTD && payload_len > source_len.saturating_add(STREAM_SLACK))
            || (route[0] == ROUTE_RAW && payload_len != source_len)
            || (route[0] == ROUTE_CIXG
                // Nested CIXG can itself use its 8*n+4096 payload allowance,
                // plus its 13-byte header and two 41-byte frame prefixes.
                && payload_len > source_len.saturating_mul(8).saturating_add(8192))
        {
            return Err("CIXZ1 payload exceeds bounded frame allowance".into());
        }
        let frame_live = source_len
            .checked_add(payload_len)
            .and_then(|n| n.checked_add(decoder_memory().unwrap_or(usize::MAX)))
            .ok_or("CIXZ1 frame memory overflow")?;
        if frame_live > memory {
            return Err("CIXZ1 frame exceeds --memory".into());
        }
        let mut payload = vec![0u8; payload_len];
        read_exact_poll(&mut src, &mut payload, input_fd)?;
        let restored = if route[0] == ROUTE_RAW {
            if decoder.is_some() {
                return Err("CIXZ1 raw frame requires an explicit zstd reset boundary".into());
            }
            payload
        } else if route[0] == ROUTE_CIXG {
            if decoder.is_some() {
                return Err("CIXZ1 CIXG frame requires an explicit zstd reset boundary".into());
            }
            if !matches!(payload.get(..5), Some(b"CIXG1") | Some(b"CIXG2")) {
                return Err("CIXZ1 nested frame is not a CIXG1/CIXG2 archive".into());
            }
            let nested_memory = memory
                .checked_sub(payload_len)
                .and_then(|remaining| remaining.checked_sub(source_len))
                .ok_or("CIXZ1 nested CIXG exceeds --memory")?;
            let mut nested = CappedWriter::new(source_len);
            super::decode(
                std::io::Cursor::new(payload),
                &mut nested,
                false,
                false,
                -1,
                nested_memory,
            )?;
            let nested = nested.into_inner();
            if nested.len() != source_len {
                return Err("CIXZ1 nested CIXG decoded length mismatch".into());
            }
            nested
        } else {
            let active = decoder.get_or_insert(Decompressor::new()?);
            active.decode_block(&payload, source_len)?
        };
        if <[u8; 32]>::from(Sha256::digest(&restored)) != expected_hash {
            return Err("CIXZ1 block checksum mismatch".into());
        }
        whole.update(&restored);
        total = total
            .checked_add(restored.len() as u64)
            .ok_or("decoded length overflow")?;
        frames += 1;
        if list {
            eprintln!(
                "CIXZ1 block: route={} source={} bytes payload={} bytes",
                match route[0] {
                    ROUTE_ZSTD => "zstd-persistent",
                    ROUTE_CIXG => "cixg2",
                    _ => "raw",
                },
                source_len,
                payload_len
            );
        }
        if !verify_only {
            dst.write_all(&restored).map_err(ioerr)?;
            dst.flush().map_err(ioerr)?;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    fn decode_archive(archive: Vec<u8>, memory: usize) -> Result<Vec<u8>, String> {
        let mut restored = Vec::new();
        // Production `super::decode` consumes the magic before dispatching
        // here. Unit tests call this module directly, so mirror that boundary.
        decode(
            Cursor::new(archive[5..].to_vec()),
            &mut restored,
            false,
            false,
            -1,
            memory,
        )?;
        Ok(restored)
    }

    fn round_trip(data: Vec<u8>) {
        let block = 64 * 1024;
        let memory = required_memory(block).saturating_add(4 * 1024 * 1024);
        let mut archive = Vec::new();
        let split = data.len().min(block as usize);
        let first = data[..split].to_vec();
        let rest = data[split..].to_vec();
        encode(
            Cursor::new(rest),
            &mut archive,
            first,
            split == data.len(),
            block,
            9,
            -1,
            None,
            memory,
            1,
            false,
            false,
        )
        .unwrap();
        assert_eq!(&archive[..5], MAGIC);
        let restored = decode_archive(archive, memory).unwrap();
        assert_eq!(restored, data);
    }

    #[test]
    fn persistent_backend_round_trips_strong_weak_and_mixed_regions() {
        let mut mixed = b"repeated text channel ".repeat(8192);
        mixed.extend((0..(64 * 1024)).map(|n| (n as u8).wrapping_mul(73)));
        mixed.extend(b"repeated text channel ".repeat(8192));
        round_trip(mixed);
        round_trip(Vec::new());
    }

    #[test]
    fn persistent_backend_rejects_corrupt_frame() {
        let input = b"corrupt persistent zstd CIX frame".repeat(1024);
        let block = 64 * 1024;
        let memory = required_memory(block).saturating_add(4 * 1024 * 1024);
        let mut archive = Vec::new();
        encode(
            Cursor::new(Vec::<u8>::new()),
            &mut archive,
            input,
            true,
            block,
            9,
            -1,
            None,
            memory,
            1,
            false,
            false,
        )
        .unwrap();
        // Header then first CIX frame header.  Mutate payload only when the
        // selected first route is zstd; otherwise corrupt its hash field.
        let first = 13usize;
        let source = u32::from_le_bytes(archive[first + 1..first + 5].try_into().unwrap()) as usize;
        let payload =
            u32::from_le_bytes(archive[first + 5..first + 9].try_into().unwrap()) as usize;
        let payload_start = first + 41;
        assert!(source != 0 && payload != 0);
        archive[payload_start] ^= 0x80;
        assert!(decode_archive(archive, memory).is_err());
    }

    #[test]
    fn nested_cixg_frame_is_bounded_and_round_trips() {
        let input = b"nested CIXG selection fixture ".repeat(2048);
        let block = 64 * 1024;
        let memory = required_memory(block).saturating_add(8 * 1024 * 1024);
        let payload = native_cixg_candidate(&input, memory / 2, 1).unwrap();
        assert!(matches!(payload.get(..5), Some(b"CIXG1") | Some(b"CIXG2")));
        let mut archive = Vec::new();
        archive.extend_from_slice(MAGIC);
        archive.extend_from_slice(&block.to_le_bytes());
        archive.extend_from_slice(&0u32.to_le_bytes());
        let frame_hash: [u8; 32] = Sha256::digest(&input).into();
        put_frame(
            &mut archive,
            ROUTE_CIXG,
            input.len() as u32,
            payload.len() as u32,
            &frame_hash,
        )
        .unwrap();
        archive.extend_from_slice(&payload);
        let whole_hash: [u8; 32] = Sha256::digest(&input).into();
        put_frame(&mut archive, END, 0, 0, &whole_hash).unwrap();
        let restored = decode_archive(archive, memory).unwrap();
        assert_eq!(restored, input);
    }

    #[test]
    fn fresh_raw_segment_has_no_invalid_zstd_reset() {
        let mut input = vec![0u8; 64 * 1024];
        let mut state = 0x6d2b_79f5u32;
        for byte in &mut input {
            state = state.wrapping_mul(1664525).wrapping_add(1013904223);
            *byte = (state >> 24) as u8;
        }
        let block = 64 * 1024;
        let memory = required_memory(block).saturating_add(8 * 1024 * 1024);
        let mut archive = Vec::new();
        encode(
            Cursor::new(Vec::<u8>::new()),
            &mut archive,
            input.clone(),
            true,
            block,
            9,
            -1,
            None,
            memory,
            1,
            false,
            false,
        )
        .unwrap();
        assert_eq!(archive[13], ROUTE_RAW);
        let restored = decode_archive(archive, memory).unwrap();
        assert_eq!(restored, input);
    }
    #[test]
    fn nested_archive_cannot_expand_past_outer_length() {
        let input = b"bounded inner output".repeat(32);
        let memory = required_memory(1024).saturating_add(8 * 1024 * 1024);
        let payload = native_cixg_candidate(&input, memory, 1).unwrap();
        assert!(payload.len() < 8192);
        let mut archive = Vec::new();
        archive.extend_from_slice(MAGIC);
        archive.extend_from_slice(&1024u32.to_le_bytes());
        archive.extend_from_slice(&0u32.to_le_bytes());
        put_frame(&mut archive, ROUTE_CIXG, 1, payload.len() as u32, &[0; 32]).unwrap();
        archive.extend_from_slice(&payload);
        let error = decode_archive(archive, memory).unwrap_err();
        assert!(error.contains("exceeds CIXZ1 source descriptor"), "{error}");
    }

    #[test]
    fn inactive_footer_rejects_unaccounted_zstd_tail() {
        let mut archive = Vec::new();
        archive.extend_from_slice(MAGIC);
        archive.extend_from_slice(&1024u32.to_le_bytes());
        archive.extend_from_slice(&0u32.to_le_bytes());
        put_frame(&mut archive, END, 0, 3, &Sha256::digest([]).into()).unwrap();
        archive.extend_from_slice(&[1, 0, 0]);
        let error = decode_archive(archive, required_memory(1024)).unwrap_err();
        assert!(error.contains("footer"), "{error}");
    }
}
