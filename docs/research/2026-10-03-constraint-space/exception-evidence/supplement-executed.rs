//! Isolated, input-only exact-record exception experiment; no production integration.
use num_bigint::BigUint;
use num_traits::{One, Zero};
use std::{env, fs, io::Read, time::Instant};

const MAX_N: usize = 16_384;
const MAX_ARCHIVE: usize = 30_000;
const HEADER: usize = 31;

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
#[derive(Clone, Copy)]
struct Model {
    b: usize,
    mask: u16,
    count: Count,
    param: u8,
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
    let mut out = vec![0; k];
    let mut up = n;
    for i in (1..=k).rev() {
        let (mut lo, mut hi) = (i - 1, up);
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
            return Err(fail("map rank"));
        }
        rank -= t;
        out[i - 1] = lo;
        up = lo;
    }
    if !rank.is_zero() || out.windows(2).any(|x| x[0] >= x[1]) {
        Err(fail("map rank"))
    } else {
        Ok(out)
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
    sy: [u8; 2],
    r: usize,
    e: usize,
    ml: usize,
    pl: usize,
    xl: usize,
) -> Vec<u8> {
    let mut x = b"REX1".to_vec();
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
    let mut x = header(Kind::Raw, d.len(), m, [0, 0], 0, 0, 0, d.len(), 0);
    x.extend(d);
    x.extend(crc(&x).to_le_bytes());
    x
}
fn build(d: &[u8], sy: [u8; 2], m: Model) -> Result<Vec<u8>, String> {
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
    let map_card = choose(r, e);
    let map = pack(&colex_rank(&bad), width(&map_card))?;
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
    if d.len() < HEADER + 4 || d.len() > MAX_ARCHIVE || &d[..4] != b"REX1" {
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
    let ml = u16::from_le_bytes(d[25..27].try_into().unwrap()) as usize;
    let pl = u16::from_le_bytes(d[27..29].try_into().unwrap()) as usize;
    let xl = u16::from_le_bytes(d[29..31].try_into().unwrap()) as usize;
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
    let mc = choose(r, e);
    let pc = power(t.len(), r - e);
    if ml != width(&mc).div_ceil(8) || pl != width(&pc).div_ceil(8) || xl != (e * b).div_ceil(8) {
        return Err(fail("noncanonical lengths"));
    }
    let map_rank = unpack(&body[..ml], width(&mc))?;
    if map_rank >= mc {
        return Err(fail("map rank range"));
    }
    let positions = colex_unrank(map_rank, r, e)?;
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
// Exact final wire length, without computing any member rank. This permits
// safe pruning against the incumbent; both rank widths are exact cardinalities.
fn final_cost(d: &[u8], sy: [u8; 2], m: Model) -> Option<usize> {
    let t = table(m);
    if t.is_empty() {
        return None;
    }
    let r = d.len() / m.b;
    let e = d
        .chunks_exact(m.b)
        .filter(|c| t.binary_search(&word(c, sy)).is_err())
        .count();
    Some(
        HEADER
            + 4
            + width(&choose(r, e)).div_ceil(8)
            + width(&power(t.len(), r - e)).div_ceil(8)
            + (m.b * e).div_ceil(8),
    )
}
fn main() -> Result<(), String> {
    let a: Vec<String> = env::args().collect();
    match a.get(1).map(String::as_str) {
        Some("encode") if a.len() == 4 => {
            let data = bounded(&a[2], MAX_N)?;
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
                        let Some(cost) = final_cost(&data, symbols, model) else {
                            continue;
                        };
                        if cost >= best.len() {
                            continue;
                        }
                        let candidate = build(&data, symbols, model)?;
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
            fs::write(&a[3], &best).map_err(|e| e.to_string())?;
            let structural = selected.is_some();
            let b = selected.map_or(0, |model| model.b);
            println!(
                "{{\"format\":\"{}\",\"bytes\":{},\"model_bytes\":{},\"framing_bytes\":{},\"b\":{},\"r\":{},\"e\":{},\"mask\":{},\"mode\":{},\"param\":{},\"map_bytes\":{},\"payload_bytes\":{},\"exception_bytes\":{},\"discovery_ns\":{},\"candidates\":{}}}",
                if structural { "exceptions" } else { "raw" }, best.len(),
                if structural { 5 } else { 0 }, if structural { HEADER + 4 - 5 } else { HEADER + 4 }, b,
                if structural { u32::from_le_bytes(best[13..17].try_into().unwrap()) } else { 0 },
                if structural { u32::from_le_bytes(best[17..21].try_into().unwrap()) } else { 0 },
                if structural { u16::from_le_bytes(best[21..23].try_into().unwrap()) } else { 0 },
                if structural { best[23] } else { 0 }, if structural { best[24] } else { 0 },
                u16::from_le_bytes(best[25..27].try_into().unwrap()),
                u16::from_le_bytes(best[27..29].try_into().unwrap()),
                u16::from_le_bytes(best[29..31].try_into().unwrap()), discovery_ns, candidates
            );
            Ok(())
        }
        Some("decode") if a.len() == 4 => {
            let archive = bounded(&a[2], MAX_ARCHIVE)?;
            let output = decode(&archive)?;
            fs::write(&a[3], output).map_err(|e| e.to_string())
        }
        _ => Err(fail(
            "usage: record_exceptions encode INPUT ARCHIVE | record_exceptions decode ARCHIVE OUT",
        )),
    }
}

// Append this tail verbatim to executed-record_exceptions.rs before `rustc --test`.
// It is a forced-model mechanical-accounting supplement, not discovery evidence.

#[test]
fn supplement_forced_exception_accounting() -> Result<(), String> {
    use std::path::Path;

    const ROOT: &str = "benchmark-work/record-exceptions/supplement";
    let root = Path::new(ROOT);
    fs::create_dir_all(root).map_err(|error| error.to_string())?;
    let model = Model {
        b: 6,
        mask: 1,
        count: Count::Exact,
        param: 3,
    };
    let symbols = [0u8, 1u8];
    let valid = table(model);
    if valid.len() != 8 {
        return Err(fail("supplement expected eight valid words"));
    }

    let write_case = |name: &str,
                      input: Vec<u8>,
                      archive: Vec<u8>,
                      expected_e: usize,
                      expected_len: Option<usize>|
     -> Result<(), String> {
        if decode(&archive)? != input {
            return Err(fail("supplement decode"));
        }
        let observed_e = if archive[5] == Kind::Exceptions as u8 {
            u32::from_le_bytes(archive[17..21].try_into().unwrap()) as usize
        } else {
            0
        };
        if observed_e != expected_e || expected_len.is_some_and(|length| archive.len() != length) {
            return Err(fail("supplement accounting"));
        }
        fs::write(root.join(format!("{name}.input")), &input).map_err(|error| error.to_string())?;
        fs::write(root.join(format!("{name}.rex")), &archive).map_err(|error| error.to_string())?;
        println!(
            "supplement case={name} bytes={} e={observed_e}",
            archive.len()
        );
        Ok(())
    };
    let words_to_bytes = |words: &[u16]| -> Vec<u8> {
        words
            .iter()
            .flat_map(|&word| (0..6).map(move |bit| symbols[((word >> (5 - bit)) & 1) as usize]))
            .collect()
    };
    let cyclic = |records: usize| -> Vec<u16> {
        (0..records)
            .map(|index| valid[index % valid.len()])
            .collect()
    };
    let invalid = |word: u16| -> u16 { word ^ (1 << 5) };

    let empty = Vec::new();
    write_case("empty-raw", empty.clone(), raw(&empty), 0, None)?;

    let e0_words = cyclic(16);
    let e0_input = words_to_bytes(&e0_words);
    write_case(
        "e0",
        e0_input.clone(),
        build(&e0_input, symbols, model)?,
        0,
        None,
    )?;

    let all_words: Vec<u16> = cyclic(16).into_iter().map(invalid).collect();
    let all_input = words_to_bytes(&all_words);
    write_case(
        "e-all",
        all_input.clone(),
        build(&all_input, symbols, model)?,
        16,
        None,
    )?;

    let mut first_words = cyclic(16);
    first_words[0] = invalid(first_words[0]);
    let first_input = words_to_bytes(&first_words);
    write_case(
        "e-first",
        first_input.clone(),
        build(&first_input, symbols, model)?,
        1,
        None,
    )?;

    let mut last_words = cyclic(16);
    let last = last_words.len() - 1;
    last_words[last] = invalid(last_words[last]);
    let last_input = words_to_bytes(&last_words);
    write_case(
        "e-last",
        last_input.clone(),
        build(&last_input, symbols, model)?,
        1,
        None,
    )?;

    for (name, exceptions, expected_len) in [
        ("weak-r2048-e269", 269usize, 1048usize),
        ("weak-r2048-e270", 270usize, 1049usize),
    ] {
        let mut words = cyclic(2048);
        for word in words.iter_mut().take(exceptions) {
            *word = invalid(*word);
        }
        let input = words_to_bytes(&words);
        write_case(
            name,
            input.clone(),
            build(&input, symbols, model)?,
            exceptions,
            Some(expected_len),
        )?;
    }
    Ok(())
}
