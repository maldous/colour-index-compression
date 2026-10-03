//! RNC1 paired model-cost control. Isolated framing adapter, not production CIX.
use num_bigint::BigUint;
use num_traits::One;
use std::{env, fs, io::Read};
const MODEL: usize = 256;
const OUTER: usize = 10;
const CAP: usize = 20_000;
fn read(path: &str, cap: usize) -> Result<Vec<u8>, String> {
    let mut bytes = Vec::new();
    fs::File::open(path).map_err(|e| e.to_string())?.take((cap + 1) as u64)
        .read_to_end(&mut bytes).map_err(|e| e.to_string())?;
    if bytes.len() > cap { return Err("resource bound".into()); }
    Ok(bytes)
}
fn crc(data: &[u8]) -> u32 {
    let mut c = !0u32;
    for &v in data { c ^= v as u32; for _ in 0..8 {
        c = if c & 1 != 0 { (c >> 1) ^ 0xedb88320 } else { c >> 1 };
    }}
    !c
}
fn u32_at(data: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes(data[offset..offset+4].try_into().unwrap())
}
fn metadata_len(codec: u8, data: &[u8]) -> Result<usize, String> {
    let header = match codec { 1 => 20, 2 => 15, _ => return Err("codec".into()) };
    if data.len() < header || data[4] != 1 || u32_at(data, 6) > 16_384 {
        return Err("inner envelope".into());
    }
    if codec == 1 {
        if &data[..4] != b"ERC1" || data[5] > 3 { return Err("ERC1 model".into()); }
        return Ok(20);
    }
    if &data[..4] != b"RDIC" || data[5] > 1 { return Err("RDIC model".into()); }
    if data[5] == 0 { return Ok(15); }
    let b = data[10] as usize;
    let m = u16::from_le_bytes(data[11..13].try_into().unwrap()) as usize;
    if !(2..=12).contains(&b) || m == 0 || m > 256 || m > 1usize << b {
        return Err("dictionary bounds".into());
    }
    let u = 1usize << b;
    let k = m.min(u - m);
    let mut n = BigUint::one();
    for j in 1..=k { n *= u-k+j; n /= j; }
    let width = (n - BigUint::one()).bits() as usize;
    let length = 15 + width.div_ceil(8);
    if length > MODEL { return Err("model budget".into()); }
    Ok(length)
}
fn pack(codec: u8, data: &[u8]) -> Result<Vec<u8>, String> {
    if data.len() < 19 || data.len() > CAP { return Err("inner length".into()); }
    let end = data.len()-4;
    if crc(&data[..end]) != u32_at(data,end) { return Err("inner CRC".into()); }
    let m = metadata_len(codec, &data[..end])?;
    if m > end { return Err("truncated model".into()); }
    let payload = &data[m..end];
    let mut out = b"RNC1".to_vec();
    out.extend([1,codec]); out.extend((payload.len() as u32).to_le_bytes());
    out.extend(&data[..m]); out.resize(OUTER+MODEL,0); out.extend(payload);
    out.extend(crc(&out).to_le_bytes());
    Ok(out)
}
fn unpack(data: &[u8]) -> Result<Vec<u8>, String> {
    if data.len() < OUTER+MODEL+4 || data.len() > OUTER+MODEL+CAP+4
        || &data[..4] != b"RNC1" || data[4] != 1 { return Err("RNC1 envelope".into()); }
    let end=data.len()-4;
    if crc(&data[..end]) != u32_at(data,end) { return Err("outer CRC".into()); }
    let payload=u32_at(data,6) as usize;
    if payload > CAP || payload != end-OUTER-MODEL { return Err("payload length".into()); }
    let m=metadata_len(data[5], &data[OUTER..OUTER+MODEL])?;
    if data[OUTER+m..OUTER+MODEL].iter().any(|&v|v!=0) { return Err("model padding".into()); }
    let mut out=data[OUTER..OUTER+m].to_vec();
    out.extend(&data[OUTER+MODEL..end]);
    out.extend(crc(&out).to_le_bytes());
    if out.len()>CAP { return Err("inner resource bound".into()); }
    Ok(out)
}
fn uniform(data: &[u8]) -> Result<Vec<u8>, String> {
    if data.is_empty() || data.len()>16_384 || data.len()%2!=0 { return Err("uniform length".into()); }
    let mut seen=[false;256];
    for &v in data { seen[v as usize]=true; }
    let alphabet: Vec<u8>=seen.iter().enumerate().filter_map(|(i,&v)|v.then_some(i as u8)).collect();
    if alphabet.len()!=2 { return Err("uniform alphabet".into()); }
    let mut rank=BigUint::from(0u8);
    for &v in data { rank<<=1; rank+=u8::from(v==alphabet[1]); }
    let width=data.len();
    let mut inner=b"ERC1".to_vec(); inner.extend([1,1]);
    inner.extend((data.len() as u32).to_le_bytes()); inner.push(2);
    inner.extend(0u16.to_le_bytes()); inner.push(0); inner.extend(&alphabet);
    inner.extend((width as u32).to_le_bytes());
    let digits=rank.to_bytes_be(); let bytes=width.div_ceil(8);
    inner.resize(20+bytes-digits.len(),0); inner.extend(digits);
    inner.extend(crc(&inner).to_le_bytes());
    pack(1,&inner)
}
fn main() -> Result<(),String> {
    let args: Vec<String>=env::args().collect();
    let (out,path)=match args.get(1).map(String::as_str) {
        Some("pack") if args.len()==5 => {
            let codec=match args[2].as_str(){"erc"=>1,"rdic"=>2,_=>return Err("codec".into())};
            (pack(codec,&read(&args[3],CAP)?)?,&args[4])
        },
        Some("uniform") if args.len()==4 => (uniform(&read(&args[2],16_384)?)?,&args[3]),
        Some("unpack") if args.len()==4 => (unpack(&read(&args[2],CAP+OUTER+MODEL+4)?)?,&args[3]),
        _=>return Err("usage: rnc pack erc|rdic INNER OUT | rnc unpack FRAME INNER | rnc uniform INPUT FRAME".into())
    };
    fs::write(path,&out).map_err(|e|e.to_string())?;
    println!("bytes={}",out.len()); Ok(())
}
