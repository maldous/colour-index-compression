//! NCSL v2 lane-mask refinement.  It remains a bounded standalone experiment.
use cix_native::{adaptive, huffman, legacy_lz};
use std::{
    env,
    fs::{self, File},
    io::Read,
    time::Instant,
};

const MAGIC: &[u8; 4] = b"NCSL";
const V1: u8 = 1;
const V2: u8 = 2;
const HEADER: usize = 17;
const META: usize = 9;
const MAX_N: usize = 4096;
const MAX_A: usize = 32768;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
enum Route {
    Raw = 0,
    Huffman = 1,
    Adaptive = 2,
    LegacyLz = 3,
}
impl Route {
    fn get(id: u8) -> Result<Self, String> {
        match id {
            0 => Ok(Self::Raw),
            1 => Ok(Self::Huffman),
            2 => Ok(Self::Adaptive),
            3 => Ok(Self::LegacyLz),
            _ => Err("unknown NCSL route".into()),
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
    count: usize,
    payload: Vec<u8>,
    residual: bool,
}
struct Candidate {
    stride: usize,
    mask: u8,
    bytes: usize,
    lanes: Vec<Lane>,
}

fn crc(data: &[u8]) -> u32 {
    let mut c = !0u32;
    for &b in data {
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
fn enc(r: Route, x: &[u8]) -> Result<Vec<u8>, String> {
    match r {
        Route::Raw => Ok(x.to_vec()),
        Route::Huffman => huffman::encode(x).map_err(|e| e.to_string()),
        Route::Adaptive => adaptive::encode_general(x, 0, 8, &[], 1),
        Route::LegacyLz => Ok(legacy_lz::encode(x, &[], 1)?.payload),
    }
}
fn dec(r: Route, p: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let out = match r {
        Route::Raw => {
            if p.len() != n {
                return Err("raw lane length".into());
            }
            p.to_vec()
        }
        Route::Huffman => {
            if p.len() < 19 || p[0] != huffman::VERSION {
                return Err("invalid Huffman lane".into());
            }
            if u64::from_le_bytes(p[3..11].try_into().map_err(|_| "invalid Huffman length")?)
                != n as u64
            {
                return Err("Huffman lane length".into());
            }
            huffman::decode(p).map_err(|e| e.to_string())?
        }
        Route::Adaptive => adaptive::decode_general(p, n, &[], 1)?,
        Route::LegacyLz => legacy_lz::decode(p, n, &[], 4096)?,
    };
    if out.len() != n {
        Err("lane decoded length".into())
    } else {
        Ok(out)
    }
}
fn column(input: &[u8], stride: usize, offset: usize, residual: bool) -> Vec<u8> {
    let mut x = Vec::new();
    for i in (offset..input.len()).step_by(stride) {
        x.push(if residual {
            input[i].wrapping_sub(input[i - 1])
        } else {
            input[i]
        });
    }
    x
}
fn route_best(x: &[u8], residual: bool) -> Result<Lane, String> {
    let mut best = None;
    for route in [Route::Raw, Route::Huffman, Route::Adaptive, Route::LegacyLz] {
        let trial = Lane {
            route,
            count: x.len(),
            payload: enc(route, x)?,
            residual,
        };
        if best.as_ref().map_or(true, |old: &Lane| {
            (trial.payload.len(), trial.route) < (old.payload.len(), old.route)
        }) {
            best = Some(trial);
        }
    }
    best.ok_or("no fixed lane route".into())
}
fn choices(
    input: &[u8],
    stride: usize,
    need_delta: bool,
) -> Result<Vec<(Lane, Option<Lane>)>, String> {
    let mut all = Vec::with_capacity(stride);
    for offset in 0..stride {
        let identity = route_best(&column(input, stride, offset, false), false)?;
        let delta = if offset == 0 || !need_delta {
            None
        } else {
            Some(route_best(&column(input, stride, offset, true), true)?)
        };
        all.push((identity, delta));
    }
    Ok(all)
}
fn from_choices(stride: usize, choices: &[(Lane, Option<Lane>)], automatic: bool) -> Candidate {
    let mut mask = 0u8;
    let mut lanes = Vec::with_capacity(stride);
    for (k, (identity, delta)) in choices.iter().enumerate() {
        let selected = if automatic && k > 0 {
            let d = delta.as_ref().expect("delta choice");
            if (d.payload.len(), true, d.route) < (identity.payload.len(), false, identity.route) {
                d.clone()
            } else {
                identity.clone()
            }
        } else {
            identity.clone()
        };
        if selected.residual {
            mask |= 1 << k;
        }
        lanes.push(selected);
    }
    Candidate {
        stride,
        mask,
        bytes: HEADER
            + lanes
                .iter()
                .map(|lane| META + lane.payload.len())
                .sum::<usize>(),
        lanes,
    }
}
fn oracle_gap(choices: &[(Lane, Option<Lane>)], selected: &Candidate) -> usize {
    let mut best = usize::MAX;
    for suffix in 0usize..(1usize << choices.len().saturating_sub(1)) {
        let mut cost = HEADER;
        for (k, (identity, delta)) in choices.iter().enumerate() {
            let residual = k > 0 && suffix & (1 << (k - 1)) != 0;
            cost += META
                + if residual {
                    delta.as_ref().expect("delta oracle").payload.len()
                } else {
                    identity.payload.len()
                };
        }
        best = best.min(cost);
    }
    selected.bytes - best
}
fn params(policy: &str, n: usize) -> Result<Vec<(usize, bool)>, String> {
    let limit = n.clamp(1, 8);
    Ok(match policy {
        "auto" => (1..=limit).map(|s| (s, true)).collect(),
        "shuffle" => (1..=limit).map(|s| (s, false)).collect(),
        "whole" => vec![(1, false)],
        _ => return Err("policy must be auto, shuffle, or whole".into()),
    })
}
fn pack(input: &[u8], c: &Candidate) -> Result<Vec<u8>, String> {
    let count = c.lanes.len();
    if input.is_empty() {
        if c.stride != 1 || c.mask != 0 || count != 0 {
            return Err("noncanonical empty NCSL".into());
        }
    } else if c.stride > input.len() || count != c.stride {
        return Err("invalid lane candidate".into());
    }
    let mut a = Vec::with_capacity(c.bytes);
    a.extend_from_slice(MAGIC);
    a.push(V2);
    a.extend_from_slice(&(input.len() as u32).to_le_bytes());
    a.extend_from_slice(&crc(input).to_le_bytes());
    a.push(c.stride as u8);
    a.push(c.mask);
    a.extend_from_slice(&(count as u16).to_le_bytes());
    for lane in &c.lanes {
        a.push(lane.route as u8);
        a.extend_from_slice(&(lane.count as u32).to_le_bytes());
        a.extend_from_slice(&(lane.payload.len() as u32).to_le_bytes());
        a.extend_from_slice(&lane.payload);
    }
    if a.len() != c.bytes || a.len() > MAX_A {
        Err("archive exceeds bound".into())
    } else {
        Ok(a)
    }
}
fn u32at(a: &[u8], p: &mut usize) -> Result<usize, String> {
    let e = p.checked_add(4).ok_or("u32 offset")?;
    let x = a.get(*p..e).ok_or("truncated u32")?;
    *p = e;
    Ok(u32::from_le_bytes(x.try_into().map_err(|_| "invalid u32")?) as usize)
}
fn header_mask(version: u8, field: u8, stride: usize) -> Result<u8, String> {
    match version {
        V1 => {
            if field > 1 || (field == 1 && stride == 1) {
                Err("invalid v1 transform".into())
            } else if field == 0 {
                Ok(0)
            } else {
                Ok(((1u16 << stride) - 2) as u8)
            }
        }
        V2 => {
            if field & 1 != 0 || field as usize >> stride != 0 {
                Err("invalid v2 mask".into())
            } else {
                Ok(field)
            }
        }
        _ => Err("invalid NCSL version".into()),
    }
}
fn unpack(a: &[u8]) -> Result<Vec<u8>, String> {
    if a.len() < HEADER || a.len() > MAX_A || a.get(..4) != Some(MAGIC) {
        return Err("invalid NCSL header".into());
    }
    let version = a[4];
    let mut p = 5;
    let n = u32at(a, &mut p)?;
    let expected_crc = u32at(a, &mut p)? as u32;
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
    if n > MAX_N || !(1..=8).contains(&stride) {
        return Err("invalid NCSL bounds".into());
    }
    let mask = header_mask(version, field, stride)?;
    if n == 0 {
        if stride != 1 || mask != 0 || count != 0 {
            return Err("noncanonical empty NCSL".into());
        }
    } else if stride > n || count != stride {
        return Err("invalid NCSL lane count".into());
    }
    let mut lanes = Vec::with_capacity(count);
    for k in 0..count {
        let route = Route::get(*a.get(p).ok_or("truncated route")?)?;
        p += 1;
        let z = u32at(a, &mut p)?;
        let plen = u32at(a, &mut p)?;
        let want = (n - k).div_ceil(stride);
        if z != want || z > MAX_N {
            return Err("invalid lane length".into());
        }
        let e = p.checked_add(plen).ok_or("payload offset")?;
        let payload = a.get(p..e).ok_or("truncated lane payload")?;
        let y = dec(route, payload, z)?;
        if y.len() != z {
            return Err("lane result length".into());
        }
        p = e;
        lanes.push(y);
    }
    if p != a.len() {
        return Err("trailing NCSL bytes".into());
    }
    let mut out = vec![0u8; n];
    for (k, lane) in lanes.iter().enumerate() {
        for (row, &x) in lane.iter().enumerate() {
            let i = row * stride + k;
            out[i] = if mask & (1 << k) != 0 {
                x.wrapping_add(out[i - 1])
            } else {
                x
            };
        }
    }
    if crc(&out) != expected_crc {
        Err("NCSL source CRC".into())
    } else {
        Ok(out)
    }
}
fn encode(policy: &str, input_path: &str, archive_path: &str) -> Result<(), String> {
    let input = read(input_path, MAX_N, "input")?;
    let start = Instant::now();
    let mut candidates = Vec::new();
    let mut oracle_max = if input.len() <= 12 {
        Some(0usize)
    } else {
        None
    };
    for (stride, automatic) in params(policy, input.len())? {
        let c = if input.is_empty() {
            Candidate {
                stride: 1,
                mask: 0,
                bytes: HEADER,
                lanes: Vec::new(),
            }
        } else {
            let cached = choices(&input, stride, automatic || input.len() <= 12)?;
            let c = from_choices(stride, &cached, automatic);
            if input.len() <= 12 {
                let gap = oracle_gap(&cached, &c);
                oracle_max = Some(oracle_max.unwrap_or(0usize).max(gap));
            }
            c
        };
        candidates.push(c);
    }
    let selected = candidates
        .iter()
        .min_by_key(|c| (c.bytes, c.stride, c.mask))
        .ok_or("no candidates")?;
    let archive = pack(&input, selected)?;
    let elapsed = start.elapsed().as_nanos();
    if unpack(&archive)? != input {
        return Err("in-process restoration mismatch".into());
    }
    fs::write(archive_path, &archive).map_err(|e| format!("archive write: {e}"))?;
    print!("{{\"source_bytes\":{},\"archive_bytes\":{},\"search_elapsed_ns\":{},\"max_mask_oracle_gap_bytes\":", input.len(), archive.len(), elapsed);
    match oracle_max {
        Some(value) => print!("{value}"),
        None => print!("null"),
    };
    print!(",\"candidates\":[");
    for (i, c) in candidates.iter().enumerate() {
        if i != 0 {
            print!(",");
        }
        print!(
            "{{\"stride\":{},\"mask\":{},\"complete_bytes\":{}}}",
            c.stride, c.mask, c.bytes
        );
    }
    print!(
        "],\"selected_stride\":{},\"selected_mask\":{},\"lanes\":[",
        selected.stride, selected.mask
    );
    let mut archive_offset = HEADER;
    for (input_offset, lane) in selected.lanes.iter().enumerate() {
        if input_offset != 0 {
            print!(",");
        }
        let total = META + lane.payload.len();
        print!("{{\"archive_offset\":{},\"input_offset\":{},\"stride\":{},\"count\":{},\"residual\":{},\"route\":\"{}\",\"metadata_bytes\":9,\"payload_bytes\":{},\"total_bytes\":{}}}", archive_offset, input_offset, selected.stride, lane.count, lane.residual, lane.route.name(), lane.payload.len(), total);
        archive_offset += total;
    }
    println!("]}}");
    Ok(())
}
fn decode(archive_path: &str, output_path: &str) -> Result<(), String> {
    let start = Instant::now();
    let out = unpack(&read(archive_path, MAX_A, "archive")?)?;
    fs::write(output_path, &out).map_err(|e| format!("output write: {e}"))?;
    println!(
        "{{\"restored_bytes\":{},\"decode_elapsed_ns\":{}}}",
        out.len(),
        start.elapsed().as_nanos()
    );
    Ok(())
}
fn run() -> Result<(), String> {
    let a: Vec<String> = env::args().skip(1).collect();
    match a.as_slice() { [op, flag, policy, input, archive] if op == "encode" && flag == "--policy" => encode(policy, input, archive), [op, archive, output] if op == "decode" => decode(archive, output), _ => Err("usage: segmentation_lane_masks encode --policy auto|shuffle|whole INPUT ARCHIVE | segmentation_lane_masks decode ARCHIVE OUT".into()) }
}
fn main() {
    if let Err(e) = run() {
        eprintln!("segmentation_lane_masks: {e}");
        std::process::exit(1);
    }
}
