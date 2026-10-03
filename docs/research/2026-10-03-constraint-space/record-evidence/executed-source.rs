//! Isolated exact intersection experiment; no production integration.
use num_bigint::BigUint;
use num_traits::{One, Zero};
use std::{env, fs, io::Read};
const MAX_N: usize = 16384;
const HEADER: usize = 20;
#[derive(Clone, Copy, Debug, PartialEq)]
enum Mode {
    Raw = 0,
    E = 1,
    C = 2,
    EC = 3,
}
fn fail(s: &str) -> String {
    s.into()
}
fn bounded(path: &str, cap: usize) -> Result<Vec<u8>, String> {
    let f = fs::File::open(path).map_err(|e| e.to_string())?;
    let mut d = Vec::new();
    f.take((cap + 1) as u64)
        .read_to_end(&mut d)
        .map_err(|e| e.to_string())?;
    if d.len() > cap {
        return Err(fail("input exceeds experimental bound"));
    }
    Ok(d)
}
fn width(a: &BigUint) -> usize {
    if a.is_zero() {
        0
    } else {
        (a - BigUint::one()).bits() as usize
    }
}
fn crc(d: &[u8]) -> u32 {
    let mut c = !0u32;
    for &b in d {
        c ^= b as u32;
        for _ in 0..8 {
            c = if c & 1 != 0 {
                (c >> 1) ^ 0xedb88320
            } else {
                c >> 1
            };
        }
    }
    !c
}
fn integer(r: &BigUint, w: usize) -> Result<Vec<u8>, String> {
    if r.bits() > w as u64 {
        return Err(fail("integer width"));
    }
    let b = r.to_bytes_be();
    let len = w.div_ceil(8);
    if len == 0 {
        if !r.is_zero() {
            return Err(fail("nonzero empty rank"));
        }
        return Ok(vec![]);
    }
    if b.len() > len {
        return Err(fail("integer allocation"));
    }
    let mut d = vec![0; len];
    d[len - b.len()..].copy_from_slice(&b);
    Ok(d)
}
fn read_integer(d: &[u8], w: usize) -> Result<BigUint, String> {
    if d.len() != w.div_ceil(8) {
        return Err(fail("rank width"));
    }
    let r = BigUint::from_bytes_be(d);
    if r.bits() > w as u64 {
        return Err(fail("rank padding"));
    }
    Ok(r)
}
fn alphabet(d: &[u8]) -> Option<[u8; 2]> {
    let mut seen = [false; 256];
    for &b in d {
        seen[b as usize] = true;
    }
    let v: Vec<u8> = seen
        .iter()
        .enumerate()
        .filter_map(|(i, &s)| s.then_some(i as u8))
        .collect();
    if v.len() == 2 {
        Some([v[0], v[1]])
    } else {
        None
    }
}
fn local_table(b: usize, mask: u16, h: usize, m: Mode) -> Vec<u16> {
    (0..(1usize << b))
        .filter(|&x| {
            let equality = (0..b - 1).all(|j| {
                mask & (1 << j) == 0 || ((x >> (b - 1 - j)) & 1) == ((x >> (b - 2 - j)) & 1)
            });
            let counts = x.count_ones() as usize == h;
            (m == Mode::C || equality) && (m == Mode::E || counts)
        })
        .map(|x| x as u16)
        .collect()
}
fn observed(d: &[u8], sy: [u8; 2], b: usize) -> (u16, Option<usize>) {
    let mut mask = (1u16 << (b - 1)) - 1;
    let mut count = None;
    let mut same = true;
    for chunk in d.chunks_exact(b) {
        for j in 0..b - 1 {
            if chunk[j] != chunk[j + 1] {
                mask &= !(1 << j);
            }
        }
        let h = chunk.iter().filter(|&&v| v == sy[1]).count();
        match count {
            None => count = Some(h),
            Some(k) if k != h => same = false,
            _ => {}
        }
    }
    (mask, if same { count } else { None })
}
fn local_value(d: &[u8], sy: [u8; 2]) -> u16 {
    d.iter().fold(0, |x, &b| (x << 1) | u16::from(b == sy[1]))
}
fn record_build(d: &[u8], m: Mode, b: usize, mask: u16, h: usize) -> Result<Vec<u8>, String> {
    if d.len() > MAX_N {
        return Err(fail("source bound"));
    }
    let n = d.len();
    let mut sy = [0, 0];
    let mut w = n * 8;
    let body;
    if m == Mode::Raw {
        body = d.to_vec();
    } else {
        sy = alphabet(d)
            .ok_or_else(|| fail("structural candidate requires two observed symbols"))?;
        if b < 2 || b > 12 || n == 0 || n % b != 0 || mask >> (b - 1) != 0 || h > b {
            return Err(fail("record metadata"));
        }
        if m == Mode::E && h != 0 || m == Mode::C && mask != 0 {
            return Err(fail("inapplicable metadata"));
        }
        let table = local_table(b, mask, h, m);
        if table.is_empty() {
            return Err(fail("contradictory local constraints"));
        }
        let base = table.len();
        let mut r = BigUint::zero();
        let mut cardinal = BigUint::one();
        for chunk in d.chunks_exact(b) {
            let value = local_value(chunk, sy);
            let idx = table
                .binary_search(&value)
                .map_err(|_| fail("source outside local space"))?;
            r = r * base + idx;
            cardinal *= base;
        }
        w = width(&cardinal);
        body = integer(&r, w)?;
    }
    let mut out = b"ERC1".to_vec();
    out.extend([1, m as u8]);
    out.extend((n as u32).to_le_bytes());
    out.push(if m == Mode::Raw { 0 } else { b as u8 });
    out.extend((if m == Mode::Raw { 0 } else { mask }).to_le_bytes());
    out.push(if m == Mode::Raw { 0 } else { h as u8 });
    out.extend(sy);
    out.extend((w as u32).to_le_bytes());
    assert_eq!(out.len(), HEADER);
    out.extend(body);
    out.extend(crc(&out).to_le_bytes());
    Ok(out)
}
fn u32at(d: &[u8], i: usize) -> usize {
    u32::from_le_bytes(d[i..i + 4].try_into().unwrap()) as usize
}
fn record_decode(d: &[u8]) -> Result<Vec<u8>, String> {
    if d.len() < HEADER + 4 || d.len() > HEADER + MAX_N + 4 || &d[..4] != b"ERC1" {
        return Err(fail("ERC1 envelope"));
    }
    let end = d.len() - 4;
    if crc(&d[..end]) != u32at(d, end) as u32 {
        return Err(fail("CRC"));
    }
    if d[4] != 1 {
        return Err(fail("version"));
    }
    let m = match d[5] {
        0 => Mode::Raw,
        1 => Mode::E,
        2 => Mode::C,
        3 => Mode::EC,
        _ => return Err(fail("mode")),
    };
    let n = u32at(d, 6);
    let b = d[10] as usize;
    let mask = u16::from_le_bytes(d[11..13].try_into().unwrap());
    let h = d[13] as usize;
    let sy = [d[14], d[15]];
    let w = u32at(d, 16);
    let body = &d[HEADER..end];
    if n > MAX_N || w > MAX_N * 8 {
        return Err(fail("resource bound"));
    }
    if m == Mode::Raw {
        if b != 0 || mask != 0 || h != 0 || sy != [0, 0] || w != n * 8 || body.len() != n {
            return Err(fail("raw metadata"));
        }
        return Ok(body.to_vec());
    }
    if b < 2
        || b > 12
        || n == 0
        || n % b != 0
        || mask >> (b - 1) != 0
        || h > b
        || sy[0] >= sy[1]
        || (m == Mode::E && h != 0)
        || (m == Mode::C && mask != 0)
    {
        return Err(fail("record metadata"));
    }
    let table = local_table(b, mask, h, m);
    if table.is_empty() {
        return Err(fail("empty local space"));
    }
    let base = table.len();
    let blocks = n / b;
    let mut cardinal = BigUint::one();
    for _ in 0..blocks {
        cardinal *= base;
    }
    if w != width(&cardinal) {
        return Err(fail("noncanonical width"));
    }
    let mut rank = read_integer(body, w)?;
    if rank >= cardinal {
        return Err(fail("rank range"));
    }
    let mut out = vec![0u8; n];
    for k in (0..blocks).rev() {
        let rem = (&rank % base).to_u32_digits();
        let digit = rem.first().copied().unwrap_or(0) as usize;
        rank /= base;
        let value = table[digit];
        for j in 0..b {
            out[k * b + j] = sy[((value >> (b - 1 - j)) & 1) as usize];
        }
    }
    if !rank.is_zero() {
        return Err(fail("terminal rank"));
    }
    Ok(out)
}
fn record_encode(d: &[u8], request: &str) -> Result<(Vec<u8>, usize), String> {
    if d.len() > MAX_N {
        return Err(fail("source bound"));
    }
    let mut best: Option<Vec<u8>> = None;
    let mut trials = 0;
    let mut consider = |a: Vec<u8>| {
        trials += 1;
        if best.as_ref().is_none_or(|b| a.len() < b.len()) {
            best = Some(a);
        }
    };
    if request == "raw" || request == "auto" {
        consider(record_build(d, Mode::Raw, 0, 0, 0)?);
    }
    if let Some(sy) = alphabet(d) {
        for b in 2..=12 {
            if d.len() % b != 0 {
                continue;
            }
            let (mask, h) = observed(d, sy, b);
            if mask != 0 && (request == "e" || request == "auto") {
                consider(record_build(d, Mode::E, b, mask, 0)?);
            }
            if let Some(h) = h {
                if request == "c" || request == "auto" {
                    consider(record_build(d, Mode::C, b, 0, h)?);
                }
                if mask != 0 && (request == "ec" || request == "auto") {
                    consider(record_build(d, Mode::EC, b, mask, h)?);
                }
            }
        }
    }
    best.map(|a| (a, trials))
        .ok_or_else(|| fail("no applicable candidate"))
}
fn main() -> Result<(), String> {
    let a: Vec<String> = env::args().collect();
    match a.get(1).map(String::as_str) {
        Some("encode") if a.len() == 5 => {
            if !["raw", "e", "c", "ec", "auto"].contains(&a[2].as_str()) {
                return Err(fail("mode"));
            }
            let d = bounded(&a[3], MAX_N)?;
            let (out, trials) = record_encode(&d, &a[2])?;
            if record_decode(&out)? != d {
                return Err(fail("internal round trip"));
            }
            fs::write(&a[4], &out).map_err(|e| e.to_string())?;
            println!(
                "bytes={} trials={} mode={} width={} equality_mask={} count={}",
                out.len(),
                trials,
                out[5],
                out[10],
                u16::from_le_bytes(out[11..13].try_into().unwrap()),
                out[13]
            );
            Ok(())
        }
        Some("decode") if a.len() == 4 => {
            let arc = bounded(&a[2], HEADER + MAX_N + 4)?;
            let d = record_decode(&arc)?;
            fs::write(&a[3], d).map_err(|e| e.to_string())?;
            Ok(())
        }
        _ => Err(fail(
            "usage: erc encode raw|e|c|ec|auto INPUT ARCHIVE | erc decode ARCHIVE OUTPUT",
        )),
    }
}
