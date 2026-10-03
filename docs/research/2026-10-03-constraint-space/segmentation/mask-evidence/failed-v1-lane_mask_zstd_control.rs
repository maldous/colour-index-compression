//! Native libzstd 1.5.5 level-19 control for the fixed NCSL v2 lane mask.
//! This is a standalone strong control, never a production archive path.
use std::{
    env,
    ffi::{c_int, c_uint, c_void},
    fs::{self, File},
    io::Read,
    time::Instant,
};

const MAGIC: &[u8; 4] = b"ZSC1";
const V1: u8 = 1;
const V2: u8 = 2;
const HEADER: usize = 21;
const MAX_N: usize = 4096;
const MAX_A: usize = 32768;

// Destinations use ZSTD_compressBound.  Decompression is bounded to the
// independently header-declared source length after the sole frame is checked.
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
        compressed_size: usize,
    ) -> usize;
    fn ZSTD_isError(code: usize) -> c_uint;
    fn ZSTD_findFrameCompressedSize(src: *const c_void, src_size: usize) -> usize;
}
fn crc(d: &[u8]) -> u32 {
    let mut c = !0u32;
    for &b in d {
        c ^= b as u32;
        for _ in 0..8 {
            c = if c & 1 != 0 {
                (c >> 1) ^ 0xedb8_8320
            } else {
                c >> 1
            };
        }
    }
    !c
}
fn read(path: &str, cap: usize, label: &str) -> Result<Vec<u8>, String> {
    let m = fs::metadata(path).map_err(|e| format!("{label} metadata: {e}"))?;
    if !m.is_file() || m.len() > cap as u64 {
        return Err(format!("{label} exceeds bound"));
    }
    let f = File::open(path).map_err(|e| format!("{label} open: {e}"))?;
    let mut d = Vec::new();
    f.take((cap + 1) as u64)
        .read_to_end(&mut d)
        .map_err(|e| format!("{label} read: {e}"))?;
    if d.len() > cap {
        Err(format!("{label} exceeds bound"))
    } else {
        Ok(d)
    }
}
fn zenc(x: &[u8]) -> Result<Vec<u8>, String> {
    let cap = unsafe { ZSTD_compressBound(x.len()) };
    if unsafe { ZSTD_isError(cap) } != 0 || cap > MAX_A - HEADER {
        return Err("zstd compression bound".into());
    }
    let mut out = vec![0u8; cap];
    let n = unsafe {
        ZSTD_compress(
            out.as_mut_ptr().cast(),
            out.len(),
            x.as_ptr().cast(),
            x.len(),
            19,
        )
    };
    if unsafe { ZSTD_isError(n) } != 0 || n > out.len() {
        return Err("zstd compression".into());
    }
    out.truncate(n);
    Ok(out)
}
fn zdec(frame: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let frame_size = unsafe { ZSTD_findFrameCompressedSize(frame.as_ptr().cast(), frame.len()) };
    if unsafe { ZSTD_isError(frame_size) } != 0 || frame_size != frame.len() {
        return Err("ZSC1 requires exactly one frame".into());
    }
    let mut out = vec![0u8; n];
    let got = unsafe {
        ZSTD_decompress(
            out.as_mut_ptr().cast(),
            out.len(),
            frame.as_ptr().cast(),
            frame.len(),
        )
    };
    if unsafe { ZSTD_isError(got) } != 0 || got != n {
        Err("zstd decoded length".into())
    } else {
        Ok(out)
    }
}
fn validate(n: usize, stride: usize, mask: u8, count: usize) -> Result<(), String> {
    if !(1..=8).contains(&stride) || mask & 1 != 0 || (mask as usize >> stride) != 0 {
        return Err("invalid ZSC1 mask".into());
    }
    if n == 0 {
        if stride != 1 || mask != 0 || count != 0 {
            return Err("noncanonical empty ZSC1".into());
        }
    } else if stride > n || count != stride {
        return Err("invalid ZSC1 lane count".into());
    }
    Ok(())
}
fn v1_mask(field: u8, stride: usize) -> Result<u8, String> {
    if field > 1 || (field == 1 && stride == 1) {
        Err("invalid v1 transform".into())
    } else if field == 0 {
        Ok(0)
    } else {
        Ok(((1u16 << stride) - 2) as u8)
    }
}
fn columns(input: &[u8], stride: usize, mask: u8) -> Vec<u8> {
    let mut out = Vec::with_capacity(input.len());
    for k in 0..stride {
        for i in (k..input.len()).step_by(stride) {
            out.push(if mask & (1 << k) != 0 {
                input[i].wrapping_sub(input[i - 1])
            } else {
                input[i]
            });
        }
    }
    out
}
fn inverse(x: &[u8], n: usize, stride: usize, mask: u8) -> Result<Vec<u8>, String> {
    if x.len() != n {
        return Err("transposed length".into());
    }
    let mut out = vec![0u8; n];
    let mut p = 0;
    for k in 0..stride {
        let z = (n - k).div_ceil(stride);
        let e = p.checked_add(z).ok_or("lane offset")?;
        for (row, &b) in x
            .get(p..e)
            .ok_or("truncated lane stream")?
            .iter()
            .enumerate()
        {
            let i = row * stride + k;
            out[i] = if mask & (1 << k) != 0 {
                b.wrapping_add(out[i - 1])
            } else {
                b
            };
        }
        p = e;
    }
    if p != x.len() {
        Err("trailing lane stream".into())
    } else {
        Ok(out)
    }
}
fn pack(input: &[u8], stride: usize, mask: u8) -> Result<Vec<u8>, String> {
    let count = if input.is_empty() { 0 } else { stride };
    validate(input.len(), stride, mask, count)?;
    let payload = zenc(&columns(input, stride, mask))?;
    let total = HEADER
        .checked_add(payload.len())
        .ok_or("archive overflow")?;
    if total > MAX_A || payload.len() > u32::MAX as usize {
        return Err("archive exceeds bound".into());
    }
    let mut a = Vec::with_capacity(total);
    a.extend_from_slice(MAGIC);
    a.push(V2);
    a.extend_from_slice(&(input.len() as u32).to_le_bytes());
    a.extend_from_slice(&crc(input).to_le_bytes());
    a.push(stride as u8);
    a.push(mask);
    a.extend_from_slice(&(count as u16).to_le_bytes());
    a.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    a.extend_from_slice(&payload);
    Ok(a)
}
fn u32at(a: &[u8], p: &mut usize) -> Result<usize, String> {
    let e = p.checked_add(4).ok_or("u32 offset")?;
    let x = a.get(*p..e).ok_or("truncated u32")?;
    *p = e;
    Ok(u32::from_le_bytes(x.try_into().map_err(|_| "invalid u32")?) as usize)
}
fn unpack(a: &[u8]) -> Result<Vec<u8>, String> {
    if a.len() < HEADER || a.len() > MAX_A || a.get(..4) != Some(MAGIC) {
        return Err("invalid ZSC1 header".into());
    }
    let v = a[4];
    let mut p = 5;
    let n = u32at(a, &mut p)?;
    let c = u32at(a, &mut p)? as u32;
    let stride = *a.get(p).ok_or("truncated stride")? as usize;
    p += 1;
    let field = *a.get(p).ok_or("truncated mask")?;
    p += 1;
    let ce = p.checked_add(2).ok_or("lane count offset")?;
    let count = u16::from_le_bytes(
        a.get(p..ce)
            .ok_or("truncated lane count")?
            .try_into()
            .map_err(|_| "invalid lane count")?,
    ) as usize;
    p = ce;
    let plen = u32at(a, &mut p)?;
    if n > MAX_N || !(1..=8).contains(&stride) {
        return Err("ZSC1 source bound".into());
    }
    let mask = match v {
        V1 => v1_mask(field, stride)?,
        V2 => field,
        _ => return Err("invalid ZSC1 version".into()),
    };
    validate(n, stride, mask, count)?;
    let e = p.checked_add(plen).ok_or("payload offset")?;
    let frame = a.get(p..e).ok_or("truncated frame")?;
    if e != a.len() {
        return Err("trailing ZSC1 bytes".into());
    }
    let out = inverse(&zdec(frame, n)?, n, stride, mask)?;
    if crc(&out) != c {
        Err("ZSC1 source CRC".into())
    } else {
        Ok(out)
    }
}
fn stride(s: &str) -> Result<usize, String> {
    match s.parse() {
        Ok(x @ 1..=8) => Ok(x),
        _ => Err("stride must be 1 through 8".into()),
    }
}
fn mask(s: &str) -> Result<u8, String> {
    s.parse::<u8>()
        .map_err(|_| "mask must be unsigned 0 through 255".into())
}
fn encode(s: usize, m: u8, input_path: &str, archive_path: &str) -> Result<(), String> {
    let input = read(input_path, MAX_N, "input")?;
    validate(input.len(), s, m, if input.is_empty() { 0 } else { s })?;
    let start = Instant::now();
    let a = pack(&input, s, m)?;
    if unpack(&a)? != input {
        return Err("in-process restoration mismatch".into());
    }
    let ns = start.elapsed().as_nanos();
    fs::write(archive_path, &a).map_err(|e| format!("archive write: {e}"))?;
    println!("{{\"source_bytes\":{},\"archive_bytes\":{},\"model_bytes\":21,\"payload_bytes\":{},\"time_ns\":{},\"stride\":{},\"mask\":{}}}", input.len(), a.len(), a.len() - HEADER, ns, s, m);
    Ok(())
}
fn decode(archive_path: &str, output_path: &str) -> Result<(), String> {
    let out = unpack(&read(archive_path, MAX_A, "archive")?)?;
    fs::write(output_path, out).map_err(|e| format!("output write: {e}"))
}
fn run() -> Result<(), String> {
    let a: Vec<String> = env::args().skip(1).collect();
    match a.as_slice() { [op, sf, s, mf, m, input, archive] if op == "encode" && sf == "--stride" && mf == "--mask" => encode(stride(s)?, mask(m)?, input, archive), [op, archive, output] if op == "decode" => decode(archive, output), _ => Err("usage: lane_mask_zstd_control encode --stride 1..8 --mask 0..255 INPUT ARC | lane_mask_zstd_control decode ARC OUT".into()) }
}
fn main() {
    if let Err(e) = run() {
        eprintln!("lane_mask_zstd_control: {e}");
        std::process::exit(1);
    }
}
