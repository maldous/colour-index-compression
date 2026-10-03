//! Isolated finite constraint-space prototype. Compile/run only under root's lease.
use std::{
    env,
    fs::{self, File},
    io::Read,
    path::Path,
};

const MAGIC: &[u8; 4] = b"CSP1";
const VERSION: u8 = 1;
const MAX_LEN: u8 = 5;
const MASK_EQ: u8 = 1;
const MASK_MOD: u8 = 2;
const MASK_HIST: u8 = 4;
#[derive(Clone, Copy)]
enum Domain {
    Byte,
    Nibble,
}
#[derive(Clone, Copy)]
struct Model {
    d: Domain,
    n: u8,
    mask: u8,
    eq: u8,
    mp: u8,
    modulus: u8,
    residue: u8,
    hv: u8,
    hc: u8,
}
fn err(s: &str) -> String {
    s.into()
}
fn space(m: Model) -> Result<u32, String> {
    let b = match m.d {
        Domain::Byte => 8,
        Domain::Nibble => 4,
    };
    if m.n == 0
        || m.n
            > match m.d {
                Domain::Byte => 2,
                Domain::Nibble => MAX_LEN,
            }
    {
        return Err(err("invalid object length"));
    }
    Ok(1u32 << (b * m.n))
}
fn metadata(m: Model) -> Result<(), String> {
    space(m)?;
    if m.mask & !7 != 0 {
        return Err(err("unknown model mask"));
    }
    match m.d {
        Domain::Byte => {
            if m.mask & MASK_HIST != 0 || m.eq != 0 || m.mp != 0 || m.hv != 0 || m.hc != 0 {
                return Err(err("invalid byte metadata"));
            }
        }
        Domain::Nibble => {
            if m.eq & !((1u8 << m.n.saturating_sub(1)) - 1) != 0 {
                return Err(err("equality mask beyond length"));
            }
            if m.mask & MASK_MOD != 0
                && (m.mp >= m.n || m.modulus < 2 || m.modulus > 16 || m.residue >= m.modulus)
            {
                return Err(err("invalid modular metadata"));
            }
            if m.mask & MASK_HIST != 0 && (m.hv > 15 || m.hc > m.n) {
                return Err(err("invalid histogram metadata"));
            }
        }
    }
    Ok(())
}
fn sym(x: u32, m: Model, p: u8) -> u8 {
    let b = match m.d {
        Domain::Byte => 8,
        Domain::Nibble => 4,
    };
    ((x >> ((m.n - 1 - p) * b)) & ((1 << b) - 1)) as u8
}
fn valid(x: u32, m: Model) -> bool {
    if matches!(m.d, Domain::Byte) {
        if m.mask & MASK_EQ != 0 && sym(x, m, 0) >= m.modulus {
            return false;
        }
        if m.mask & MASK_MOD != 0 && sym(x, m, 0) < m.residue {
            return false;
        }
        return true;
    }
    if m.mask & MASK_EQ != 0 {
        for p in 0..m.n.saturating_sub(1) {
            if m.eq & (1 << p) != 0 && sym(x, m, p) != sym(x, m, p + 1) {
                return false;
            }
        }
    }
    if m.mask & MASK_MOD != 0 {
        if m.mp >= m.n || m.modulus < 2 || m.modulus > 16 || m.residue >= m.modulus {
            return false;
        }
        if sym(x, m, m.mp) % m.modulus != m.residue {
            return false;
        }
    }
    if m.mask & MASK_HIST != 0 {
        let mut c = 0;
        for p in 0..m.n {
            if sym(x, m, p) == m.hv {
                c += 1
            }
        }
        if c != m.hc {
            return false;
        }
    }
    true
}
fn count(m: Model) -> Result<u32, String> {
    metadata(m)?;
    let mut c = 0;
    for x in 0..space(m)? {
        if valid(x, m) {
            c += 1
        }
    }
    Ok(c)
}
fn width(c: u32) -> u8 {
    if c <= 1 {
        0
    } else {
        32 - (c - 1).leading_zeros() as u8
    }
}
fn rank(x: u32, m: Model) -> Result<u32, String> {
    if x >= space(m)? || !valid(x, m) {
        return Err(err("object is outside model"));
    }
    let mut r = 0;
    for y in 0..x {
        if valid(y, m) {
            r += 1
        }
    }
    Ok(r)
}
fn unrank(r: u32, m: Model) -> Result<u32, String> {
    let mut left = r;
    for x in 0..space(m)? {
        if valid(x, m) {
            if left == 0 {
                return Ok(x);
            }
            left -= 1
        }
    }
    Err(err("rank outside model"))
}
struct BW {
    d: Vec<u8>,
    v: u8,
    n: u8,
}
impl BW {
    fn put(&mut self, b: u8) {
        self.v = (self.v << 1) | (b & 1);
        self.n += 1;
        if self.n == 8 {
            self.d.push(self.v);
            self.v = 0;
            self.n = 0
        }
    }
    fn bits(&mut self, v: u32, n: u8) {
        for s in (0..n).rev() {
            self.put((v >> s) as u8)
        }
    }
    fn finish(mut self) -> Vec<u8> {
        if self.n > 0 {
            self.d.push(self.v << (8 - self.n))
        }
        self.d
    }
}
fn header_bits(m: Model) -> u8 {
    33 + if matches!(m.d, Domain::Byte) { 16 } else { 9 }
}
fn object_bytes(x: u32, m: Model) -> Vec<u8> {
    (0..m.n).map(|p| sym(x, m, p)).collect()
}
fn read_bounded(p: impl AsRef<Path>, cap: usize) -> Result<Vec<u8>, String> {
    let p = p.as_ref();
    let meta = fs::metadata(p).map_err(|e| e.to_string())?;
    if !meta.is_file() || meta.len() > cap as u64 {
        return Err(err("archive cap"));
    }
    let f = File::open(p).map_err(|e| e.to_string())?;
    let mut r = f.take(cap as u64 + 1);
    let mut d = Vec::new();
    r.read_to_end(&mut d).map_err(|e| e.to_string())?;
    if d.len() > cap {
        Err(err("archive cap"))
    } else {
        Ok(d)
    }
}
struct BR<'a> {
    d: &'a [u8],
    p: usize,
}
impl<'a> BR<'a> {
    fn bit(&mut self) -> Result<u8, String> {
        let i = self.p / 8;
        if i >= self.d.len() {
            return Err(err("truncated prefix"));
        }
        let b = (self.d[i] >> (7 - self.p % 8)) & 1;
        self.p += 1;
        Ok(b)
    }
    fn bits(&mut self, n: u8) -> Result<u32, String> {
        let mut v = 0u32;
        for _ in 0..n {
            v = (v << 1) | self.bit()? as u32
        }
        Ok(v)
    }
}
fn crc32(d: &[u8]) -> u32 {
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
fn archive(m: Model, x: u32, raw: bool) -> Result<Vec<u8>, String> {
    metadata(m)?;
    if x >= space(m)? {
        return Err(err("object range"));
    }
    let c = count(m)?;
    if c == 0 && !raw {
        return Err(err("contradictory model"));
    }
    let pb = if raw {
        match m.d {
            Domain::Byte => 8 * m.n,
            Domain::Nibble => 4 * m.n,
        }
    } else {
        width(c)
    };
    let value = if raw { x } else { rank(x, m)? };
    let header = header_bits(m);
    let pad = (8 - (header + pb) % 8) % 8;
    let mut w = BW {
        d: Vec::new(),
        v: 0,
        n: 0,
    };
    w.bits(VERSION as u32, 3);
    w.bits(matches!(m.d, Domain::Nibble) as u32, 1);
    w.bits(raw as u32, 1);
    w.bits(m.n as u32, 3);
    w.bits(m.mask as u32, 3);
    w.bits(m.eq as u32, 4);
    w.bits(m.mp as u32, 3);
    if matches!(m.d, Domain::Byte) {
        w.bits(m.modulus as u32, 8);
        w.bits(m.residue as u32, 8)
    } else {
        w.bits(m.modulus as u32, 5);
        w.bits(m.residue as u32, 4)
    }
    w.bits(m.hv as u32, 4);
    w.bits(m.hc as u32, 3);
    w.bits(pb as u32, 5);
    w.bits(pad as u32, 3);
    w.bits(value, pb);
    w.bits(0, pad);
    let prefix = w.finish();
    let mut o = MAGIC.to_vec();
    o.extend(prefix);
    o.extend_from_slice(&crc32(&o[4..]).to_le_bytes());
    Ok(o)
}
fn restore(d: &[u8]) -> Result<(Model, u32), String> {
    if d.len() < 9 || d.get(..4) != Some(MAGIC) {
        return Err(err("not CSP1"));
    }
    let e = d.len() - 4;
    let got = u32::from_le_bytes(d[e..].try_into().map_err(|_| err("crc"))?);
    if crc32(&d[4..e]) != got {
        return Err(err("CRC"));
    }
    let mut r = BR { d: &d[4..e], p: 0 };
    if r.bits(3)? as u8 != VERSION {
        return Err(err("version"));
    }
    let dom = if r.bits(1)? == 0 {
        Domain::Byte
    } else {
        Domain::Nibble
    };
    let raw = r.bits(1)? != 0;
    let m = Model {
        d: dom,
        n: r.bits(3)? as u8,
        mask: r.bits(3)? as u8,
        eq: r.bits(4)? as u8,
        mp: r.bits(3)? as u8,
        modulus: if matches!(dom, Domain::Byte) {
            r.bits(8)? as u8
        } else {
            r.bits(5)? as u8
        },
        residue: if matches!(dom, Domain::Byte) {
            r.bits(8)? as u8
        } else {
            r.bits(4)? as u8
        },
        hv: r.bits(4)? as u8,
        hc: r.bits(3)? as u8,
    };
    let pb = r.bits(5)? as u8;
    let pad = r.bits(3)? as u8;
    if pad > 7 {
        return Err(err("padding"));
    }
    let x = r.bits(pb)?;
    for _ in 0..pad {
        if r.bit()? != 0 {
            return Err(err("noncanonical padding"));
        }
    }
    if r.p != r.d.len() * 8 {
        return Err(err("trailing prefix"));
    }
    metadata(m)?;
    let c = count(m)?;
    let want = if raw {
        match dom {
            Domain::Byte => 8 * m.n,
            Domain::Nibble => 4 * m.n,
        }
    } else {
        width(c)
    };
    if pb != want {
        return Err(err("payload width"));
    }
    let object = if raw { x } else { unrank(x, m)? };
    if object >= space(m)? || (!raw && !valid(object, m)) {
        return Err(err("invalid object"));
    }
    Ok((m, object))
}
fn num(s: &str) -> Result<u8, String> {
    s.parse().map_err(|_| err("numeric argument"))
}
fn model(a: &[String]) -> Result<Model, String> {
    let d = match a[2].as_str() {
        "byte" => Domain::Byte,
        "nibble" => Domain::Nibble,
        _ => return Err(err("domain byte|nibble")),
    };
    Ok(Model {
        d,
        n: num(&a[3])?,
        mask: num(&a[4])?,
        eq: num(&a[5])?,
        mp: num(&a[6])?,
        modulus: num(&a[7])?,
        residue: num(&a[8])?,
        hv: num(&a[9])?,
        hc: num(&a[10])?,
    })
}
fn main() -> Result<(), String> {
    let a: Vec<String> = env::args().collect();
    match a.get(1).map(String::as_str){Some("count")if a.len()==11=>{println!("{}",count(model(&a)? )?);Ok(())},Some("encode")if a.len()==15=>{let m=model(&a)?;let raw=match a[11].as_str(){"raw"=>true,"rank"=>false,_=>return Err(err("mode raw|rank"))};let x:u32=a[12].parse().map_err(|_|err("object argument"))?;let source=object_bytes(x,m);let arc=archive(m,x,raw)?;fs::write(&a[13],&arc).map_err(|e|e.to_string())?;let exe=env::current_exe().map_err(|e|e.to_string())?;let out=Path::new(&a[14]);let ok=std::process::Command::new(exe).args(["decode",&a[13],out.to_str().ok_or_else(||err("nonutf8"))?]).status().map_err(|e|e.to_string())?.success()&&read_bounded(out,MAX_LEN as usize)?==source;if !ok{return Err(err("fresh archive-only restore failed"))}println!("{{\"complete_bytes\":{},\"source_bytes\":{},\"fresh_archive_only_decode\":true}}",arc.len(),source.len());Ok(())},Some("decode")if a.len()==4=>{let d=read_bounded(&a[2],128)?;let(m,x)=restore(&d)?;fs::write(&a[3],object_bytes(x,m)).map_err(|e|e.to_string())?;Ok(())},_=>Err(err("usage: csp count DOMAIN N MASK EQ MODPOS MODULUS RESIDUE HISTVALUE HISTCOUNT | csp encode DOMAIN N MASK EQ MODPOS MODULUS RESIDUE HISTVALUE HISTCOUNT raw|rank OBJECT ARCHIVE RESTORED | csp decode ARCHIVE OUT"))}
}
