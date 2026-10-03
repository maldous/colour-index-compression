//! Isolated CIX constraint-space model-description comparator; no production integration.
//!
//! Forced-model encoding compares complete, self-describing wires for a fixed
//! exact local space.  The separate `discover` command uses only its narrow,
//! fixed primitive bank over complete binary records; it never uses input names,
//! source-file identity, or hidden model assets.
use num_bigint::BigUint;
use num_traits::{One, Zero};
use std::{env, fs, io::Read, time::Instant};

#[path = "model_bdd.rs"]
mod model_bdd;

const MAX_N: usize = 16_384;
const MAX_ARCHIVE: usize = 40_000;
const MAX_MODEL: usize = 21_000;
const HEADER: usize = 15;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct Atom {
    op: u8,
    mask: u16,
    param: u8,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Kind {
    Raw = 0,
    Subset = 1,
    Bitset = 2,
    Rle = 3,
    Flat = 4,
    PackedFlat = 5,
    Shared = 6,
    Bdd = 7,
    Auto = 255,
}

fn fail(s: &str) -> String {
    s.into()
}
fn bounded(path: &str, cap: usize) -> Result<Vec<u8>, String> {
    let file = fs::File::open(path).map_err(|e| e.to_string())?;
    let mut data = Vec::new();
    file.take((cap + 1) as u64)
        .read_to_end(&mut data)
        .map_err(|e| e.to_string())?;
    if data.len() > cap {
        return Err(fail("experimental input bound"));
    }
    Ok(data)
}
fn crc(data: &[u8]) -> u32 {
    let mut c = !0u32;
    for &x in data {
        c ^= x as u32;
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
fn width(card: &BigUint) -> usize {
    if card.is_zero() {
        0
    } else {
        (card - BigUint::one()).bits() as usize
    }
}
fn power(base: usize, n: usize) -> BigUint {
    let mut x = BigUint::one();
    for _ in 0..n {
        x *= base;
    }
    x
}
fn pack(x: &BigUint, bits: usize) -> Result<Vec<u8>, String> {
    if x.bits() > bits as u64 {
        return Err(fail("rank width"));
    }
    let bytes = bits.div_ceil(8);
    if bytes == 0 {
        return x.is_zero().then(Vec::new).ok_or_else(|| fail("empty rank"));
    }
    let raw = x.to_bytes_be();
    if raw.len() > bytes {
        return Err(fail("rank allocation"));
    }
    let mut out = vec![0; bytes];
    out[bytes - raw.len()..].copy_from_slice(&raw);
    Ok(out)
}
fn unpack(data: &[u8], bits: usize) -> Result<BigUint, String> {
    if data.len() != bits.div_ceil(8) {
        return Err(fail("rank length"));
    }
    let x = BigUint::from_bytes_be(data);
    if x.bits() > bits as u64 {
        return Err(fail("rank high padding"));
    }
    Ok(x)
}
fn alphabet(data: &[u8]) -> Option<[u8; 2]> {
    let mut seen = [false; 256];
    for &x in data {
        seen[x as usize] = true
    }
    let v: Vec<u8> = seen
        .iter()
        .enumerate()
        .filter_map(|(i, &x)| x.then_some(i as u8))
        .collect();
    if v.len() == 2 {
        Some([v[0], v[1]])
    } else {
        None
    }
}
fn word(data: &[u8], sy: [u8; 2]) -> u16 {
    data.iter()
        .fold(0, |v, &x| (v << 1) | u16::from(x == sy[1]))
}
fn validate_atom(b: usize, a: Atom) -> Result<(), String> {
    let u = 1usize << b;
    if a.op > 3 || a.mask == 0 || a.mask as usize >= u {
        return Err(fail("atom selector/op"));
    }
    match a.op {
        0 | 1 if a.param as usize > b => Err(fail("count parameter")),
        2 | 3 if a.param > 1 => Err(fail("parity parameter")),
        3 if a.mask.count_ones() < 2 => Err(fail("xor endpoints requires two bits")),
        _ => Ok(()),
    }
}
fn normalize(b: usize, atoms: &mut Vec<Atom>) -> Result<(), String> {
    if atoms.len() > 32 {
        return Err(fail("more than 32 atoms"));
    }
    for &a in atoms.iter() {
        validate_atom(b, a)?;
    }
    atoms.sort();
    atoms.dedup();
    Ok(())
}
fn holds(value: u16, a: Atom) -> bool {
    let selected = (value & a.mask).count_ones() as u8;
    match a.op {
        0 => selected == a.param,
        1 => selected <= a.param,
        2 => (selected & 1) == a.param,
        3 => {
            let lo = a.mask.trailing_zeros();
            let hi = 15 - a.mask.leading_zeros();
            (((value >> lo) ^ (value >> hi)) & 1) as u8 == a.param
        }
        _ => false,
    }
}
fn table(b: usize, atoms: &[Atom]) -> Vec<u16> {
    (0..(1usize << b))
        .filter(|&x| atoms.iter().all(|&a| holds(x as u16, a)))
        .map(|x| x as u16)
        .collect()
}
fn parse_text(data: &[u8]) -> Result<(usize, Vec<Atom>), String> {
    if data.len() > 4096 {
        return Err(fail("model read cap"));
    }
    let text = std::str::from_utf8(data).map_err(|_| fail("model must be UTF-8"))?;
    let mut lines = text.lines();
    let b: usize = lines
        .next()
        .ok_or_else(|| fail("missing bit count"))?
        .trim()
        .parse()
        .map_err(|_| fail("bit count"))?;
    if !(2..=12).contains(&b) {
        return Err(fail("bit count range"));
    }
    let mut atoms = Vec::new();
    for line in lines {
        let p: Vec<&str> = line.split_whitespace().collect();
        if p.is_empty() {
            continue;
        }
        if p.len() != 3 {
            return Err(fail("atom fields"));
        }
        let op: u8 = p[0].parse().map_err(|_| fail("atom op"))?;
        let mask: u16 = p[1].parse().map_err(|_| fail("atom mask"))?;
        let param: u8 = p[2].parse().map_err(|_| fail("atom param"))?;
        atoms.push(Atom { op, mask, param });
    }
    normalize(b, &mut atoms)?;
    Ok((b, atoms))
}
fn colex_rank(values: &[u16]) -> BigUint {
    values
        .iter()
        .enumerate()
        .fold(BigUint::zero(), |r, (i, &v)| r + choose(v as usize, i + 1))
}
fn colex_unrank(mut rank: BigUint, universe: usize, count: usize) -> Result<Vec<u16>, String> {
    let mut out = vec![0u16; count];
    let mut upper = universe;
    for i in (1..=count).rev() {
        let (mut lo, mut hi) = (i - 1, upper);
        while lo + 1 < hi {
            let mid = lo + (hi - lo) / 2;
            if choose(mid, i) <= rank {
                lo = mid
            } else {
                hi = mid
            }
        }
        let t = choose(lo, i);
        if t > rank {
            return Err(fail("subset rank"));
        }
        rank -= t;
        out[i - 1] = lo as u16;
        upper = lo;
    }
    if !rank.is_zero() || out.windows(2).any(|x| x[0] >= x[1]) {
        return Err(fail("subset rank"));
    }
    Ok(out)
}
fn atoms_flat(b: usize, data: &[u8], packed: bool) -> Result<Vec<Atom>, String> {
    if data.is_empty() {
        return Err(fail("flat model"));
    }
    let n = data[0] as usize;
    if n > 32 {
        return Err(fail("atom count"));
    }
    let step = if packed { 3 } else { 4 };
    if data.len() != 1 + n * step {
        return Err(fail("flat model length"));
    }
    let mut a = Vec::with_capacity(n);
    for i in 0..n {
        let q = 1 + i * step;
        if packed {
            let x = data[q];
            a.push(Atom {
                op: x >> 4,
                mask: u16::from_le_bytes(data[q + 1..q + 3].try_into().unwrap()),
                param: x & 15,
            });
        } else {
            a.push(Atom {
                op: data[q],
                mask: u16::from_le_bytes(data[q + 1..q + 3].try_into().unwrap()),
                param: data[q + 3],
            });
        }
    }
    let original = a.clone();
    normalize(b, &mut a)?;
    if a != original {
        return Err(fail("noncanonical flat atoms"));
    }
    Ok(a)
}
fn wire_flat(atoms: &[Atom], packed: bool) -> Vec<u8> {
    let mut out = vec![atoms.len() as u8];
    for a in atoms {
        if packed {
            out.push((a.op << 4) | a.param);
        } else {
            out.push(a.op);
        }
        out.extend(a.mask.to_le_bytes());
        if !packed {
            out.push(a.param);
        }
    }
    out
}
fn wire_shared(atoms: &[Atom]) -> Vec<u8> {
    let mut masks: Vec<u16> = atoms.iter().map(|a| a.mask).collect();
    masks.sort();
    masks.dedup();
    let mut out = vec![masks.len() as u8];
    for m in &masks {
        out.extend(m.to_le_bytes());
    }
    out.push(atoms.len() as u8);
    for a in atoms {
        let id = masks.binary_search(&a.mask).unwrap() as u8;
        out.push((a.op << 6) | id);
        out.push(a.param);
    }
    out
}
fn parse_shared(b: usize, data: &[u8]) -> Result<Vec<Atom>, String> {
    if data.len() < 2 {
        return Err(fail("shared model"));
    }
    let s = data[0] as usize;
    if s == 0 {
        return if data == [0, 0] {
            Ok(Vec::new())
        } else {
            Err(fail("zero-scope shared model"))
        };
    }
    if s > 32 || data.len() < 1 + 2 * s + 1 {
        return Err(fail("shared scopes"));
    }
    let mut masks = Vec::with_capacity(s);
    for i in 0..s {
        masks.push(u16::from_le_bytes(
            data[1 + 2 * i..3 + 2 * i].try_into().unwrap(),
        ));
    }
    if masks.windows(2).any(|x| x[0] >= x[1]) {
        return Err(fail("shared scope order"));
    }
    let at = 1 + 2 * s;
    let n = data[at] as usize;
    if n > 32 || data.len() != at + 1 + 2 * n {
        return Err(fail("shared atom length"));
    }
    let mut used = vec![false; s];
    let mut atoms = Vec::with_capacity(n);
    for i in 0..n {
        let x = data[at + 1 + 2 * i];
        let id = (x & 63) as usize;
        if id >= s {
            return Err(fail("shared scope id"));
        }
        used[id] = true;
        atoms.push(Atom {
            op: x >> 6,
            mask: masks[id],
            param: data[at + 2 + 2 * i],
        });
    }
    if used.iter().any(|&x| !x) {
        return Err(fail("unused shared selector"));
    }
    let original = atoms.clone();
    normalize(b, &mut atoms)?;
    if atoms != original {
        return Err(fail("noncanonical shared atoms"));
    }
    Ok(atoms)
}
fn wire_model(kind: Kind, b: usize, atoms: &[Atom], members: &[u16]) -> Result<Vec<u8>, String> {
    let u = 1usize << b;
    match kind {
        Kind::Subset => {
            let m = members.len();
            let c = choose(u, m);
            let mut x = (m as u16).to_le_bytes().to_vec();
            x.extend(pack(&colex_rank(members), width(&c))?);
            Ok(x)
        }
        Kind::Bitset => {
            let mut x = vec![0; (u + 7) / 8];
            for &v in members {
                x[v as usize / 8] |= 1 << (v % 8);
            }
            Ok(x)
        }
        Kind::Rle => {
            let mut runs: Vec<(u16,u16)> = Vec::new();
            for &v in members {
                if let Some(last) = runs.last_mut() {
                    if last.0 + last.1 == v {
                        last.1 += 1;
                        continue;
                    }
                }
                runs.push((v, 1u16));
            }
            let mut x = (runs.len() as u16).to_le_bytes().to_vec();
            for (s, l) in runs {
                x.extend(s.to_le_bytes());
                x.extend(l.to_le_bytes());
            }
            Ok(x)
        }
        Kind::Flat => Ok(wire_flat(atoms, false)),
        Kind::PackedFlat => Ok(wire_flat(atoms, true)),
        Kind::Shared => Ok(wire_shared(atoms)),
        Kind::Bdd => model_bdd::encode(b, members),
        _ => Err(fail("unsupported model kind")),
    }
}
fn parse_model(kind: Kind, b: usize, data: &[u8]) -> Result<Vec<u16>, String> {
    let u = 1usize << b;
    match kind {
        Kind::Subset => {
            if data.len() < 2 {
                return Err(fail("subset model"));
            }
            let m = u16::from_le_bytes(data[..2].try_into().unwrap()) as usize;
            if m == 0 || m > u {
                return Err(fail("subset count"));
            }
            let c = choose(u, m);
            let w = width(&c);
            let r = unpack(&data[2..], w)?;
            if r >= c {
                return Err(fail("subset rank range"));
            }
            colex_unrank(r, u, m)
        }
        Kind::Bitset => {
            if data.len() != (u + 7) / 8 {
                return Err(fail("bitset length"));
            }
            let used = u % 8;
            if used != 0 && data.last().copied().unwrap_or(0) & !((1u8 << used) - 1) != 0 {
                return Err(fail("bitset high padding"));
            }
            let mut out = Vec::new();
            for v in 0..u {
                if data[v / 8] & (1 << (v % 8)) != 0 {
                    out.push(v as u16)
                }
            }
            Ok(out)
        }
        Kind::Rle => {
            if data.len() < 2 {
                return Err(fail("rle model"));
            }
            let n = u16::from_le_bytes(data[..2].try_into().unwrap()) as usize;
            if n == 0 || data.len() != 2 + 4 * n {
                return Err(fail("rle length"));
            }
            let mut out = Vec::new();
            let mut previous_end = None;
            for i in 0..n {
                let p = 2 + 4 * i;
                let s = u16::from_le_bytes(data[p..p + 2].try_into().unwrap()) as usize;
                let l = u16::from_le_bytes(data[p + 2..p + 4].try_into().unwrap()) as usize;
                if l == 0 || s >= u || s + l > u || previous_end.is_some_and(|end| s <= end) {
                    return Err(fail("noncanonical rle"));
                }
                for v in s..s + l {
                    out.push(v as u16)
                }
                previous_end = Some(s + l);
            }
            Ok(out)
        }
        Kind::Flat => Ok(table(b, &atoms_flat(b, data, false)?)),
        Kind::PackedFlat => Ok(table(b, &atoms_flat(b, data, true)?)),
        Kind::Shared => Ok(table(b, &parse_shared(b, data)?)),
        Kind::Bdd => model_bdd::decode(b, data),
        _ => Err(fail("model kind")),
    }
}
fn header(kind: Kind, n: usize, b: usize, sy: [u8; 2], model_len: usize) -> Vec<u8> {
    let mut x = b"MSL1".to_vec();
    x.extend([1, kind as u8]);
    x.extend((n as u32).to_le_bytes());
    x.push(b as u8);
    x.extend(sy);
    x.extend((model_len as u16).to_le_bytes());
    debug_assert_eq!(x.len(), HEADER);
    x
}

#[derive(Clone, Copy, Default)]
struct EncodePhases {
    wire_construct_ns: u128,
    model_compile_ns: u128,
    cardinality_ns: u128,
    symbol_rank_ns: u128,
}

#[derive(Clone, Copy, Default)]
struct DecodePhases {
    model_compile_ns: u128,
    cardinality_ns: u128,
    unrank_ns: u128,
}

fn make(
    kind: Kind,
    data: &[u8],
    b: usize,
    atoms: &[Atom],
) -> Result<(Vec<u8>, usize, usize, EncodePhases), String> {
    if kind == Kind::Raw {
        let mut x = header(kind, data.len(), 0, [0, 0], 0);
        x.extend(data);
        x.extend(crc(&x).to_le_bytes());
        return Ok((x, 0, 0, EncodePhases::default()));
    }
    let sy = alphabet(data).ok_or_else(|| fail("structural input needs exactly two symbols"))?;
    if data.is_empty() || data.len() % b != 0 {
        return Err(fail("structural record alignment"));
    }
    let members = table(b, atoms);
    if members.is_empty() {
        return Err(fail("empty exact model set"));
    }
    let wire_start = Instant::now();
    let model = wire_model(kind, b, atoms, &members)?;
    if model.len() > MAX_MODEL {
        return Err(fail("model bound"));
    }
    let wire_construct_ns = wire_start.elapsed().as_nanos();
    let compile_start = Instant::now();
    let checked = parse_model(kind, b, &model)?;
    if checked != members {
        return Err(fail("model representation changed exact space"));
    }
    let model_compile_ns = compile_start.elapsed().as_nanos();
    let base = members.len();
    let rank_start = Instant::now();
    let mut rank = BigUint::zero();
    for chunk in data.chunks_exact(b) {
        let v = word(chunk, sy);
        let d = members
            .binary_search(&v)
            .map_err(|_| fail("input outside supplied exact model"))?;
        rank = rank * base + d;
    }
    let symbol_rank_ns = rank_start.elapsed().as_nanos();
    let cardinality_start = Instant::now();
    let card = power(base, data.len() / b);
    let cardinality_ns = cardinality_start.elapsed().as_nanos();
    let bits = width(&card);
    let body = pack(&rank, bits)?;
    let mut x = header(kind, data.len(), b, sy, model.len());
    x.extend(model);
    x.extend(body);
    x.extend(crc(&x).to_le_bytes());
    if x.len() > MAX_ARCHIVE {
        return Err(fail("archive bound"));
    }
    Ok((
        x,
        bits,
        members.len(),
        EncodePhases {
            wire_construct_ns,
            model_compile_ns,
            cardinality_ns,
            symbol_rank_ns,
        },
    ))
}
fn kind_from(s: &str) -> Result<Kind, String> {
    match s {
        "raw" => Ok(Kind::Raw),
        "subset" => Ok(Kind::Subset),
        "bitset" => Ok(Kind::Bitset),
        "rle" => Ok(Kind::Rle),
        "flat" => Ok(Kind::Flat),
        "packed-flat" => Ok(Kind::PackedFlat),
        "shared" => Ok(Kind::Shared),
        "bdd" => Ok(Kind::Bdd),
        "auto" => Ok(Kind::Auto),
        _ => Err(fail("kind")),
    }
}
fn decode_with_phases(data: &[u8]) -> Result<(Vec<u8>, DecodePhases), String> {
    if data.len() < HEADER + 4 || data.len() > MAX_ARCHIVE || &data[..4] != b"MSL1" {
        return Err(fail("MSL1 envelope"));
    }
    let end = data.len() - 4;
    if crc(&data[..end]) != u32::from_le_bytes(data[end..].try_into().unwrap()) {
        return Err(fail("CRC"));
    }
    if data[4] != 1 {
        return Err(fail("version"));
    }
    let kind = match data[5] {
        0 => Kind::Raw,
        1 => Kind::Subset,
        2 => Kind::Bitset,
        3 => Kind::Rle,
        4 => Kind::Flat,
        5 => Kind::PackedFlat,
        6 => Kind::Shared,
        7 => Kind::Bdd,
        _ => return Err(fail("kind")),
    };
    let n = u32::from_le_bytes(data[6..10].try_into().unwrap()) as usize;
    let b = data[10] as usize;
    let sy = [data[11], data[12]];
    let ml = u16::from_le_bytes(data[13..15].try_into().unwrap()) as usize;
    if n > MAX_N || ml > MAX_MODEL || HEADER + ml > end {
        return Err(fail("resource or model length"));
    }
    let model = &data[HEADER..HEADER + ml];
    let body = &data[HEADER + ml..end];
    if kind == Kind::Raw {
        if b != 0 || sy != [0, 0] || ml != 0 || body.len() != n {
            return Err(fail("raw metadata"));
        }
        return Ok((body.to_vec(), DecodePhases::default()));
    }
    if !(2..=12).contains(&b) || n == 0 || n % b != 0 || sy[0] >= sy[1] {
        return Err(fail("structural metadata"));
    }
    let compile_start = Instant::now();
    let members = parse_model(kind, b, model)?;
    if members.is_empty() {
        return Err(fail("empty model"));
    }
    let model_compile_ns = compile_start.elapsed().as_nanos();
    let cardinality_start = Instant::now();
    let card = power(members.len(), n / b);
    let cardinality_ns = cardinality_start.elapsed().as_nanos();
    let bits = width(&card);
    let mut rank = unpack(body, bits)?;
    if rank >= card {
        return Err(fail("rank range"));
    }
    let unrank_start = Instant::now();
    let base = BigUint::from(members.len());
    let mut out = vec![0; n];
    for r in (0..n / b).rev() {
        let d = (&rank % &base)
            .to_u32_digits()
            .first()
            .copied()
            .unwrap_or(0) as usize;
        rank /= &base;
        let v = members[d];
        for j in 0..b {
            out[r * b + j] = sy[((v >> (b - 1 - j)) & 1) as usize];
        }
    }
    if !rank.is_zero() {
        return Err(fail("terminal rank"));
    }
    Ok((
        out,
        DecodePhases {
            model_compile_ns,
            cardinality_ns,
            unrank_ns: unrank_start.elapsed().as_nanos(),
        },
    ))
}

fn decode(data: &[u8]) -> Result<Vec<u8>, String> {
    decode_with_phases(data).map(|(output, _)| output)
}
fn timing(
    format: &str,
    model: usize,
    bits: usize,
    rank_bytes: usize,
    total: usize,
    local: usize,
    construct: u128,
    count: u128,
    portfolio_encode: u128,
    decode_ns: u128,
    phases: EncodePhases,
) {
    println!("{{\"format\":\"{}\",\"model_bytes\":{},\"rank_bits\":{},\"rank_bytes\":{},\"total_bytes\":{},\"local_count\":{},\"model_construct_ns\":{},\"count_ns\":{},\"rank_ns\":{},\"portfolioencode_ns\":{},\"wire_construct_ns\":{},\"model_compile_ns\":{},\"cardinality_ns\":{},\"symbol_rank_ns\":{},\"internal_decode_ns\":{}}}",format,model,bits,rank_bytes,total,local,construct,count,portfolio_encode,portfolio_encode,phases.wire_construct_ns,phases.model_compile_ns,phases.cardinality_ns,phases.symbol_rank_ns,decode_ns);
}

fn kind_name(kind: Kind) -> &'static str {
    match kind {
        Kind::Raw => "raw",
        Kind::Subset => "subset",
        Kind::Bitset => "bitset",
        Kind::Rle => "rle",
        Kind::Flat => "flat",
        Kind::PackedFlat => "packed-flat",
        Kind::Shared => "shared",
        Kind::Bdd => "bdd",
        Kind::Auto => "auto",
    }
}

/// Checks the single applicability condition shared by every structural wire.
/// This makes auto's raw fallback explicit rather than treating route failures as
/// a source of selection information.
fn structural_eligible(data: &[u8], b: usize, atoms: &[Atom]) -> Result<(), String> {
    let symbols = alphabet(data).ok_or_else(|| fail("input does not have two observed symbols"))?;
    if data.is_empty() || data.len() % b != 0 {
        return Err(fail(
            "input is empty or does not align to the supplied bit width",
        ));
    }
    let members = table(b, atoms);
    if members.is_empty() {
        return Err(fail("supplied exact model set is empty"));
    }
    for chunk in data.chunks_exact(b) {
        if members.binary_search(&word(chunk, symbols)).is_err() {
            return Err(fail("input is outside the supplied exact model"));
        }
    }
    Ok(())
}

fn observed_words(data: &[u8], b: usize, symbols: [u8; 2]) -> Vec<u16> {
    data.chunks_exact(b)
        .map(|chunk| word(chunk, symbols))
        .collect()
}

/// The primitive bank is deliberately small and fixed.  It derives constraints
/// only from complete records, never from input names or external model assets.
fn discover_atoms(b: usize, words: &[u16]) -> Result<Vec<Atom>, String> {
    if words.is_empty() {
        return Err(fail("discovery needs at least one record"));
    }
    let full = (1u16 << b) - 1;
    let counts: Vec<u8> = words
        .iter()
        .map(|value| (value & full).count_ones() as u8)
        .collect();
    let mut atoms = Vec::new();
    let exact_count = counts.iter().all(|&count| count == counts[0]);
    if exact_count {
        atoms.push(Atom {
            op: 0,
            mask: full,
            param: counts[0],
        });
    } else {
        let maximum = *counts.iter().max().unwrap();
        if maximum < b as u8 {
            atoms.push(Atom {
                op: 1,
                mask: full,
                param: maximum,
            });
        }
    }
    let parities: Vec<u8> = counts.iter().map(|count| count & 1).collect();
    if !exact_count && parities.iter().all(|&parity| parity == parities[0]) {
        atoms.push(Atom {
            op: 2,
            mask: full,
            param: parities[0],
        });
    }
    let endpoint = |value: u16| ((value & 1) ^ ((value >> (b - 1)) & 1)) as u8;
    let endpoint_value = endpoint(words[0]);
    if words.iter().all(|&value| endpoint(value) == endpoint_value) {
        atoms.push(Atom {
            op: 3,
            mask: full,
            param: endpoint_value,
        });
    }
    for low in 0..b - 1 {
        let mask = (1u16 << low) | (1u16 << (low + 1));
        if b == 2 && mask == full {
            continue;
        }
        let value = (((words[0] >> low) ^ (words[0] >> (low + 1))) & 1) as u8;
        if words
            .iter()
            .all(|&word| (((word >> low) ^ (word >> (low + 1))) & 1) as u8 == value)
        {
            atoms.push(Atom {
                op: 3,
                mask,
                param: value,
            });
        }
    }
    normalize(b, &mut atoms)?;
    // A stable, repeated left-to-right pass removes only atoms whose absence
    // leaves the exact enumerated local space unchanged.
    let mut index = 0;
    while index < atoms.len() {
        let exact = table(b, &atoms);
        let mut without = atoms.clone();
        without.remove(index);
        if table(b, &without) == exact {
            atoms = without;
        } else {
            index += 1;
        }
    }
    Ok(atoms)
}

fn timing_discover(
    archive: &[u8],
    bits: usize,
    local: usize,
    phases: EncodePhases,
    portfolio_encode_ns: u128,
    internal_decode_ns: u128,
    selected_b: usize,
    discovery_ns: u128,
    atoms: &[Atom],
    candidate_count: usize,
) {
    let model_len = u16::from_le_bytes(archive[13..15].try_into().unwrap()) as usize;
    let atom_json = atoms
        .iter()
        .map(|atom| format!("[{}, {}, {}]", atom.op, atom.mask, atom.param))
        .collect::<Vec<_>>()
        .join(",");
    println!("{{\"format\":\"{}\",\"model_bytes\":{},\"rank_bits\":{},\"rank_bytes\":{},\"total_bytes\":{},\"local_count\":{},\"model_construct_ns\":0,\"count_ns\":0,\"rank_ns\":{},\"portfolioencode_ns\":{},\"wire_construct_ns\":{},\"model_compile_ns\":{},\"cardinality_ns\":{},\"symbol_rank_ns\":{},\"internal_decode_ns\":{},\"selectedb\":{},\"discovery_ns\":{},\"selectedatoms\":[{}],\"candidatecount\":{}}}",kind_name(match archive[5] { 0 => Kind::Raw, 1 => Kind::Subset, 2 => Kind::Bitset, 3 => Kind::Rle, 4 => Kind::Flat, 5 => Kind::PackedFlat, 6 => Kind::Shared, 7 => Kind::Bdd, _ => unreachable!() }),model_len,bits,bits.div_ceil(8),archive.len(),local,portfolio_encode_ns,portfolio_encode_ns,phases.wire_construct_ns,phases.model_compile_ns,phases.cardinality_ns,phases.symbol_rank_ns,internal_decode_ns,selected_b,discovery_ns,atom_json,candidate_count);
}

fn discover(
    data: &[u8],
) -> Result<
    (
        Vec<u8>,
        usize,
        usize,
        EncodePhases,
        usize,
        Vec<Atom>,
        usize,
        u128,
        u128,
    ),
    String,
> {
    let discovery_start = Instant::now();
    let symbols = match alphabet(data) {
        Some(symbols) => symbols,
        None => {
            let discovery_ns = discovery_start.elapsed().as_nanos();
            let portfolio_start = Instant::now();
            let (archive, bits, local, phases) = make(Kind::Raw, data, 2, &[])?;
            return Ok((
                archive,
                bits,
                local,
                phases,
                0,
                Vec::new(),
                1,
                discovery_ns,
                portfolio_start.elapsed().as_nanos(),
            ));
        }
    };
    let mut models = Vec::new();
    for b in 2..=12 {
        if data.is_empty() || data.len() % b != 0 {
            continue;
        }
        let words = observed_words(data, b, symbols);
        models.push((b, discover_atoms(b, &words)?));
    }
    let discovery_ns = discovery_start.elapsed().as_nanos();
    let portfolio_start = Instant::now();
    let mut best = make(Kind::Raw, data, 2, &[])?;
    let mut best_b = 0usize;
    let mut best_atoms = Vec::new();
    let mut candidates = 1usize;
    for (b, atoms) in models {
        for kind in [
            Kind::Subset,
            Kind::Bitset,
            Kind::Rle,
            Kind::Flat,
            Kind::PackedFlat,
            Kind::Shared,
            Kind::Bdd,
        ] {
            let candidate = make(kind, data, b, &atoms)?;
            candidates += 1;
            if candidate.0.len() < best.0.len() {
                best = candidate;
                best_b = b;
                best_atoms = atoms.clone();
            }
        }
    }
    let portfolio_encode_ns = portfolio_start.elapsed().as_nanos();
    Ok((
        best.0,
        best.1,
        best.2,
        best.3,
        best_b,
        best_atoms,
        candidates,
        discovery_ns,
        portfolio_encode_ns,
    ))
}

fn main() -> Result<(), String> {
    let a: Vec<String> = env::args().collect();
    match a.get(1).map(String::as_str) {
        Some("discover") if a.len() == 4 => {
            let data = bounded(&a[2], MAX_N)?;
            let (archive, bits, local, phases, selected_b, atoms, candidate_count, discovery_ns, portfolio_encode_ns) = discover(&data)?;
            let decode_start = Instant::now();
            if decode(&archive)? != data {
                return Err(fail("internal decode mismatch"));
            }
            let internal_decode_ns = decode_start.elapsed().as_nanos();
            fs::write(&a[3], &archive).map_err(|e| e.to_string())?;
            timing_discover(
                &archive,
                bits,
                local,
                phases,
                portfolio_encode_ns,
                internal_decode_ns,
                selected_b,
                discovery_ns,
                &atoms,
                candidate_count,
            );
            Ok(())
        }
        Some("encode") if a.len() == 6 => {
            let requested = kind_from(&a[2])?;
            let data = bounded(&a[4], MAX_N)?;
            let model_start = Instant::now();
            // Raw has no model metadata and deliberately accepts every bounded byte input.
            let (b, atoms) = if requested == Kind::Raw {
                (2, Vec::new())
            } else {
                let model_text = bounded(&a[3], 4096)?;
                parse_text(&model_text)?
            };
            let construct = model_start.elapsed().as_nanos();
            let count_start = Instant::now();
            if requested != Kind::Raw && !data.is_empty() && data.len() % b == 0 {
                let members = table(b, &atoms);
                let _global_cardinality = power(members.len(), data.len() / b);
            }
            let count = count_start.elapsed().as_nanos();

            let rank_start = Instant::now();
            let mut choices = vec![requested];
            if requested == Kind::Auto {
                choices = vec![Kind::Raw];
                match structural_eligible(&data, b, &atoms) {
                    Ok(()) => choices.extend([
                        Kind::Subset,
                        Kind::Bitset,
                        Kind::Rle,
                        Kind::Flat,
                        Kind::PackedFlat,
                        Kind::Shared,
                        Kind::Bdd,
                    ]),
                    Err(reason) => eprintln!(
                        "{{\"auto_status\":\"raw-only\",\"class\":\"unsupported\",\"reason\":\"{}\"}}",
                        reason
                    ),
                }
            } else if requested != Kind::Raw {
                structural_eligible(&data, b, &atoms)?;
            }

            let mut best: Option<(Vec<u8>, usize, usize, Kind, EncodePhases)> = None;
            for kind in choices {
                match make(kind, &data, b, &atoms) {
                    Ok((archive, bits, local_count, phases)) => {
                        if best
                            .as_ref()
                            .map_or(true, |(old, _, _, _, _)| archive.len() < old.len())
                        {
                            best = Some((archive, bits, local_count, kind, phases));
                        }
                    }
                    Err(reason) if requested == Kind::Auto && reason.contains("bound") => {
                        eprintln!(
                            "{{\"auto_status\":\"candidate-skipped\",\"class\":\"size\",\"kind\":\"{}\",\"reason\":\"{}\"}}",
                            kind_name(kind), reason
                        );
                    }
                    Err(reason) => {
                        eprintln!(
                            "{{\"auto_status\":\"candidate-failed\",\"class\":\"unexpected\",\"kind\":\"{}\",\"reason\":\"{}\"}}",
                            kind_name(kind), reason
                        );
                        return Err(format!("{} candidate failed: {}", kind_name(kind), reason));
                    }
                }
            }
            let rank_ns = rank_start.elapsed().as_nanos();
            let (archive, bits, local_count, chosen, phases) =
                best.ok_or_else(|| fail("no applicable complete representation"))?;
            let decode_start = Instant::now();
            if decode(&archive)? != data {
                return Err(fail("internal decode mismatch"));
            }
            let internal = decode_start.elapsed().as_nanos();
            fs::write(&a[5], &archive).map_err(|e| e.to_string())?;
            let model_len = u16::from_le_bytes(archive[13..15].try_into().unwrap()) as usize;
            timing(
                kind_name(chosen), model_len, bits, bits.div_ceil(8), archive.len(), local_count,
                construct, count, rank_ns, internal, phases,
            );
            Ok(())
        }
        Some("decode") if a.len() == 4 => {
            let arc = bounded(&a[2], MAX_ARCHIVE)?;
            let start = Instant::now();
            let (out, phases) = decode_with_phases(&arc)?;
            fs::write(&a[3], out).map_err(|e| e.to_string())?;
            eprintln!(
                "{{\"model_compile_ns\":{},\"cardinality_ns\":{},\"unrank_ns\":{},\"decode_ns\":{}}}",
                phases.model_compile_ns,
                phases.cardinality_ns,
                phases.unrank_ns,
                start.elapsed().as_nanos()
            );
            Ok(())
        }
        _ => Err(fail("usage: model_descriptions encode KIND MODEL INPUT ARCHIVE | model_descriptions discover INPUT ARCHIVE | model_descriptions decode ARCHIVE OUT")),
    }
}
