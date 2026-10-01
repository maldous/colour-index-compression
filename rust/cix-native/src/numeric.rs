//! Decoder for the frozen CIX numeric word transforms (CIXM6 mode 8).
use crate::rank;

fn bits(data: &[u8], pos: &mut usize, width: usize) -> Result<u64, String> {
    if width > 64 || pos.saturating_add(width) > data.len() * 8 {
        return Err("truncated numeric bitpack".into());
    }
    let mut v = 0u64;
    for _ in 0..width {
        v = (v << 1) | ((data[*pos / 8] >> (7 - *pos % 8)) & 1) as u64;
        *pos += 1;
    }
    Ok(v)
}
fn read_word(data: &[u8], pos: &mut usize, width: usize, big: bool) -> Result<u64, String> {
    let end = pos.checked_add(width).ok_or("numeric word overflow")?;
    let b = data.get(*pos..end).ok_or("truncated numeric word")?;
    *pos = end;
    let mut v = 0u64;
    if big {
        for x in b {
            v = (v << 8) | *x as u64;
        }
    } else {
        for (i, x) in b.iter().enumerate() {
            v |= (*x as u64) << (8 * i);
        }
    }
    Ok(v)
}
fn push_word(out: &mut Vec<u8>, v: u64, width: usize, big: bool) {
    if big {
        for i in (0..width).rev() {
            out.push((v >> (8 * i)) as u8);
        }
    } else {
        for i in 0..width {
            out.push((v >> (8 * i)) as u8);
        }
    }
}
fn unzig(v: u64) -> i128 {
    if v & 1 == 0 {
        (v / 2) as i128
    } else {
        -((v / 2) as i128) - 1
    }
}
fn decode_uints(blob: &[u8], count: usize) -> Result<Vec<usize>, String> {
    if count == 0 {
        return Ok(Vec::new());
    }
    let mode = *blob.first().ok_or("empty numeric exception stream")?;
    let mut p = 1;
    match mode {
        0 => {
            let mut out = Vec::with_capacity(count);
            for _ in 0..count {
                out.push(super::unvar(blob, &mut p)?);
            }
            if p != blob.len() {
                return Err("trailing numeric exception varints".into());
            }
            Ok(out)
        }
        1 => {
            let k = *blob.get(p).ok_or("missing Rice parameter")? as usize;
            p += 1;
            let mut bp = 0;
            let mut out = Vec::with_capacity(count);
            for _ in 0..count {
                let mut q = 0usize;
                while bits(&blob[p..], &mut bp, 1)? != 0 {
                    q = q.checked_add(1).ok_or("Rice overflow")?;
                }
                let low = bits(&blob[p..], &mut bp, k)? as usize;
                out.push(q.checked_shl(k as u32).ok_or("Rice overflow")? | low);
            }
            Ok(out)
        }
        _ => super::m6_decode_uints(blob, count, 1 << 16),
    }
}
pub fn decode(data: &[u8], n: usize) -> Result<Vec<u8>, String> {
    if data.len() < 4 || data[0] != 1 {
        return Err("unknown numeric block version".into());
    }
    let method = data[1];
    let code = data[2];
    let width = match code >> 1 {
        0 => 2,
        1 => 4,
        2 => 8,
        _ => return Err("invalid numeric word width".into()),
    };
    let big = code & 1 != 0;
    let mut p = 3;
    match method {
        1 => {
            let b = *data.get(p).ok_or("missing FOR bit width")? as usize;
            p += 1;
            let base = read_word(data, &mut p, width, big)?;
            let count = n / width;
            let tail = n % width;
            let packed = (count.checked_mul(b).ok_or("FOR bit count overflow")? + 7) / 8;
            let end = p.checked_add(packed).ok_or("FOR length overflow")?;
            if end + tail != data.len() {
                return Err("numeric FOR payload length mismatch".into());
            }
            let mut bp = 0;
            let mut out = Vec::with_capacity(n);
            for _ in 0..count {
                let value = base
                    .checked_add(bits(&data[p..end], &mut bp, b)?)
                    .ok_or("FOR value overflow")?;
                push_word(&mut out, value, width, big);
            }
            out.extend_from_slice(&data[end..]);
            Ok(out)
        }
        2 | 3 => {
            let b = *data.get(p).ok_or("missing delta bit width")? as usize;
            p += 1;
            let first = read_word(data, &mut p, width, big)?;
            let count = n / width;
            let tail = n % width;
            let bits_count = if method == 2 {
                count
                    .saturating_sub(1)
                    .checked_mul(b)
                    .ok_or("delta bit count overflow")?
            } else {
                count
                    .saturating_sub(2)
                    .checked_mul(b)
                    .ok_or("delta2 bit count overflow")?
            };
            let packed = (bits_count + 7) / 8;
            let first_delta = if method == 3 {
                Some(super::unvar(data, &mut p)? as u64)
            } else {
                None
            };
            let end = p.checked_add(packed).ok_or("delta payload overflow")?;
            if end + tail != data.len() {
                return Err("numeric delta payload length mismatch".into());
            }
            let mut bp = 0;
            let modulus = 1i128 << (width * 8);
            let mut vals = Vec::with_capacity(count);
            vals.push(first);
            let mut prev_delta = first_delta.map(unzig).unwrap_or(0);
            if method == 2 {
                for _ in 1..count {
                    let d = unzig(bits(&data[p..end], &mut bp, b)?);
                    let prev = *vals.last().unwrap() as i128;
                    vals.push((prev + d).rem_euclid(modulus) as u64);
                }
            } else if count >= 2 {
                vals.push((first as i128 + prev_delta).rem_euclid(modulus) as u64);
                for _ in 2..count {
                    let dd = unzig(bits(&data[p..end], &mut bp, b)?);
                    prev_delta = (prev_delta + dd).rem_euclid(modulus);
                    let prev = *vals.last().unwrap() as i128;
                    vals.push((prev + prev_delta).rem_euclid(modulus) as u64);
                }
            }
            let mut out = Vec::with_capacity(n);
            for v in vals {
                push_word(&mut out, v, width, big);
            }
            out.extend_from_slice(&data[end..]);
            Ok(out)
        }
        4 => {
            let low_width = *data.get(p).ok_or("missing PFOR width")? as usize;
            p += 1;
            let base = read_word(data, &mut p, width, big)?;
            let k = super::unvar(data, &mut p)?;
            let indices = rank::decode_colex_positions(data, &mut p, n / width, k)?;
            let hl = super::unvar(data, &mut p)?;
            let end = p.checked_add(hl).ok_or("PFOR exception length overflow")?;
            if end > data.len() {
                return Err("truncated PFOR exceptions".into());
            }
            let highs = decode_uints(&data[p..end], k)?;
            p = end;
            let count = n / width;
            let tail = n % width;
            let packed = (count
                .checked_mul(low_width)
                .ok_or("PFOR bit count overflow")?
                + 7)
                / 8;
            if p + packed + tail != data.len() {
                return Err("numeric PFOR payload length mismatch".into());
            }
            let mut bp = 0;
            let mut ex = 0;
            let mut out = Vec::with_capacity(n);
            for i in 0..count {
                let lo = bits(&data[p..p + packed], &mut bp, low_width)?;
                let hi = if ex < indices.len() && indices[ex] == i {
                    let v = highs[ex] as u64;
                    ex += 1;
                    v.checked_shl(low_width as u32).ok_or("PFOR overflow")?
                } else {
                    0
                };
                let value = base.checked_add(hi | lo).ok_or("PFOR value overflow")?;
                push_word(&mut out, value, width, big);
            }
            out.extend_from_slice(&data[p + packed..]);
            Ok(out)
        }
        _ => Err(format!("unsupported numeric transform mode {method}")),
    }
}
