//! Bounded latent-layout representation experiment; no production integration.
use cix_native::{adaptive, huffman, legacy_lz};
use std::{
    env,
    ffi::{c_int, c_uint, c_void},
    fs::{self, File},
    io::Read,
    time::Instant,
};
const M: &[u8; 4] = b"LLT1";
const V: u8 = 1;
const H: usize = 18;
const N: usize = 4096;
const A: usize = 32768;
#[link(name = "zstd")]
unsafe extern "C" {
    fn ZSTD_compressBound(n: usize) -> usize;
    fn ZSTD_compress(d: *mut c_void, dc: usize, s: *const c_void, sc: usize, l: c_int) -> usize;
    fn ZSTD_decompress(d: *mut c_void, dc: usize, s: *const c_void, sc: usize) -> usize;
    fn ZSTD_findFrameCompressedSize(s: *const c_void, n: usize) -> usize;
    fn ZSTD_getFrameHeader(h: *mut FrameHeader, s: *const c_void, n: usize) -> usize;
    fn ZSTD_isError(x: usize) -> c_uint;
}
#[repr(C)]
struct FrameHeader {
    frame_content_size: u64,
    window_size: u64,
    block_size_max: u32,
    frame_type: u32,
    header_size: u32,
    dict_id: u32,
    checksum_flag: u32,
    reserved1: u32,
    reserved2: u32,
}
#[derive(Clone, Copy, Eq, Ord, PartialEq, PartialOrd)]
enum R {
    Raw = 0,
    Huf = 1,
    Ada = 2,
    Lz = 3,
    Zstd = 4,
}
#[derive(Clone)]
struct L {
    op: u8,
    r: R,
    n: usize,
    p: Vec<u8>,
}
#[derive(Clone)]
struct C {
    w: usize,
    phase: usize,
    ops: Vec<u8>,
    global: bool,
    r: Option<R>,
    p: Vec<u8>,
    lanes: Vec<L>,
    bytes: usize,
    tag: &'static str,
}
fn crc(d: &[u8]) -> u32 {
    let mut c = !0u32;
    for &b in d {
        c ^= b as u32;
        for _ in 0..8 {
            c = if c & 1 != 0 {
                c >> 1 ^ 0xedb88320
            } else {
                c >> 1
            }
        }
    }
    !c
}
fn read(path: &str, cap: usize) -> Result<Vec<u8>, String> {
    let m = fs::metadata(path).map_err(|e| e.to_string())?;
    if !m.is_file() || m.len() > cap as u64 {
        return Err("regular input bound".into());
    }
    let f = File::open(path).map_err(|e| e.to_string())?;
    let mut d = Vec::new();
    f.take((cap + 1) as u64)
        .read_to_end(&mut d)
        .map_err(|e| e.to_string())?;
    if d.len() > cap {
        Err("input bound".into())
    } else {
        Ok(d)
    }
}
fn zenc(x: &[u8]) -> Result<Vec<u8>, String> {
    let cap = unsafe { ZSTD_compressBound(x.len()) };
    if unsafe { ZSTD_isError(cap) } != 0 || cap > A - H {
        return Err("zstd bound".into());
    }
    let mut y = vec![0; cap];
    let z = unsafe {
        ZSTD_compress(
            y.as_mut_ptr().cast(),
            y.len(),
            x.as_ptr().cast(),
            x.len(),
            19,
        )
    };
    if unsafe { ZSTD_isError(z) } != 0 || z > y.len() {
        Err("zstd encode".into())
    } else {
        y.truncate(z);
        Ok(y)
    }
}
fn zdec(x: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let f = unsafe { ZSTD_findFrameCompressedSize(x.as_ptr().cast(), x.len()) };
    if unsafe { ZSTD_isError(f) } != 0 || f != x.len() {
        return Err("one zstd frame".into());
    }
    let mut header: FrameHeader = unsafe { std::mem::zeroed() };
    let parsed = unsafe { ZSTD_getFrameHeader(&mut header, x.as_ptr().cast(), x.len()) };
    if unsafe { ZSTD_isError(parsed) } != 0
        || parsed != 0
        || header.frame_content_size != n as u64
        || header.window_size > N as u64
    {
        return Err("zstd frame bounds".into());
    }
    let mut y = vec![0; n];
    let z = unsafe { ZSTD_decompress(y.as_mut_ptr().cast(), y.len(), x.as_ptr().cast(), x.len()) };
    if unsafe { ZSTD_isError(z) } != 0 || z != n {
        Err("zstd length".into())
    } else {
        Ok(y)
    }
}
fn enc(r: R, x: &[u8]) -> Result<Vec<u8>, String> {
    match r {
        R::Raw => Ok(x.to_vec()),
        R::Huf => huffman::encode(x).map_err(|e| e.to_string()),
        R::Ada => adaptive::encode_general(x, 0, 8, &[], 1),
        R::Lz => Ok(legacy_lz::encode(x, &[], 1)?.payload),
        R::Zstd => zenc(x),
    }
}
fn dec(r: R, p: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let y = match r {
        R::Raw => {
            if p.len() != n {
                return Err("raw len".into());
            }
            p.to_vec()
        }
        R::Huf => {
            if p.len() < 19
                || p[0] != huffman::VERSION
                || u64::from_le_bytes(p[3..11].try_into().map_err(|_| "huf")?) != n as u64
            {
                return Err("Huffman bound".into());
            }
            huffman::decode(p).map_err(|e| e.to_string())?
        }
        R::Ada => adaptive::decode_general(p, n, &[], 1)?,
        R::Lz => legacy_lz::decode(p, n, &[], 4096)?,
        R::Zstd => zdec(p, n)?,
    };
    if y.len() != n {
        Err("decoded len".into())
    } else {
        Ok(y)
    }
}
fn valid(n: usize, w: usize, p: usize) -> bool {
    n > 0 && (1..=8).contains(&w) && p < w && p <= n && w <= n - p
}
fn stream(x: &[u8], w: usize, p: usize, j: usize, op: u8) -> Vec<u8> {
    let mut y = Vec::new();
    let mut row = 0;
    let mut i = p + j;
    while i < x.len() {
        let b = if row == 0 || op == 0 {
            x[i]
        } else {
            match op {
                1 => x[i].wrapping_sub(x[i - w]),
                2 => x[i].wrapping_sub(x[i - 1]),
                3 => x[i] ^ x[i - 1],
                4 => x[i] ^ x[i - w],
                _ => x[i],
            }
        };
        y.push(b);
        row += 1;
        i += w;
    }
    y
}
fn counts(n: usize, w: usize, p: usize, j: usize) -> usize {
    if p + j >= n {
        0
    } else {
        (n - (p + j)).div_ceil(w)
    }
}
fn lane(x: &[u8], w: usize, p: usize, j: usize, op: u8) -> Result<L, String> {
    if (op == 2 || op == 3) && j == 0 {
        return Err("previous-lane op on lane zero".into());
    }
    let s = stream(x, w, p, j, op);
    let mut b = None;
    for r in [R::Raw, R::Huf, R::Ada, R::Lz, R::Zstd] {
        let q = enc(r, &s)?;
        let z = L {
            op,
            r,
            n: s.len(),
            p: q,
        };
        if b.as_ref()
            .map_or(true, |old: &L| (z.p.len(), z.r) < (old.p.len(), old.r))
        {
            b = Some(z)
        }
    }
    Ok(b.expect("routes"))
}
fn native(x: &[u8], w: usize, p: usize, ops: Vec<u8>, tag: &'static str) -> Result<C, String> {
    let mut ls = Vec::new();
    for j in 0..w {
        ls.push(lane(x, w, p, j, ops[j])?)
    }
    let b = H + x[..p].len() + ls.iter().map(|l| 10 + l.p.len()).sum::<usize>();
    Ok(C {
        w,
        phase: p,
        ops,
        global: false,
        r: None,
        p: Vec::new(),
        lanes: ls,
        bytes: b,
        tag,
    })
}
fn native_auto(x: &[u8], w: usize, p: usize) -> Result<C, String> {
    let mut lanes = Vec::new();
    let mut ops = Vec::new();
    for j in 0..w {
        let mut best = None;
        for op in 0..=4 {
            if (op == 2 || op == 3) && j == 0 {
                continue;
            }
            let trial = lane(x, w, p, j, op)?;
            if best.as_ref().map_or(true, |old: &L| {
                (trial.p.len(), trial.op, trial.r) < (old.p.len(), old.op, old.r)
            }) {
                best = Some(trial);
            }
        }
        let chosen = best.ok_or("native operator")?;
        ops.push(chosen.op);
        lanes.push(chosen);
    }
    let bytes = H + p + lanes.iter().map(|lane| 10 + lane.p.len()).sum::<usize>();
    Ok(C {
        w,
        phase: p,
        ops,
        global: false,
        r: None,
        p: Vec::new(),
        lanes,
        bytes,
        tag: "native-auto",
    })
}
fn raw_whole(x: &[u8]) -> C {
    C {
        w: 1,
        phase: 0,
        ops: vec![0],
        global: false,
        r: None,
        p: Vec::new(),
        lanes: vec![L {
            op: 0,
            r: R::Raw,
            n: x.len(),
            p: x.to_vec(),
        }],
        bytes: H + 10 + x.len(),
        tag: "raw-whole",
    }
}
fn global(x: &[u8], w: usize, p: usize, ops: Vec<u8>, tag: &'static str) -> Result<C, String> {
    let mut q = x[..p].to_vec();
    for j in 0..w {
        q.extend(stream(x, w, p, j, ops[j]));
    }
    let z = zenc(&q[p..])?;
    Ok(C {
        w,
        phase: p,
        ops,
        global: true,
        r: Some(R::Zstd),
        p: z,
        lanes: Vec::new(),
        bytes: H + p + ops.len() + 4 + z.len(),
        tag,
    })
}
fn uniform(w: usize, op: u8) -> Vec<u8> {
    (0..w)
        .map(|j| {
            if j == 0 && (op == 2 || op == 3) {
                0
            } else {
                op
            }
        })
        .collect()
}
fn pack(x: &[u8], c: &C) -> Result<Vec<u8>, String> {
    let mut a = Vec::new();
    a.extend(M);
    a.push(V);
    a.push(if c.global { 1 } else { 0 });
    a.extend((x.len() as u32).to_le_bytes());
    a.extend(crc(x).to_le_bytes());
    a.push(c.w as u8);
    a.push(c.phase as u8);
    a.push(if c.global {
        c.ops.len() as u8
    } else {
        c.lanes.len() as u8
    });
    a.push(c.phase as u8);
    a.extend(&x[..c.phase]);
    if c.global {
        a.extend(&c.ops);
        a.extend((c.p.len() as u32).to_le_bytes());
        a.extend(&c.p)
    } else {
        for l in &c.lanes {
            a.push(l.op);
            a.push(l.r as u8);
            a.extend((l.n as u32).to_le_bytes());
            a.extend((l.p.len() as u32).to_le_bytes());
            a.extend(&l.p)
        }
    }
    if a.len() != c.bytes || a.len() > A {
        Err("archive bound".into())
    } else {
        Ok(a)
    }
}
fn u32a(a: &[u8], p: &mut usize) -> Result<usize, String> {
    let e = p.checked_add(4).ok_or("offset")?;
    let b = a.get(*p..e).ok_or("trunc")?;
    *p = e;
    Ok(u32::from_le_bytes(b.try_into().map_err(|_| "u32")?) as usize)
}
fn restore(
    n: usize,
    w: usize,
    p: usize,
    ops: &[u8],
    lanes: Vec<Vec<u8>>,
    prefix: &[u8],
) -> Result<Vec<u8>, String> {
    let mut out = prefix.to_vec();
    out.resize(n, 0);
    for row in 0.. {
        let mut any = false;
        for j in 0..w {
            let i = p + row * w + j;
            if i >= n {
                continue;
            }
            any = true;
            let b = *lanes[j].get(row).ok_or("lane row")?;
            out[i] = if row == 0 || ops[j] == 0 {
                b
            } else {
                match ops[j] {
                    1 => b.wrapping_add(out[i - w]),
                    2 => b.wrapping_add(out[i - 1]),
                    3 => b ^ out[i - 1],
                    4 => b ^ out[i - w],
                    _ => return Err("op".into()),
                }
            }
        }
        if !any {
            break;
        }
    }
    Ok(out)
}
fn unpack(a: &[u8]) -> Result<Vec<u8>, String> {
    if a.len() < H || a.len() > A || a.get(..4) != Some(M) || a[4] != V {
        return Err("LLT header".into());
    }
    let global = a[5];
    let mut p = 6;
    let n = u32a(a, &mut p)?;
    let c = u32a(a, &mut p)? as u32;
    let w = *a.get(p).ok_or("w")? as usize;
    p += 1;
    let phase = *a.get(p).ok_or("p")? as usize;
    p += 1;
    let count = *a.get(p).ok_or("count")? as usize;
    p += 1;
    let plen = *a.get(p).ok_or("prefix")? as usize;
    p += 1;
    if n == 0 {
        if w != 1
            || phase != 0
            || count != 0
            || plen != 0
            || global != 0
            || p != a.len()
            || c != crc(&[])
        {
            return Err("empty geometry".into());
        }
        return Ok(Vec::new());
    }
    if n > N || !valid(n, w, phase) || plen != phase {
        return Err("geometry".into());
    }
    let pre = a.get(p..p + plen).ok_or("prefix bytes")?;
    p += plen;
    let (ops, lanes) = if global == 1 {
        if count != w {
            return Err("global operator count".into());
        }
        let oe = p.checked_add(w).ok_or("operator offset")?;
        let ops = a.get(p..oe).ok_or("operators")?.to_vec();
        p = oe;
        for (j, &op) in ops.iter().enumerate() {
            if op > 4 || ((op == 2 || op == 3) && j == 0) {
                return Err("op".into());
            }
        }
        let z = u32a(a, &mut p)?;
        let e = p.checked_add(z).ok_or("z")?;
        let body = zdec(a.get(p..e).ok_or("frame")?, n - phase)?;
        p = e;
        let mut q: usize = 0;
        let mut ls = Vec::new();
        for j in 0..w {
            let z = counts(n, w, phase, j);
            let e = q.checked_add(z).ok_or("split")?;
            ls.push(body.get(q..e).ok_or("body")?.to_vec());
            q = e;
        }
        if q != body.len() {
            return Err("body trail".into());
        }
        (ops, ls)
    } else if global == 0 {
        if count != w {
            return Err("lane count".into());
        };
        let mut ops = Vec::new();
        let mut ls = Vec::new();
        for j in 0..w {
            let op = *a.get(p).ok_or("op")?;
            p += 1;
            let rid = *a.get(p).ok_or("route")?;
            p += 1;
            if op > 4 || ((op == 2 || op == 3) && j == 0) {
                return Err("op".into());
            };
            let z = u32a(a, &mut p)?;
            let q = u32a(a, &mut p)?;
            if z != counts(n, w, phase, j) || z > N {
                return Err("lane count".into());
            };
            let e = p.checked_add(q).ok_or("payload")?;
            ls.push(dec(
                match rid {
                    0 => R::Raw,
                    1 => R::Huf,
                    2 => R::Ada,
                    3 => R::Lz,
                    4 => R::Zstd,
                    _ => return Err("route".into()),
                },
                a.get(p..e).ok_or("payload")?,
                z,
            )?);
            p = e;
            ops.push(op)
        }
        (ops, ls)
    } else {
        return Err("kind".into());
    };
    if p != a.len() {
        return Err("trailing".into());
    };
    let out = restore(n, w, phase, &ops, lanes, pre)?;
    if crc(&out) != c {
        Err("CRC".into())
    } else {
        Ok(out)
    }
}
fn geometries(n: usize, maxw: usize) -> Vec<(usize, usize)> {
    let mut v = Vec::new();
    for w in 1..=maxw {
        for p in 0..w {
            if valid(n, w, p) {
                v.push((w, p))
            }
        }
    }
    v
}
fn oracle(x: &[u8], w: usize, p: usize) -> Result<C, String> {
    let mut best = None;
    let k = w.saturating_sub(1);
    for first in [0, 1, 4] {
        for code in 0..5usize.pow(k as u32) {
            let mut q = code;
            let mut o = vec![first];
            for _ in 0..k {
                o.push((q % 5) as u8);
                q /= 5
            }
            let z = global(x, w, p, o, "oracle")?;
            if best.as_ref().map_or(true, |b: &C| {
                (z.bytes, z.ops.clone()) < (b.bytes, b.ops.clone())
            }) {
                best = Some(z)
            }
        }
    }
    Ok(best.expect("oracle"))
}
fn mask_oracle(x: &[u8], w: usize, p: usize) -> Result<C, String> {
    let mut best = None;
    for bits in 0..(1usize << w.saturating_sub(1)) {
        let mut ops = vec![0u8];
        for lane in 1..w {
            ops.push(if bits & (1 << (lane - 1)) != 0 { 2 } else { 0 });
        }
        let candidate = global(x, w, p, ops, "mask-oracle")?;
        if best.as_ref().map_or(true, |old: &C| {
            (candidate.bytes, candidate.ops.clone()) < (old.bytes, old.ops.clone())
        }) {
            best = Some(candidate);
        }
    }
    Ok(best.expect("mask geometry"))
}
fn encode(policy: &str, input: &str, out: &str) -> Result<(), String> {
    if !["auto", "whole", "bss", "uniform", "oracle", "mask-control"].contains(&policy) {
        return Err("policy".into());
    }
    let x = read(input, N)?;
    if policy == "oracle" && x.len() > 12 {
        return Err("oracle requires n<=12".into());
    }
    if x.is_empty() {
        let c = C {
            w: 1,
            phase: 0,
            ops: vec![0],
            global: false,
            r: None,
            p: vec![],
            lanes: vec![],
            bytes: H,
            tag: "raw",
        };
        let a = pack(&x, &c)?;
        fs::write(out, a).map_err(|e| e.to_string())?;
        println!("{{\"source_bytes\":0,\"archive_bytes\":18,\"raw_fallback\":true}} ");
        return Ok(());
    }
    let st = Instant::now();
    let maxw = if x.len() <= 12 { 3 } else { 8 };
    let mut cs = Vec::new();
    cs.push(raw_whole(&x));
    let mut oracle_global_vectors = 0usize;
    let mut mask_global_vectors = 0usize;
    let gs = if policy == "whole" {
        vec![(1, 0)]
    } else {
        geometries(x.len(), maxw)
    };
    for (w, p) in gs {
        if (policy != "bss" && policy != "uniform" && policy != "mask-control")
            || ((policy == "uniform" || policy == "mask-control") && w == 1 && p == 0)
        {
            let native_candidate = if policy == "auto" || policy == "oracle" {
                native_auto(&x, w, p)?
            } else {
                native(&x, w, p, vec![0; w], "native")?
            };
            if policy == "auto" || policy == "oracle" || policy == "uniform" {
                cs.push(global(
                    &x,
                    w,
                    p,
                    native_candidate.ops.clone(),
                    "native-vector-zstd",
                )?);
            }
            cs.push(native_candidate);
        }
        if policy == "auto" || policy == "oracle" || policy == "uniform" {
            for op in 1..=4 {
                cs.push(global(&x, w, p, uniform(w, op), "global")?)
            }
        }
        cs.push(global(&x, w, p, vec![0; w], "bss")?);
        if policy == "oracle" {
            oracle_global_vectors += 3 * 5usize.pow((w - 1) as u32);
            cs.push(oracle(&x, w, p)?)
        }
        if policy == "mask-control" {
            mask_global_vectors += 1usize << w.saturating_sub(1);
            cs.push(mask_oracle(&x, w, p)?)
        }
    }
    let sel = cs
        .iter()
        .min_by_key(|c| (c.bytes, c.w, c.phase, c.global, c.ops.clone()))
        .ok_or("candidates")?;
    let a = pack(&x, sel)?;
    let ns = st.elapsed().as_nanos();
    if unpack(&a)? != x {
        return Err("inverse".into());
    };
    fs::write(out, &a).map_err(|e| e.to_string())?;
    let raw_fallback = !sel.global
        && sel.w == 1
        && sel.phase == 0
        && sel.ops == [0]
        && sel.lanes.iter().all(|lane| lane.r == R::Raw);
    print!("{{\"source_bytes\":{},\"archive_bytes\":{},\"elapsed_ns\":{},\"retained_entries\":{},\"oracle_global_vectors\":{},\"mask_global_vectors\":{},\"transform_cache\":\"none\",\"candidates\":[",x.len(),a.len(),ns,cs.len(),oracle_global_vectors,mask_global_vectors);
    for (i, candidate) in cs.iter().enumerate() {
        if i != 0 {
            print!(",");
        }
        print!("{{\"tag\":\"{}\",\"kind\":\"{}\",\"backend\":\"{}\",\"width\":{},\"phase\":{},\"operators\":[", candidate.tag, if candidate.global { "global" } else { "lanes" }, if candidate.global { "zstd" } else { "mixed-five-route" }, candidate.w, candidate.phase);
        for (j, op) in candidate.ops.iter().enumerate() {
            if j != 0 {
                print!(",");
            }
            print!("{op}");
        }
        print!("],\"routes\":[");
        if candidate.global {
            print!("4");
        } else {
            for (j, lane) in candidate.lanes.iter().enumerate() {
                if j != 0 {
                    print!(",");
                }
                print!("{}", lane.r as u8);
            }
        }
        println!(
            "],\"route_count\":{},\"complete_bytes\":{}}}",
            if candidate.global {
                1
            } else {
                candidate.lanes.len()
            },
            candidate.bytes
        );
    }
    print!(
        "],\"selected\":{{\"tag\":\"{}\",\"width\":{},\"phase\":{},\"operators\":[",
        sel.tag, sel.w, sel.phase
    );
    for (i, o) in sel.ops.iter().enumerate() {
        if i > 0 {
            print!(",")
        }
        print!("{o}")
    }
    println!(
        "],\"backend\":\"{}\",\"internal_verified_inverse\":true,\"raw_fallback\":{}}}}}",
        if sel.global {
            "global-zstd"
        } else {
            "per-lane-mixed"
        },
        raw_fallback
    );
    Ok(())
}
fn run() -> Result<(), String> {
    let a: Vec<String> = env::args().skip(1).collect();
    match a.as_slice(){[op,flag,pol,input,out]if op=="encode"&&flag=="--policy"=>encode(pol,input,out),[op,input,out]if op=="decode"=>fs::write(out,unpack(&read(input,A)?)?).map_err(|e|e.to_string()),_=>Err("usage: latent_layout encode --policy auto|whole|bss|uniform|oracle|mask-control INPUT ARC | latent_layout decode ARC OUT".into())}
}
fn main() {
    if let Err(e) = run() {
        eprintln!("latent_layout: {e}");
        std::process::exit(1)
    }
}
