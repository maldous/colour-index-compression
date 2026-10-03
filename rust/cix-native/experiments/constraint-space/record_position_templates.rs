//! Isolated RXP1 exact-record exception-position template experiment.
//!
//! It learns only from the supplied bytes.  RXP1 shares REX's local table
//! discovery and payload ranks, but pays for and selects a position-map codec:
//! canonical combinadic (colex), a four-byte arithmetic progression, or the
//! archive-only Zstd CLI -19 (C API level +19) u16 gap-vector control.
use num_bigint::BigUint;
use num_traits::{One, Zero};
use std::{env, ffi::c_void, fs, io::Read, time::Instant};

const MAX_N: usize = 16_384;
const MAX_ARCHIVE: usize = 30_000;
const HEADER: usize = 32;

#[derive(Clone, Copy, Eq, PartialEq)]
enum Kind {
    Raw = 0,
    Exceptions = 1,
}
#[derive(Clone, Copy, Eq, PartialEq)]
enum Count {
    None = 0,
    Exact = 1,
    Max = 2,
}
#[derive(Clone, Copy, Eq, PartialEq)]
enum PositionCodec {
    Colex = 0,
    Progression = 1,
    ZstdGaps = 2,
}
#[derive(Clone, Copy, Eq, PartialEq)]
enum PositionPolicy {
    Auto,
    Colex,
    Progression,
    ZstdGaps,
}
#[derive(Clone, Copy)]
struct Model {
    b: usize,
    mask: u16,
    count: Count,
    param: u8,
}

// libzstd 1.5.5 is supplied by the native host.  Every FFI buffer is owned by
// Rust, its pointer is valid for the supplied length, and output capacity is
// either ZSTD_compressBound(input length) or the exactly prevalidated u16 gap
// vector length (at most MAX_N).  ZSTD_isError is checked before every result.
#[link(name = "zstd")]
unsafe extern "C" {
    fn ZSTD_compressBound(src_size: usize) -> usize;
    fn ZSTD_compress(
        dst: *mut c_void,
        dst_capacity: usize,
        src: *const c_void,
        src_size: usize,
        compression_level: i32,
    ) -> usize;
    fn ZSTD_decompress(
        dst: *mut c_void,
        dst_capacity: usize,
        src: *const c_void,
        compressed_size: usize,
    ) -> usize;
    fn ZSTD_findFrameCompressedSize(src: *const c_void, src_size: usize) -> usize;
    fn ZSTD_isError(code: usize) -> u32;
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
        Err(fail("bound"))
    } else {
        Ok(d)
    }
}
fn crc(d: &[u8]) -> u32 {
    let mut c = !0u32;
    for &x in d {
        c ^= x as u32;
        for _ in 0..8 {
            c = if c & 1 != 0 {
                (c >> 1) ^ 0xedb88320
            } else {
                c >> 1
            }
        }
    }
    !c
}
fn choose(n: usize, k: usize) -> BigUint {
    if k > n {
        return BigUint::zero();
    }
    let k = k.min(n - k);
    let mut x = BigUint::one();
    for d in 1..=k {
        x *= n - k + d;
        x /= d;
    }
    x
}
fn width(x: &BigUint) -> usize {
    if x.is_zero() {
        0
    } else {
        (x - BigUint::one()).bits() as usize
    }
}
fn power(base: usize, n: usize) -> BigUint {
    let mut x = BigUint::one();
    for _ in 0..n {
        x *= base;
    }
    x
}
fn pack(x: &BigUint, w: usize) -> Result<Vec<u8>, String> {
    if x.bits() > w as u64 {
        return Err(fail("rank width"));
    }
    let n = w.div_ceil(8);
    if n == 0 {
        return x.is_zero().then(Vec::new).ok_or_else(|| fail("empty rank"));
    }
    let v = x.to_bytes_be();
    if v.len() > n {
        return Err(fail("rank allocation"));
    }
    let mut out = vec![0; n];
    out[n - v.len()..].copy_from_slice(&v);
    Ok(out)
}
fn unpack(d: &[u8], w: usize) -> Result<BigUint, String> {
    if d.len() != w.div_ceil(8) {
        return Err(fail("rank length"));
    }
    let x = BigUint::from_bytes_be(d);
    if x.bits() > w as u64 {
        return Err(fail("rank padding"));
    }
    Ok(x)
}
fn alphabet(d: &[u8]) -> Option<[u8; 2]> {
    let mut s = [false; 256];
    for &x in d {
        s[x as usize] = true
    }
    let v: Vec<u8> = s
        .iter()
        .enumerate()
        .filter_map(|(i, &p)| p.then_some(i as u8))
        .collect();
    if v.len() == 2 {
        Some([v[0], v[1]])
    } else {
        None
    }
}
fn word(d: &[u8], sy: [u8; 2]) -> u16 {
    d.iter().fold(0, |x, &v| (x << 1) | u16::from(v == sy[1]))
}
fn table(m: Model) -> Vec<u16> {
    (0..1usize << m.b)
        .filter(|&x| {
            let x = x as u16;
            let equal = (0..m.b - 1).all(|j| {
                m.mask & (1 << j) == 0 || ((x >> (m.b - 1 - j)) & 1) == ((x >> (m.b - 2 - j)) & 1)
            });
            let c = x.count_ones() as u8;
            equal
                && match m.count {
                    Count::None => true,
                    Count::Exact => c == m.param,
                    Count::Max => c <= m.param,
                }
        })
        .map(|x| x as u16)
        .collect()
}
fn colex_rank(v: &[usize]) -> BigUint {
    v.iter()
        .enumerate()
        .fold(BigUint::zero(), |r, (i, &x)| r + choose(x, i + 1))
}
fn colex_unrank(mut rank: BigUint, n: usize, k: usize) -> Result<Vec<usize>, String> {
    if rank >= choose(n, k) {
        return Err(fail("map rank"));
    }
    if k == 0 {
        return rank.is_zero().then(Vec::new).ok_or_else(|| fail("map rank"));
    }
    let mut out = vec![0; k];
    let mut remaining = k;
    let mut top = n.checked_sub(1).ok_or_else(|| fail("map rank"))?;
    // Scan C(top, remaining) downward once.  On a skipped top, use
    // C(x-1,k)=C(x,k)*(x-k)/x; on selection, use
    // C(x-1,k-1)=C(x,k)*k/x.  This avoids repeated binary searches and
    // recomputation of BigUint binomials for dense maps.
    let mut binomial = choose(top, remaining);
    while remaining != 0 {
        if binomial <= rank {
            out[remaining - 1] = top;
            rank -= &binomial;
            if remaining == 1 {
                break;
            }
            binomial = (binomial * remaining) / top;
            remaining -= 1;
            top = top.checked_sub(1).ok_or_else(|| fail("map rank"))?;
        } else {
            if top == 0 {
                return Err(fail("map rank"));
            }
            binomial = (binomial * (top - remaining)) / top;
            top -= 1;
        }
    }
    if !rank.is_zero() || out.windows(2).any(|x| x[0] >= x[1]) {
        Err(fail("map rank"))
    } else {
        Ok(out)
    }
}
fn zstd_compress(input: &[u8]) -> Result<Vec<u8>, String> {
    let cap = unsafe { ZSTD_compressBound(input.len()) };
    let mut output = vec![0u8; cap];
    let written = unsafe {
        ZSTD_compress(
            output.as_mut_ptr().cast(),
            output.len(),
            input.as_ptr().cast(),
            input.len(),
            19,
        )
    };
    if unsafe { ZSTD_isError(written) } != 0 || written > output.len() {
        return Err(fail("zstd compress"));
    }
    output.truncate(written);
    Ok(output)
}
fn gap_vector(positions: &[usize], records: usize) -> Result<Vec<u8>, String> {
    if positions.len().checked_mul(2).ok_or_else(|| fail("gap length"))? > MAX_N {
        return Err(fail("gap length"));
    }
    let mut gaps = Vec::with_capacity(positions.len() * 2);
    let mut previous = 0usize;
    for (i, &position) in positions.iter().enumerate() {
        if position >= records || position > u16::MAX as usize {
            return Err(fail("gap position"));
        }
        let gap = if i == 0 {
            position
        } else {
            position
                .checked_sub(previous)
                .ok_or_else(|| fail("gap order"))?
        };
        if i != 0 && gap == 0 || gap > u16::MAX as usize {
            return Err(fail("gap value"));
        }
        gaps.extend((gap as u16).to_le_bytes());
        previous = position;
    }
    Ok(gaps)
}
fn zstd_gaps(positions: &[usize], records: usize) -> Result<Vec<u8>, String> {
    zstd_compress(&gap_vector(positions, records)?)
}
enum SelectedMap {
    Colex(usize),
    Progression,
    ZstdGaps(Vec<u8>),
}
impl SelectedMap {
    fn len(&self) -> usize {
        match self {
            Self::Colex(len) => *len,
            Self::Progression => 4,
            Self::ZstdGaps(bytes) => bytes.len(),
        }
    }
}
fn progression_legal(positions: &[usize], records: usize) -> Option<()> {
    if positions.len() < 2 {
        return None;
    }
    let start = positions[0];
    let step = positions[1].checked_sub(start)?;
    let last = start.checked_add(step.checked_mul(positions.len() - 1)?)?;
    (step > 0
        && last < records
        && positions.iter().enumerate().all(|(j, &p)| p == start + j * step)
        && start <= u16::MAX as usize
        && step <= u16::MAX as usize)
        .then_some(())
}
fn select_position_map(
    positions: &[usize],
    records: usize,
    policy: PositionPolicy,
) -> Result<Option<SelectedMap>, String> {
    if policy == PositionPolicy::Colex {
        let colex_len = width(&choose(records, positions.len())).div_ceil(8);
        return Ok(Some(SelectedMap::Colex(colex_len)));
    }
    if policy == PositionPolicy::Progression {
        return Ok(progression_legal(positions, records).map(|_| SelectedMap::Progression));
    }
    if policy == PositionPolicy::ZstdGaps {
        return Ok(Some(SelectedMap::ZstdGaps(zstd_gaps(positions, records)?)));
    }
    let colex_len = width(&choose(records, positions.len())).div_ceil(8);
    let zstd = zstd_gaps(positions, records)?;
    if colex_len > 4 && progression_legal(positions, records).is_some() {
        if zstd.len() < 4 {
            return Ok(Some(SelectedMap::ZstdGaps(zstd)));
        }
        return Ok(Some(SelectedMap::Progression));
    }
    if zstd.len() < colex_len {
        Ok(Some(SelectedMap::ZstdGaps(zstd)))
    } else {
        Ok(Some(SelectedMap::Colex(colex_len)))
    }
}
fn position_map(
    positions: &[usize],
    records: usize,
    policy: PositionPolicy,
) -> Result<(PositionCodec, Vec<u8>), String> {
    match select_position_map(positions, records, policy)? {
        Some(SelectedMap::Colex(_)) => Ok((
            PositionCodec::Colex,
            pack(
                &colex_rank(positions),
                width(&choose(records, positions.len())),
            )?,
        )),
        Some(SelectedMap::Progression) => {
            let start = positions[0] as u16;
            let step = (positions[1] - positions[0]) as u16;
            let mut map = Vec::with_capacity(4);
            map.extend(start.to_le_bytes());
            map.extend(step.to_le_bytes());
            Ok((PositionCodec::Progression, map))
        }
        Some(SelectedMap::ZstdGaps(map)) => Ok((PositionCodec::ZstdGaps, map)),
        None => Err(fail("position policy unavailable")),
    }
}
fn decode_positions(
    codec: PositionCodec,
    map: &[u8],
    records: usize,
    exceptions: usize,
) -> Result<Vec<usize>, String> {
    match codec {
        PositionCodec::Colex => {
            let card = choose(records, exceptions);
            if map.len() != width(&card).div_ceil(8) {
                return Err(fail("noncanonical map length"));
            }
            let rank = unpack(map, width(&card))?;
            if rank >= card {
                return Err(fail("map rank range"));
            }
            colex_unrank(rank, records, exceptions)
        }
        PositionCodec::Progression => {
            if exceptions < 2 || map.len() != 4 {
                return Err(fail("progression length"));
            }
            let start = u16::from_le_bytes(map[..2].try_into().unwrap()) as usize;
            let step = u16::from_le_bytes(map[2..4].try_into().unwrap()) as usize;
            if step == 0 {
                return Err(fail("progression step"));
            }
            let last = start
                .checked_add(
                    step.checked_mul(exceptions - 1)
                        .ok_or_else(|| fail("progression overflow"))?,
                )
                .ok_or_else(|| fail("progression overflow"))?;
            if last >= records {
                return Err(fail("progression range"));
            }
            Ok((0..exceptions).map(|j| start + j * step).collect())
        }
        PositionCodec::ZstdGaps => {
            let decoded_len = exceptions
                .checked_mul(2)
                .filter(|&n| n <= MAX_N)
                .ok_or_else(|| fail("gap length"))?;
            let mut gaps = vec![0u8; decoded_len];
            let frame_len = unsafe { ZSTD_findFrameCompressedSize(map.as_ptr().cast(), map.len()) };
            if unsafe { ZSTD_isError(frame_len) } != 0 || frame_len != map.len() {
                return Err(fail("zstd frame"));
            }
            let written = unsafe {
                ZSTD_decompress(
                    gaps.as_mut_ptr().cast(),
                    gaps.len(),
                    map.as_ptr().cast(),
                    map.len(),
                )
            };
            if unsafe { ZSTD_isError(written) } != 0 || written != gaps.len() {
                return Err(fail("zstd gaps"));
            }
            let mut positions = Vec::with_capacity(exceptions);
            let mut previous = 0usize;
            for i in 0..exceptions {
                let gap = u16::from_le_bytes(gaps[i * 2..i * 2 + 2].try_into().unwrap()) as usize;
                if i != 0 && gap == 0 {
                    return Err(fail("gap step"));
                }
                let position = if i == 0 { gap } else {
                    previous.checked_add(gap).ok_or_else(|| fail("gap overflow"))?
                };
                if position >= records {
                    return Err(fail("gap range"));
                }
                positions.push(position);
                previous = position;
            }
            Ok(positions)
        }
    }
}
fn bits_pack(values: &[u16], b: usize) -> Vec<u8> {
    let mut out = vec![0; (values.len() * b).div_ceil(8)];
    for (i, &v) in values.iter().enumerate() {
        for j in 0..b {
            if (v >> (b - 1 - j)) & 1 != 0 {
                let p = i * b + j;
                out[p / 8] |= 1 << (7 - p % 8)
            }
        }
    }
    out
}
fn bits_unpack(d: &[u8], n: usize, b: usize) -> Result<Vec<u16>, String> {
    if d.len() != (n * b).div_ceil(8) {
        return Err(fail("exception length"));
    }
    if n * b % 8 != 0 && d.last().copied().unwrap_or(0) & ((1 << (8 - n * b % 8)) - 1) != 0 {
        return Err(fail("exception padding"));
    }
    let mut v = Vec::with_capacity(n);
    for i in 0..n {
        let mut x = 0;
        for j in 0..b {
            let p = i * b + j;
            x = (x << 1) | u16::from(d[p / 8] & (1 << (7 - p % 8)) != 0)
        }
        v.push(x)
    }
    Ok(v)
}
fn header(
    k: Kind,
    n: usize,
    m: Model,
    codec: PositionCodec,
    sy: [u8; 2],
    r: usize,
    e: usize,
    ml: usize,
    pl: usize,
    xl: usize,
) -> Vec<u8> {
    let mut x = b"RXP1".to_vec();
    x.extend([1, k as u8]);
    x.extend((n as u32).to_le_bytes());
    x.push(if k == Kind::Raw { 0 } else { m.b as u8 });
    x.extend(if k == Kind::Raw { [0, 0] } else { sy });
    x.extend((if k == Kind::Raw { 0 } else { r } as u32).to_le_bytes());
    x.extend((if k == Kind::Raw { 0 } else { e } as u32).to_le_bytes());
    x.extend((if k == Kind::Raw { 0 } else { m.mask }).to_le_bytes());
    x.extend([
        if k == Kind::Raw { 0 } else { m.count as u8 },
        if k == Kind::Raw { 0 } else { m.param },
    ]);
    x.push(if k == Kind::Raw { PositionCodec::Colex as u8 } else { codec as u8 });
    x.extend((ml as u16).to_le_bytes());
    x.extend((pl as u16).to_le_bytes());
    x.extend((xl as u16).to_le_bytes());
    assert_eq!(x.len(), HEADER);
    x
}
fn raw(d: &[u8]) -> Vec<u8> {
    let m = Model {
        b: 2,
        mask: 0,
        count: Count::None,
        param: 0,
    };
    let mut x = header(Kind::Raw, d.len(), m, PositionCodec::Colex, [0, 0], 0, 0, 0, d.len(), 0);
    x.extend(d);
    x.extend(crc(&x).to_le_bytes());
    x
}
fn build(
    d: &[u8],
    sy: [u8; 2],
    m: Model,
    policy: PositionPolicy,
) -> Result<Vec<u8>, String> {
    let r = d.len() / m.b;
    let t = table(m);
    if t.is_empty() {
        return Err(fail("empty model"));
    }
    let mut bad = Vec::new();
    let mut good = Vec::new();
    let mut exception = Vec::new();
    for (i, c) in d.chunks_exact(m.b).enumerate() {
        let v = word(c, sy);
        match t.binary_search(&v) {
            Ok(q) => good.push(q),
            Err(_) => {
                bad.push(i);
                exception.push(v)
            }
        }
    }
    let e = bad.len();
    let (codec, map) = position_map(&bad, r, policy)?;
    let mut rank = BigUint::zero();
    for q in good {
        rank = rank * t.len() + q
    }
    let payload_card = power(t.len(), r - e);
    let payload = pack(&rank, width(&payload_card))?;
    let ex = bits_pack(&exception, m.b);
    let mut out = header(
        Kind::Exceptions,
        d.len(),
        m,
        codec,
        sy,
        r,
        e,
        map.len(),
        payload.len(),
        ex.len(),
    );
    out.extend(&map);
    out.extend(&payload);
    out.extend(&ex);
    out.extend(crc(&out).to_le_bytes());
    if out.len() > MAX_ARCHIVE {
        return Err(fail("archive bound"));
    }
    Ok(out)
}
fn decode(d: &[u8]) -> Result<Vec<u8>, String> {
    if d.len() < HEADER + 4 || d.len() > MAX_ARCHIVE || &d[..4] != b"RXP1" {
        return Err(fail("envelope"));
    }
    let end = d.len() - 4;
    if crc(&d[..end]) != u32::from_le_bytes(d[end..].try_into().unwrap()) {
        return Err(fail("CRC"));
    }
    if d[4] != 1 {
        return Err(fail("version"));
    }
    let k = match d[5] {
        0 => Kind::Raw,
        1 => Kind::Exceptions,
        _ => return Err(fail("kind")),
    };
    let n = u32::from_le_bytes(d[6..10].try_into().unwrap()) as usize;
    let b = d[10] as usize;
    let sy = [d[11], d[12]];
    let r = u32::from_le_bytes(d[13..17].try_into().unwrap()) as usize;
    let e = u32::from_le_bytes(d[17..21].try_into().unwrap()) as usize;
    let mask = u16::from_le_bytes(d[21..23].try_into().unwrap());
    let mode = match d[23] {
        0 => Count::None,
        1 => Count::Exact,
        2 => Count::Max,
        _ => return Err(fail("count mode")),
    };
    let p = d[24];
    let codec = match d[25] {
        0 => PositionCodec::Colex,
        1 => PositionCodec::Progression,
        2 => PositionCodec::ZstdGaps,
        _ => return Err(fail("position codec")),
    };
    let ml = u16::from_le_bytes(d[26..28].try_into().unwrap()) as usize;
    let pl = u16::from_le_bytes(d[28..30].try_into().unwrap()) as usize;
    let xl = u16::from_le_bytes(d[30..32].try_into().unwrap()) as usize;
    if n > MAX_N || HEADER + ml + pl + xl != end {
        return Err(fail("lengths"));
    }
    let body = &d[HEADER..end];
    if k == Kind::Raw {
        if b != 0
            || sy != [0, 0]
            || r != 0
            || e != 0
            || mask != 0
            || d[23] != 0
            || p != 0
            || codec != PositionCodec::Colex
            || ml != 0
            || xl != 0
            || pl != n
        {
            return Err(fail("raw metadata"));
        }
        return Ok(body.to_vec());
    }
    if !(2..=12).contains(&b)
        || n == 0
        || n % b != 0
        || r != n / b
        || e > r
        || sy[0] >= sy[1]
        || mask >> (b - 1) != 0
        || match mode {
            Count::None => p != 0,
            Count::Exact | Count::Max => p as usize > b,
        }
    {
        return Err(fail("metadata"));
    }
    let m = Model {
        b,
        mask,
        count: mode,
        param: p,
    };
    let t = table(m);
    if t.is_empty() {
        return Err(fail("empty model"));
    }
    let pc = power(t.len(), r - e);
    let canonical_ml = match codec {
        PositionCodec::Colex => width(&choose(r, e)).div_ceil(8),
        PositionCodec::Progression => 4,
        PositionCodec::ZstdGaps => {
            if ml == 0 {
                return Err(fail("zstd map length"));
            }
            ml
        }
    };
    if ml != canonical_ml || pl != width(&pc).div_ceil(8) || xl != (e * b).div_ceil(8) {
        return Err(fail("noncanonical lengths"));
    }
    let positions = decode_positions(codec, &body[..ml], r, e)?;
    let mut rank = unpack(&body[ml..ml + pl], width(&pc))?;
    if rank >= pc {
        return Err(fail("payload rank"));
    }
    let exceptions = bits_unpack(&body[ml + pl..], e, b)?;
    let mut out = vec![0; n];
    let mut pi = 0;
    let mut xi = 0;
    let base = BigUint::from(t.len());
    for rec in (0..r).rev() {
        let exceptional = positions.binary_search(&rec).is_ok();
        let v = if exceptional {
            let v = exceptions[e - 1 - xi];
            xi += 1;
            if t.binary_search(&v).is_ok() {
                return Err(fail("noncanonical exception"));
            }
            v
        } else {
            let q = (&rank % &base)
                .to_u32_digits()
                .first()
                .copied()
                .unwrap_or(0) as usize;
            rank /= &base;
            t[q]
        };
        for j in 0..b {
            out[rec * b + j] = sy[((v >> (b - 1 - j)) & 1) as usize]
        }
        pi += 1;
    }
    if pi != r || xi != e || !rank.is_zero() {
        return Err(fail("terminal"));
    }
    Ok(out)
}
fn inferred(d: &[u8], sy: [u8; 2], b: usize) -> Vec<Model> {
    let records = d.len() / b;
    let mut equality_histogram = vec![0usize; 1usize << (b - 1)];
    let mut edge_hits = vec![0usize; b - 1];
    let mut count_histogram = vec![0usize; b + 1];
    for c in d.chunks_exact(b) {
        let mut equality = 0u16;
        for j in 0..b - 1 {
            if c[j] == c[j + 1] {
                equality |= 1 << j;
                edge_hits[j] += 1;
            }
        }
        equality_histogram[equality as usize] += 1;
        count_histogram[c.iter().filter(|&&x| x == sy[1]).count()] += 1;
    }
    let mut masks = vec![0u16];
    let mut observed_masks: Vec<(usize, u16)> = equality_histogram
        .iter()
        .enumerate()
        .filter_map(|(mask, &hits)| (hits != 0).then_some((hits, mask as u16)))
        .collect();
    observed_masks.sort_by(|left, right| right.0.cmp(&left.0).then(left.1.cmp(&right.1)));
    masks.extend(observed_masks.iter().take(4).map(|&(_, mask)| mask));
    let mut majority = 0u16;
    for (edge, &hits) in edge_hits.iter().enumerate() {
        if hits * 2 >= records {
            majority |= 1 << edge;
        }
    }
    masks.push(majority);
    let mut edges: Vec<(usize, usize)> = edge_hits
        .iter()
        .copied()
        .enumerate()
        .map(|(edge, hits)| (hits, edge))
        .collect();
    edges.sort_by(|left, right| right.0.cmp(&left.0).then(left.1.cmp(&right.1)));
    masks.extend(edges.iter().take(4).map(|&(_, edge)| 1u16 << edge));
    masks.sort();
    masks.dedup();

    let mut count_modes = vec![(Count::None, 0u8)];
    let mut count_labels: Vec<(usize, u8)> = count_histogram
        .iter()
        .enumerate()
        .filter_map(|(count, &hits)| (hits != 0).then_some((hits, count as u8)))
        .collect();
    count_labels.sort_by(|left, right| right.0.cmp(&left.0).then(left.1.cmp(&right.1)));
    count_modes.extend(
        count_labels
            .iter()
            .take(2)
            .map(|&(_, count)| (Count::Exact, count)),
    );
    let mut sorted_counts = Vec::with_capacity(records);
    for (count, &hits) in count_histogram.iter().enumerate() {
        sorted_counts.extend(std::iter::repeat(count as u8).take(hits));
    }
    let upper = sorted_counts[(records * 3) / 4];
    let maximum = *sorted_counts.last().unwrap();
    for limit in [upper, maximum] {
        if limit < b as u8 {
            count_modes.push((Count::Max, limit));
        }
    }
    let mut out = Vec::new();
    for &m in &masks {
        for &(count, param) in &count_modes {
            let x = Model {
                b,
                mask: m,
                count,
                param,
            };
            if !out
                .iter()
                .any(|y: &Model| y.mask == x.mask && y.count == x.count && y.param == x.param)
            {
                out.push(x)
            }
        }
    }
    // Ten masks times at most five count modes is bounded below 64; use a
    // fixed final cap so all eleven widths remain below 500 total candidates.
    out.truncate(40);
    out
}
// Exact final wire length.  Rank widths are cardinality-exact; the Zstd map is
// deliberately materialized so the control competes on its real archive cost.
fn final_cost(
    d: &[u8],
    sy: [u8; 2],
    m: Model,
    policy: PositionPolicy,
) -> Result<Option<usize>, String> {
    let t = table(m);
    if t.is_empty() {
        return Ok(None);
    }
    let r = d.len() / m.b;
    let positions: Vec<usize> = d
        .chunks_exact(m.b)
        .enumerate()
        .filter_map(|(i, c)| t.binary_search(&word(c, sy)).is_err().then_some(i))
        .collect();
    let e = positions.len();
    let Some(map) = select_position_map(&positions, r, policy)? else {
        return Ok(None);
    };
    Ok(Some(
        HEADER
            + 4
            + map.len()
            + width(&power(t.len(), r - e)).div_ceil(8)
            + (m.b * e).div_ceil(8),
    ))
}
fn main() -> Result<(), String> {
    let a: Vec<String> = env::args().collect();
    match a.get(1).map(String::as_str) {
        Some("encode") if a.len() == 4 || a.len() == 6 => {
            let (policy, input, archive) = if a.len() == 4 {
                (PositionPolicy::Auto, &a[2], &a[3])
            } else {
                if a[2] != "--positions" {
                    return Err(fail("positions flag"));
                }
                let policy = match a[3].as_str() {
                    "auto" => PositionPolicy::Auto,
                    "colex" => PositionPolicy::Colex,
                    "progression" => PositionPolicy::Progression,
                    "zstd-gaps" => PositionPolicy::ZstdGaps,
                    _ => return Err(fail("positions mode")),
                };
                (policy, &a[4], &a[5])
            };
            let data = bounded(input, MAX_N)?;
            let start = Instant::now();
            let mut best = raw(&data);
            let mut selected = None;
            let mut candidates = 1usize;
            if let Some(symbols) = alphabet(&data) {
                for b in 2..=12 {
                    if data.is_empty() || data.len() % b != 0 {
                        continue;
                    }
                    for model in inferred(&data, symbols, b) {
                        candidates += 1;
                        let Some(cost) = final_cost(&data, symbols, model, policy)? else {
                            continue;
                        };
                        if cost >= best.len() {
                            continue;
                        }
                        let candidate = build(&data, symbols, model, policy)?;
                        if candidate.len() != cost {
                            return Err(fail("wire cost identity"));
                        }
                        if candidate.len() < best.len() {
                            best = candidate;
                            selected = Some(model);
                        }
                    }
                }
            }
            let discovery_ns = start.elapsed().as_nanos();
            if decode(&best)? != data {
                return Err(fail("internal decode"));
            }
            fs::write(archive, &best).map_err(|e| e.to_string())?;
            let structural = selected.is_some();
            let b = selected.map_or(0, |model| model.b);
            println!(
                "{{\"format\":\"{}\",\"bytes\":{},\"header_bytes\":{},\"crc_bytes\":4,\"b\":{},\"r\":{},\"e\":{},\"mask\":{},\"mode\":{},\"param\":{},\"position_codec\":\"{}\",\"map_bytes\":{},\"payload_bytes\":{},\"exception_bytes\":{},\"discovery_ns\":{},\"candidates\":{}}}",
                if structural { "exceptions" } else { "raw" }, best.len(), HEADER, b,
                if structural { u32::from_le_bytes(best[13..17].try_into().unwrap()) } else { 0 },
                if structural { u32::from_le_bytes(best[17..21].try_into().unwrap()) } else { 0 },
                if structural { u16::from_le_bytes(best[21..23].try_into().unwrap()) } else { 0 },
                if structural { best[23] } else { 0 }, if structural { best[24] } else { 0 },
                match best[25] { 0 => "colex", 1 => "progression", 2 => "zstd-gaps", _ => "invalid" },
                u16::from_le_bytes(best[26..28].try_into().unwrap()),
                u16::from_le_bytes(best[28..30].try_into().unwrap()),
                u16::from_le_bytes(best[30..32].try_into().unwrap()), discovery_ns, candidates
            );
            Ok(())
        }
        Some("decode") if a.len() == 4 => {
            let archive = bounded(&a[2], MAX_ARCHIVE)?;
            let output = decode(&archive)?;
            fs::write(&a[3], output).map_err(|e| e.to_string())
        }
        _ => Err(fail(
            "usage: record_position_templates encode [--positions auto|colex|progression|zstd-gaps] INPUT ARCHIVE | record_position_templates decode ARCHIVE OUT",
        )),
    }
}
