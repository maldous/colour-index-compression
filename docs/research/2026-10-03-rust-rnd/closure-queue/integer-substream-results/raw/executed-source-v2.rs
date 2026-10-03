//! Isolated ISC1 structural-integer closure harness; outside Cargo and src/.
//! Root must grant a scheduler lease before compiling or running this file.
use std::{
    env,
    fs::{self, File},
    io::Read,
    path::Path,
};
const MAGIC: &[u8; 4] = b"ISC1";
const VERSION: u8 = 1;
const SCHEMA: u8 = 1;
const MAX_VALUES: usize = 4096;
const MAX_TAIL: usize = 1024;
const MAX_BITS: u64 = 1 << 20;
const MAX_RICE_QUOTIENT: u64 = 1 << 16;
const MAX_ARCHIVE: usize = 128 << 10;
const MAX_INPUT: usize = 8 + MAX_VALUES * 11 + 2 + MAX_TAIL;
#[derive(Clone, Copy)]
enum Coder {
    Varint,
    Gamma,
    Delta,
    Rice(u8),
}
impl Coder {
    fn parse(s: &str) -> Result<Self, String> {
        match s {
            "varint" => Ok(Self::Varint),
            "gamma" => Ok(Self::Gamma),
            "delta" => Ok(Self::Delta),
            "rice:0" => Ok(Self::Rice(0)),
            "rice:2" => Ok(Self::Rice(2)),
            "rice:4" => Ok(Self::Rice(4)),
            "rice:8" => Ok(Self::Rice(8)),
            _ => Err("invalid ISC1 coder".into()),
        }
    }
    fn id(self) -> u8 {
        match self {
            Self::Varint => 0,
            Self::Gamma => 1,
            Self::Delta => 2,
            Self::Rice(_) => 3,
        }
    }
    fn k(self) -> u8 {
        if let Self::Rice(k) = self {
            k
        } else {
            0
        }
    }
    fn from(id: u8, k: u8) -> Result<Self, String> {
        match (id, k) {
            (0, 0) => Ok(Self::Varint),
            (1, 0) => Ok(Self::Gamma),
            (2, 0) => Ok(Self::Delta),
            (3, 0 | 2 | 4 | 8) => Ok(Self::Rice(k)),
            _ => Err("invalid ISC1 coder".into()),
        }
    }
}
fn crc32(d: &[u8]) -> u32 {
    let mut c = !0u32;
    for &b in d {
        c ^= b as u32;
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
fn put64(o: &mut Vec<u8>, v: u64) {
    o.extend_from_slice(&v.to_le_bytes())
}
fn take64(d: &[u8], p: &mut usize) -> Result<u64, String> {
    let e = p
        .checked_add(8)
        .ok_or_else(|| "ISC length overflow".to_string())?;
    let a: [u8; 8] = d
        .get(*p..e)
        .ok_or_else(|| "truncated ISC length".to_string())?
        .try_into()
        .map_err(|_| "bad ISC length".to_string())?;
    *p = e;
    Ok(u64::from_le_bytes(a))
}
fn as_usize(v: u64, n: &str) -> Result<usize, String> {
    usize::try_from(v).map_err(|_| format!("ISC {n} exceeds host width"))
}
fn read_bounded(p: impl AsRef<Path>, cap: usize) -> Result<Vec<u8>, String> {
    let p = p.as_ref();
    let m = fs::metadata(p).map_err(|e| format!("{}: {e}", p.display()))?;
    if !m.is_file() || m.len() > cap as u64 {
        return Err(format!("{} exceeds ISC input cap", p.display()));
    }
    let f = File::open(p).map_err(|e| format!("{}: {e}", p.display()))?;
    let mut r = f.take(cap as u64 + 1);
    let mut d = Vec::new();
    r.read_to_end(&mut d).map_err(|e| e.to_string())?;
    if d.len() > cap {
        Err("ISC input cap".into())
    } else {
        Ok(d)
    }
}
fn put_var(mut v: u64, o: &mut Vec<u8>) {
    while v >= 128 {
        o.push((v as u8 & 127) | 128);
        v >>= 7
    }
    o.push(v as u8)
}
fn take_var(d: &[u8], p: &mut usize) -> Result<u64, String> {
    let mut v: u64 = 0;
    for s in (0..70).step_by(7) {
        let b = *d.get(*p).ok_or_else(|| "truncated varint".to_string())?;
        *p = p
            .checked_add(1)
            .ok_or_else(|| "varint position overflow".to_string())?;
        if s == 63 && b & 127 > 1 {
            return Err("varint overflow".into());
        }
        v |= (b as u64 & 127) << s;
        if b < 128 {
            if s > 0 && b == 0 {
                return Err("noncanonical varint".into());
            }
            return Ok(v);
        }
    }
    Err("oversized varint".into())
}
struct BW {
    d: Vec<u8>,
    c: u8,
    n: u8,
    b: u64,
}
impl BW {
    fn put(&mut self, x: u8) -> Result<(), String> {
        if self.b == MAX_BITS {
            return Err("ISC bit cap".into());
        }
        self.c = (self.c << 1) | (x & 1);
        self.n += 1;
        self.b += 1;
        if self.n == 8 {
            self.d.push(self.c);
            self.c = 0;
            self.n = 0
        }
        Ok(())
    }
    fn bits(&mut self, v: u64, n: u8) -> Result<(), String> {
        for s in (0..n).rev() {
            self.put(((v >> s) & 1) as u8)?
        }
        Ok(())
    }
    fn finish(mut self) -> (Vec<u8>, u64) {
        if self.n > 0 {
            self.d.push(self.c << (8 - self.n))
        }
        (self.d, self.b)
    }
}
struct BR<'a> {
    d: &'a [u8],
    b: u64,
    p: u64,
}
impl<'a> BR<'a> {
    fn bit(&mut self) -> Result<u8, String> {
        if self.p >= self.b {
            return Err("truncated bits".into());
        }
        let x = (self.d[(self.p / 8) as usize] >> (7 - self.p % 8)) & 1;
        self.p += 1;
        Ok(x)
    }
    fn bits(&mut self, n: u8) -> Result<u64, String> {
        let mut v: u64 = 0;
        for _ in 0..n {
            v = (v << 1) | self.bit()? as u64
        }
        Ok(v)
    }
}
fn gamma(w: &mut BW, v: u64) -> Result<(), String> {
    if v == 0 {
        return Err("gamma zero".into());
    }
    let z = (63 - v.leading_zeros()) as u8;
    for _ in 0..z {
        w.put(0)?
    }
    w.bits(v, z + 1)
}
fn ungamma(r: &mut BR) -> Result<u64, String> {
    let mut z: u8 = 0;
    while r.bit()? == 0 {
        z = z.checked_add(1).ok_or_else(|| "gamma width".to_string())?;
        if z >= 64 {
            return Err("gamma width".into());
        }
    }
    Ok((1u64 << z) | r.bits(z)?)
}
fn delta(w: &mut BW, v: u64) -> Result<(), String> {
    if v == 0 {
        return Err("delta zero".into());
    }
    let n = (64 - v.leading_zeros()) as u8;
    gamma(w, n as u64)?;
    w.bits(v ^ (1u64 << (n - 1)), n - 1)
}
fn undelta(r: &mut BR) -> Result<u64, String> {
    let n = ungamma(r)?;
    if n == 0 || n > 64 {
        return Err("delta width".into());
    }
    Ok((1u64 << (n - 1)) | r.bits((n - 1) as u8)?)
}
fn rice_limit(k: u8) -> u64 {
    63 - k as u64
}
fn enc(c: Coder, v: u64, raw: &mut Vec<u8>, w: &mut BW) -> Result<(), String> {
    match c {
        Coder::Varint => {
            put_var(v, raw);
            Ok(())
        }
        Coder::Gamma => {
            if v == u64::MAX {
                w.put(0)
            } else {
                w.put(1)?;
                gamma(w, v + 1)
            }
        }
        Coder::Delta => {
            if v == u64::MAX {
                w.put(0)
            } else {
                w.put(1)?;
                delta(w, v + 1)
            }
        }
        Coder::Rice(k) => {
            let q = v >> k;
            if q > rice_limit(k) {
                w.put(0)?;
                w.bits(v, 64)
            } else {
                w.put(1)?;
                for _ in 0..q {
                    w.put(0)?
                }
                w.put(1)?;
                w.bits(v & ((1u64 << k) - 1), k)
            }
        }
    }
}
fn dec(c: Coder, raw: &[u8], rp: &mut usize, r: &mut BR) -> Result<u64, String> {
    match c {
        Coder::Varint => take_var(raw, rp),
        Coder::Gamma => {
            if r.bit()? == 0 {
                Ok(u64::MAX)
            } else {
                ungamma(r)?
                    .checked_sub(1)
                    .ok_or_else(|| "gamma value".to_string())
            }
        }
        Coder::Delta => {
            if r.bit()? == 0 {
                Ok(u64::MAX)
            } else {
                undelta(r)?
                    .checked_sub(1)
                    .ok_or_else(|| "delta value".to_string())
            }
        }
        Coder::Rice(k) => {
            if r.bit()? == 0 {
                let v = r.bits(64)?;
                if v >> k <= rice_limit(k) {
                    Err("noncanonical Rice raw escape".into())
                } else {
                    Ok(v)
                }
            } else {
                let mut q: u64 = 0;
                while r.bit()? == 0 {
                    q = q
                        .checked_add(1)
                        .ok_or_else(|| "rice quotient overflow".to_string())?;
                    if q > MAX_RICE_QUOTIENT {
                        return Err("rice quotient cap".into());
                    }
                    if q > rice_limit(k) {
                        return Err("noncanonical Rice unary quotient".into());
                    }
                }
                Ok((q << k) | r.bits(k)?)
            }
        }
    }
}
fn input(v: &[(u8, u64)], tail: &[u8]) -> Vec<u8> {
    let mut o = b"ISIN1".to_vec();
    o.push(SCHEMA);
    o.extend_from_slice(&(v.len() as u16).to_le_bytes());
    for &(t, x) in v {
        o.push(t);
        put_var(x, &mut o)
    }
    o.extend_from_slice(&(tail.len() as u16).to_le_bytes());
    o.extend_from_slice(tail);
    o
}
fn parse_input(d: &[u8]) -> Result<(Vec<u8>, Vec<u64>, Vec<u8>), String> {
    if d.get(..5) != Some(b"ISIN1") || d.get(5) != Some(&SCHEMA) {
        return Err("not ISC input".into());
    }
    let n = u16::from_le_bytes(
        d.get(6..8)
            .ok_or_else(|| "short input".to_string())?
            .try_into()
            .map_err(|_| "bad count".to_string())?,
    ) as usize;
    if n > MAX_VALUES {
        return Err("value cap".into());
    }
    let mut p = 8;
    let mut t = Vec::with_capacity(n);
    let mut v = Vec::with_capacity(n);
    for _ in 0..n {
        let x = *d.get(p).ok_or_else(|| "short tag".to_string())?;
        p = p
            .checked_add(1)
            .ok_or_else(|| "tag position overflow".to_string())?;
        if x > 3 {
            return Err("unknown tag".into());
        }
        t.push(x);
        v.push(take_var(d, &mut p)?)
    }
    let e = p
        .checked_add(2)
        .ok_or_else(|| "tail overflow".to_string())?;
    let l = u16::from_le_bytes(
        d.get(p..e)
            .ok_or_else(|| "short tail".to_string())?
            .try_into()
            .map_err(|_| "bad tail".to_string())?,
    ) as usize;
    p = e;
    let end = p
        .checked_add(l)
        .ok_or_else(|| "tail overflow".to_string())?;
    if l > MAX_TAIL || end != d.len() {
        return Err("tail mismatch".into());
    }
    Ok((t, v, d[p..end].to_vec()))
}
fn next(s: &mut u64) -> u64 {
    *s ^= *s << 13;
    *s ^= *s >> 7;
    *s ^= *s << 17;
    *s
}
fn fixture(n: &str) -> Result<Vec<u8>, String> {
    let mut s = 0x9e3779b97f4a7c15;
    let mut v = Vec::new();
    for i in 0..256 {
        let x = match n {
            "strong" => [0, 1, 4, 16, 64, 255, u64::MAX, 8][i % 8],
            "weak" => {
                if i % 9 == 0 {
                    next(&mut s) & 1023
                } else {
                    [0, 1, 4, 16, 64, 255][i % 6]
                }
            }
            "absent" => next(&mut s) & 65535,
            _ => return Err("fixture must be strong, weak, or absent".into()),
        };
        v.push(((i % 4) as u8, x))
    }
    Ok(input(&v, if n == "strong" { b"tail" } else { b"t" }))
}
fn frame(c: Coder, t: &[u8], v: &[u64], tail: &[u8]) -> Result<Vec<u8>, String> {
    let mut raw = Vec::new();
    let mut w = BW {
        d: Vec::new(),
        c: 0,
        n: 0,
        b: 0,
    };
    for &x in v {
        enc(c, x, &mut raw, &mut w)?
    }
    let (bits, bits_n) = w.finish();
    let (data, bits_n) = if matches!(c, Coder::Varint) {
        let n = (raw.len() as u64)
            .checked_mul(8)
            .ok_or_else(|| "varint bit length".to_string())?;
        (raw, n)
    } else {
        (bits, bits_n)
    };
    let mut o = MAGIC.to_vec();
    o.extend([VERSION, c.id(), c.k(), SCHEMA]);
    put64(&mut o, v.len() as u64);
    put64(&mut o, t.len() as u64);
    put64(&mut o, tail.len() as u64);
    put64(&mut o, bits_n);
    put64(&mut o, data.len() as u64);
    o.extend_from_slice(t);
    o.extend_from_slice(&data);
    o.extend_from_slice(tail);
    let crc = crc32(&o[4..]);
    o.extend_from_slice(&crc.to_le_bytes());
    if o.len() > MAX_ARCHIVE {
        Err("archive cap".into())
    } else {
        Ok(o)
    }
}
fn unframe(d: &[u8]) -> Result<Vec<u8>, String> {
    if d.len() > MAX_ARCHIVE || d.get(..4) != Some(MAGIC) || d.get(4) != Some(&VERSION) {
        return Err("not ISC1".into());
    }
    let c = Coder::from(
        *d.get(5).ok_or_else(|| "short coder".to_string())?,
        *d.get(6).ok_or_else(|| "short rice k".to_string())?,
    )?;
    if d.get(7) != Some(&SCHEMA) {
        return Err("unknown schema".into());
    }
    let mut p = 8;
    let n = as_usize(take64(d, &mut p)?, "count")?;
    let tn = as_usize(take64(d, &mut p)?, "tags")?;
    let tl = as_usize(take64(d, &mut p)?, "tail")?;
    let bn = take64(d, &mut p)?;
    let il = as_usize(take64(d, &mut p)?, "integer length")?;
    if n > MAX_VALUES
        || tn != n
        || tl > MAX_TAIL
        || bn > MAX_BITS
        || il > ((MAX_BITS + 7) / 8) as usize
    {
        return Err("ISC bounds".into());
    }
    let packed = as_usize(
        bn.checked_add(7)
            .ok_or_else(|| "bit length overflow".to_string())?
            / 8,
        "packed length",
    )?;
    if (matches!(c, Coder::Varint) && bn != il as u64 * 8)
        || (!matches!(c, Coder::Varint) && il != packed)
    {
        return Err("integer length".into());
    }
    let end = p
        .checked_add(tn)
        .and_then(|x| x.checked_add(il))
        .and_then(|x| x.checked_add(tl))
        .ok_or_else(|| "length overflow".to_string())?;
    if end.checked_add(4) != Some(d.len()) {
        return Err("frame length".into());
    }
    let crc = u32::from_le_bytes(d[end..].try_into().map_err(|_| "short CRC".to_string())?);
    if crc32(&d[4..end]) != crc {
        return Err("CRC".into());
    }
    let tags = &d[p..p + tn];
    if tags.iter().any(|&x| x > 3) {
        return Err("tag".into());
    }
    p += tn;
    let ints = &d[p..p + il];
    p += il;
    let tail = &d[p..end];
    if !matches!(c, Coder::Varint) && bn % 8 != 0 {
        let mask = (1u8 << (8 - bn % 8) as u8) - 1;
        if ints
            .last()
            .ok_or_else(|| "missing integer payload".to_string())?
            & mask
            != 0
        {
            return Err("noncanonical padding".into());
        }
    }
    let mut rp = 0;
    let mut r = BR {
        d: ints,
        b: bn,
        p: 0,
    };
    let mut v = Vec::with_capacity(n);
    for _ in 0..n {
        v.push(dec(c, ints, &mut rp, &mut r)?)
    }
    if if matches!(c, Coder::Varint) {
        rp != ints.len()
    } else {
        r.p != bn
    } {
        return Err("integer trailing".into());
    }
    Ok(input(
        &tags.iter().copied().zip(v).collect::<Vec<_>>(),
        tail,
    ))
}
fn main() -> Result<(), String> {
    let a: Vec<String> = env::args().collect();
    match a.get(1).map(String::as_str){Some("generate")if a.len()==4=>fs::write(&a[3],fixture(&a[2])?).map_err(|e|e.to_string()),Some("decode")if a.len()==4=>fs::write(&a[3],unframe(&read_bounded(&a[2],MAX_ARCHIVE)?)?).map_err(|e|e.to_string()),Some("encode")if a.len()==6=>{let src=read_bounded(&a[3],MAX_INPUT)?;let(t,v,tail)=parse_input(&src)?;let arc=frame(Coder::parse(&a[2])?,&t,&v,&tail)?;fs::write(&a[4],&arc).map_err(|e|e.to_string())?;let exe=env::current_exe().map_err(|e|e.to_string())?;let out=Path::new(&a[5]);let ok=std::process::Command::new(exe).args(["decode",&a[4],out.to_str().ok_or_else(||"nonutf8".to_string())?]).status().map_err(|e|e.to_string())?.success()&&read_bounded(out,MAX_INPUT)?==src;if !ok{return Err("fresh archive-only decode failed".into())}println!("{{\"coder\":\"{}\",\"input_bytes\":{},\"complete_bytes\":{},\"values\":{},\"fresh_archive_only_decode\":true}}",a[2],src.len(),arc.len(),v.len());Ok(())},_=>Err("usage: isc generate strong|weak|absent OUT | isc encode CODER INPUT ARCHIVE RESTORED | isc decode ARCHIVE OUT".into())}
}
