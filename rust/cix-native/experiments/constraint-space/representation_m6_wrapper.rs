//! Bounded SMC1 composition wrapper; standalone experiment binary.
use cix_native::{adaptive, huffman, legacy_lz};
use std::{
    env,
    ffi::{c_uint, c_void},
    fs,
    io::{Read, Write},
    process::{Command, Stdio},
    thread,
};
const M: &[u8; 4] = b"SMC1";
const V: u8 = 1;
const H: usize = 25;
const N: usize = 4096;
const A: usize = 32768;
#[link(name = "zstd")]
unsafe extern "C" {
    fn ZSTD_decompress(
        dst: *mut c_void,
        dst_cap: usize,
        src: *const c_void,
        src_len: usize,
    ) -> usize;
    fn ZSTD_findFrameCompressedSize(src: *const c_void, src_len: usize) -> usize;
    fn ZSTD_getFrameHeader(header: *mut FH, src: *const c_void, src_len: usize) -> usize;
    fn ZSTD_isError(code: usize) -> c_uint;
}
// Exact ZSTD_frameHeader layout from the system zstd.h.
#[repr(C)]
struct FH {
    f: u64,
    w: u64,
    b: u32,
    t: u32,
    h: u32,
    d: u32,
    c: u32,
    r1: u32,
    r2: u32,
}
fn crc(x: &[u8]) -> u32 {
    let mut c = !0u32;
    for &b in x {
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
        return Err("regular-file bound".into());
    }
    let mut f = fs::File::open(path).map_err(|e| e.to_string())?;
    let mut x = Vec::new();
    Read::by_ref(&mut f)
        .take((cap + 1) as u64)
        .read_to_end(&mut x)
        .map_err(|e| e.to_string())?;
    if x.len() > cap {
        Err("file bound".into())
    } else {
        Ok(x)
    }
}
fn geo(n: usize, w: usize, p: usize) -> bool {
    n > 0 && (1..=8).contains(&w) && p < w && p <= n && w <= n - p
}
fn ops(s: &str, w: usize) -> Result<Vec<u8>, String> {
    let o: Result<Vec<u8>, _> = s.split(',').map(str::parse).collect();
    let o = o.map_err(|_| "operators")?;
    if o.len() != w || o.iter().any(|&x| x > 4) || o.first() != Some(&0) {
        Err("operator grammar".into())
    } else {
        Ok(o)
    }
}
fn count(n: usize, w: usize, p: usize, j: usize) -> Result<usize, String> {
    let q = p.checked_add(j).ok_or("lane")?;
    if q >= n {
        Err("empty lane".into())
    } else {
        Ok((n - q).div_ceil(w))
    }
}
// T = source[..p] then complete lanes.  Predictors reference original bytes.
fn trans(x: &[u8], w: usize, p: usize, o: &[u8]) -> Result<Vec<u8>, String> {
    if !geo(x.len(), w, p) || o.len() != w {
        return Err("geometry".into());
    }
    let mut y = x[..p].to_vec();
    for j in 0..w {
        for r in 0..count(x.len(), w, p, j)? {
            let i = p + r * w + j;
            y.push(if r == 0 || o[j] == 0 {
                x[i]
            } else {
                match o[j] {
                    1 => x[i].wrapping_sub(x[i - w]),
                    2 => x[i].wrapping_sub(x[i - 1]),
                    3 => x[i] ^ x[i - 1],
                    4 => x[i] ^ x[i - w],
                    _ => return Err("operator".into()),
                }
            })
        }
    }
    if y.len() == x.len() {
        Ok(y)
    } else {
        Err("transform length".into())
    }
}
fn inv(y: &[u8], n: usize, w: usize, p: usize, o: &[u8]) -> Result<Vec<u8>, String> {
    if y.len() != n || !geo(n, w, p) || o.len() != w {
        return Err("inverse grammar".into());
    }
    let mut x = y[..p].to_vec();
    x.resize(n, 0);
    let mut q = p;
    for j in 0..w {
        for r in 0..count(n, w, p, j)? {
            let b = *y.get(q).ok_or("lane data")?;
            q += 1;
            let i = p + r * w + j;
            x[i] = if r == 0 || o[j] == 0 {
                b
            } else {
                match o[j] {
                    1 => b.wrapping_add(x[i - w]),
                    2 => b.wrapping_add(x[i - 1]),
                    3 => b ^ x[i - 1],
                    4 => b ^ x[i - w],
                    _ => return Err("operator".into()),
                }
            }
        }
    }
    if q == n {
        Ok(x)
    } else {
        Err("trailing transformed".into())
    }
}
fn u32a(x: &[u8], p: &mut usize) -> Result<usize, String> {
    let e = p.checked_add(4).ok_or("offset")?;
    let b = x.get(*p..e).ok_or("u32")?;
    *p = e;
    Ok(u32::from_le_bytes(b.try_into().map_err(|_| "u32")?) as usize)
}
fn var(x: &[u8], p: &mut usize) -> Result<usize, String> {
    let s = *p;
    let mut v = 0usize;
    for sh in (0..usize::BITS).step_by(7) {
        let b = *x.get(*p).ok_or("truncated varint")?;
        *p += 1;
        let low = (b & 127) as usize;
        if sh + 7 > usize::BITS && low > (usize::MAX >> sh) {
            return Err("varint overflow".into());
        }
        v = v
            .checked_add(low.checked_shl(sh).ok_or("varint overflow")?)
            .ok_or("varint overflow")?;
        if b & 128 == 0 {
            if *p - s > 1 && b == 0 {
                return Err("noncanonical varint".into());
            }
            return Ok(v);
        }
    }
    Err("oversized varint".into())
}
// Validate all finite CIXM6 framing before the frozen external decoder sees it.
fn m6ok(x: &[u8], n: usize) -> Result<u32, String> {
    if x.get(..5) != Some(b"CIXM6") {
        return Err("CIXM6 magic".into());
    }
    let mut p = 5;
    let h = var(x, &mut p)?;
    if h == 0 || h > 1024 * 1024 {
        return Err("CIXM6 history".into());
    }
    let mut total = 0;
    loop {
        let mode = *x.get(p).ok_or("CIXM6 frame")?;
        p += 1;
        if mode == 255 {
            let expect = var(x, &mut p)?;
            let e = p.checked_add(4).ok_or("CIXM6 footer")?;
            let sum = u32::from_le_bytes(
                x.get(p..e)
                    .ok_or("CIXM6 footer")?
                    .try_into()
                    .map_err(|_| "CIXM6 footer")?,
            );
            p = e;
            if expect == total && total == n && p == x.len() {
                return Ok(sum);
            }
            return Err("CIXM6 footer".into());
        }
        let sl = var(x, &mut p)?;
        let pl = var(x, &mut p)?;
        if mode > 20
            || sl == 0
            || sl > n
            || pl > A
            || pl > sl.saturating_mul(8).saturating_add(4096)
        {
            return Err("CIXM6 frame bound".into());
        }
        total = total.checked_add(sl).ok_or("CIXM6 total")?;
        if total > n {
            return Err("CIXM6 total".into());
        }
        let e = p.checked_add(pl).ok_or("CIXM6 payload")?;
        if e > x.len() {
            return Err("CIXM6 payload".into());
        }
        p = e
    }
}
fn zdec(x: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let z = unsafe { ZSTD_findFrameCompressedSize(x.as_ptr().cast(), x.len()) };
    if unsafe { ZSTD_isError(z) } != 0 || z != x.len() {
        return Err("one zstd frame".into());
    }
    let mut h: FH = unsafe { std::mem::zeroed() };
    let q = unsafe { ZSTD_getFrameHeader(&mut h, x.as_ptr().cast(), x.len()) };
    if unsafe { ZSTD_isError(q) } != 0 || q != 0 || h.f != n as u64 || h.w > N as u64 {
        return Err("zstd frame bounds".into());
    }
    let mut y = vec![0; n];
    let q = unsafe { ZSTD_decompress(y.as_mut_ptr().cast(), n, x.as_ptr().cast(), x.len()) };
    if unsafe { ZSTD_isError(q) } != 0 || q != n {
        Err("zstd decode".into())
    } else {
        Ok(y)
    }
}
fn cixdec(cix: &str, pay: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let _ = m6ok(pay, n)?;
    let mut c = Command::new(cix)
        .args(["-d", "--threads", "1", "--memory", "1536MiB", "-c"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .map_err(|e| e.to_string())?;
    let mut sin = c.stdin.take().ok_or("cix stdin")?;
    let input = pay.to_vec();
    let writer = thread::spawn(move || -> Result<(), String> {
        for q in input.chunks(A) {
            sin.write_all(q).map_err(|e| e.to_string())?
        }
        Ok(())
    });
    let mut sout = c.stdout.take().ok_or("cix stdout")?;
    let mut y = Vec::with_capacity(n + 1);
    let read_result = sout
        .by_ref()
        .take((n + 1) as u64)
        .read_to_end(&mut y)
        .map_err(|e| e.to_string());
    if let Err(error) = read_result {
        let _ = c.kill();
        drop(sout);
        let _ = c.wait();
        let _ = writer.join();
        return Err(error);
    }
    if y.len() > n {
        let _ = c.kill();
    }
    drop(sout);
    let status = c.wait().map_err(|e| e.to_string())?;
    writer.join().map_err(|_| "cix writer panic")??;
    if !status.success() || y.len() != n {
        Err("sealed cix decode".into())
    } else {
        Ok(y)
    }
}
fn lane(x: &[u8], w: usize, p: usize, j: usize, o: u8) -> Result<Vec<u8>, String> {
    let mut v = vec![0; w];
    v[j] = o;
    let t = trans(x, w, p, &v)?;
    let start = p
        + (0..j).try_fold(0usize, |total, i| {
            count(x.len(), w, p, i).map(|n| total + n)
        })?;
    let n = count(x.len(), w, p, j)?;
    Ok(t.get(start..start + n).ok_or("lane slice")?.to_vec())
}
fn nenc(x: &[u8], w: usize, p: usize, o: &[u8]) -> Result<Vec<u8>, String> {
    let mut b = x[..p].to_vec();
    for j in 0..w {
        let d = lane(x, w, p, j, o[j])?;
        let mut cs = vec![
            (0, d.clone()),
            (1, huffman::encode(&d).map_err(|e| e.to_string())?),
            (2, adaptive::encode_general(&d, 0, 8, &[], 1)?),
            (3, legacy_lz::encode(&d, &[], 1)?.payload),
        ];
        let (r, q) = cs
            .drain(..)
            .min_by_key(|(r, q)| (q.len(), *r))
            .ok_or("native route")?;
        b.push(r);
        b.extend((d.len() as u32).to_le_bytes());
        b.extend((q.len() as u32).to_le_bytes());
        b.extend(q)
    }
    if b.len() <= A {
        Ok(b)
    } else {
        Err("native body bound".into())
    }
}
fn ndec(b: &[u8], n: usize, w: usize, phase: usize, o: &[u8]) -> Result<Vec<u8>, String> {
    let mut p = phase;
    let mut t = b.get(..phase).ok_or("native prefix")?.to_vec();
    for j in 0..w {
        let r = *b.get(p).ok_or("native route")?;
        p += 1;
        let dl = u32a(b, &mut p)?;
        let pl = u32a(b, &mut p)?;
        let e = p.checked_add(pl).ok_or("native payload")?;
        let q = b.get(p..e).ok_or("native payload")?;
        p = e;
        let want = count(n, w, phase, j)?;
        if dl != want || pl > A {
            return Err("native lane length".into());
        }
        let d = match r {
            0 => {
                if q.len() != want {
                    return Err("raw lane".into());
                }
                q.to_vec()
            }
            1 => {
                if q.len() < 19
                    || q.first() != Some(&huffman::VERSION)
                    || u64::from_le_bytes(
                        q.get(3..11)
                            .ok_or("huffman header")?
                            .try_into()
                            .map_err(|_| "huffman header")?,
                    ) != want as u64
                {
                    return Err("huffman header".into());
                }
                huffman::decode(q).map_err(|e| e.to_string())?
            }
            2 => adaptive::decode_general(q, want, &[], 1)?,
            3 => legacy_lz::decode(q, want, &[], 4096)?,
            _ => return Err("native route".into()),
        };
        if d.len() != want {
            return Err("native decoded length".into());
        }
        t.extend(d)
    }
    if p != b.len() || t.len() != n {
        return Err("native trailing".into());
    }
    inv(&t, n, w, phase, o)
}
fn pack(
    kind: &str,
    w: usize,
    p: usize,
    o: &[u8],
    src: &[u8],
    pay: &[u8],
) -> Result<Vec<u8>, String> {
    if !geo(src.len(), w, p) || o.len() != w {
        return Err("geometry".into());
    }
    let id = match kind {
        "m6" => 0,
        "zstd" => 1,
        "native" => 2,
        _ => return Err("backend".into()),
    };
    if id == 0 {
        if m6ok(pay, src.len())? != crc(&trans(src, w, p, o)?) {
            return Err("CIXM6 footer CRC32".into());
        }
    } else if id == 1 {
        if zdec(pay, src.len())? != trans(src, w, p, o)? {
            return Err("zstd transformed bytes".into());
        }
    } else if ndec(pay, src.len(), w, p, o)? != src {
        return Err("native source bytes".into());
    }
    let len = H
        .checked_add(w)
        .and_then(|z| z.checked_add(pay.len()))
        .ok_or("archive size")?;
    if len > A {
        return Err("archive bound".into());
    }
    let mut a = Vec::with_capacity(len);
    a.extend(M);
    a.push(V);
    a.push(id);
    a.extend((src.len() as u32).to_le_bytes());
    a.extend((src.len() as u32).to_le_bytes());
    a.extend(crc(src).to_le_bytes());
    a.push(w as u8);
    a.push(p as u8);
    a.push(w as u8);
    a.extend(o);
    a.extend((pay.len() as u32).to_le_bytes());
    a.extend(pay);
    if a.len() == len {
        Ok(a)
    } else {
        Err("archive construction".into())
    }
}
fn unpack(cix: &str, a: &[u8]) -> Result<Vec<u8>, String> {
    if a.len() < H || a.len() > A || a.get(..4) != Some(M) || a.get(4) != Some(&V) {
        return Err("SMC1 header".into());
    }
    let id = *a.get(5).ok_or("backend")?;
    let mut p = 6;
    let n = u32a(a, &mut p)?;
    let tn = u32a(a, &mut p)?;
    let c = u32a(a, &mut p)? as u32;
    let w = *a.get(p).ok_or("width")? as usize;
    p += 1;
    let phase = *a.get(p).ok_or("phase")? as usize;
    p += 1;
    let k = *a.get(p).ok_or("operator count")? as usize;
    p += 1;
    if n > N || tn != n || !geo(n, w, phase) || k != w {
        return Err("SMC1 grammar".into());
    }
    let e = p.checked_add(w).ok_or("operator offset")?;
    let o = ops(
        &a.get(p..e)
            .ok_or("operators")?
            .iter()
            .map(u8::to_string)
            .collect::<Vec<_>>()
            .join(","),
        w,
    )?;
    p = e;
    let z = u32a(a, &mut p)?;
    let e = p.checked_add(z).ok_or("payload offset")?;
    let pay = a.get(p..e).ok_or("payload")?;
    if e != a.len() {
        return Err("trailing archive".into());
    }
    let x = match id {
        0 => {
            if !cix.starts_with('/') {
                return Err("sealed CIX path must be absolute".into());
            }
            inv(&cixdec(cix, pay, n)?, n, w, phase, &o)?
        }
        1 => inv(&zdec(pay, n)?, n, w, phase, &o)?,
        2 => ndec(pay, n, w, phase, &o)?,
        _ => return Err("backend".into()),
    };
    if crc(&x) == c {
        Ok(x)
    } else {
        Err("source CRC32".into())
    }
}
fn run() -> Result<(), String> {
    let a: Vec<String> = env::args().skip(1).collect();
    match a.as_slice(){[op,fw,w,fp,p,fo,o,input,out]if op=="transform"&&fw=="--width"&&fp=="--phase"&&fo=="--ops"=>{let w=w.parse().map_err(|_|"width")?;let p=p.parse().map_err(|_|"phase")?;let x=read(input,N)?;fs::write(out,trans(&x,w,p,&ops(o,w)?)?).map_err(|e|e.to_string())},[op,fb,b,fw,w,fp,p,fo,o,src,pay,out]if op=="pack"&&fb=="--backend"&&fw=="--width"&&fp=="--phase"&&fo=="--ops"=>{let w=w.parse().map_err(|_|"width")?;let p=p.parse().map_err(|_|"phase")?;let x=read(src,N)?;let q=read(pay,A)?;fs::write(out,pack(b,w,p,&ops(o,w)?,&x,&q)?).map_err(|e|e.to_string())},[op,fc,cix,arc,out]if op=="decode"&&fc=="--cix"=>fs::write(out,unpack(cix,&read(arc,A)?)?).map_err(|e|e.to_string()),[op,fw,w,fp,p,fo,o,src,out]if op=="native"&&fw=="--width"&&fp=="--phase"&&fo=="--ops"=>{let w=w.parse().map_err(|_|"width")?;let p=p.parse().map_err(|_|"phase")?;let x=read(src,N)?;let o=ops(o,w)?;if !geo(x.len(),w,p){return Err("geometry".into())}let body=nenc(&x,w,p,&o)?;fs::write(out,pack("native",w,p,&o,&x,&body)?).map_err(|e|e.to_string())},_=>Err("usage: transform --width W --phase P --ops csv SOURCE OUT | pack --backend m6|zstd --width W --phase P --ops csv SOURCE PAYLOAD OUT | decode --cix ABS_SEALED_CIX ARC OUT | native --width W --phase P --ops csv SOURCE OUT".into())}
}
fn main() {
    if let Err(e) = run() {
        eprintln!("representation_m6_wrapper: {e}");
        std::process::exit(1)
    }
}
