//! Native framing adapter for established model-metadata compression controls.
//! The underlying zstd/bzip2 programs remain explicit reference controls.
use std::{env,fs,io::Read};
const CAP:usize=40_000;
const HEADER:usize=27;
fn read(p:&str)->Result<Vec<u8>,String>{let mut v=Vec::new();fs::File::open(p).map_err(|e|e.to_string())?.take((CAP+1)as u64).read_to_end(&mut v).map_err(|e|e.to_string())?;if v.len()>CAP{return Err("bound".into());}Ok(v)}
fn crc(d:&[u8])->u32{let mut c=!0u32;for &v in d{c^=v as u32;for _ in 0..8{c=if c&1!=0{(c>>1)^0xedb88320}else{c>>1};}}!c}
fn check(d:&[u8])->Result<(),String>{if d.len()<4||crc(&d[..d.len()-4])!=u32::from_le_bytes(d[d.len()-4..].try_into().unwrap()){return Err("CRC".into());}Ok(())}
fn base_model(d:&[u8])->Result<usize,String>{
 if d.len()<19||&d[..4]!=b"MSL1"||d[4]!=1{return Err("MSL1 envelope".into());}check(d)?;
 let m=u16::from_le_bytes(d[13..15].try_into().unwrap())as usize;
 if m>21_000||15+m>d.len()-4{return Err("model length".into());}Ok(m)
}
fn outer(d:&[u8])->Result<usize,String>{
 if d.len()<HEADER+4||&d[..4]!=b"MDC1"||d[4]!=1||!(1..=2).contains(&d[5])||&d[6..10]!=b"MSL1"||d[10]!=1{return Err("MDC1 envelope".into());}check(d)?;
 let n=u16::from_le_bytes(d[21..23].try_into().unwrap())as usize;
 if HEADER+n>d.len()-4{return Err("compressed length".into());}Ok(n)
}
fn main()->Result<(),String>{
 let a:Vec<String>=env::args().collect();let(data,path)=match a.get(1).map(String::as_str){
 Some("model")if a.len()==4=>{let d=read(&a[2])?;let n=base_model(&d)?;(d[15..15+n].to_vec(),&a[3])},
 Some("pack")if a.len()==6=>{
  let codec=match a[2].as_str(){"zstd"=>1,"bzip2"=>2,_=>return Err("codec".into())};
  let base=read(&a[3])?;let n=base_model(&base)?;let model=read(&a[4])?;
  let len=u16::try_from(model.len()).map_err(|_|"compressed model length")?;
  let mut out=b"MDC1".to_vec();out.extend([1,codec]);out.extend(&base[..15]);out.extend(len.to_le_bytes());out.extend(&base[base.len()-4..]);
  debug_assert_eq!(out.len(),HEADER);out.extend(model);out.extend(&base[15+n..base.len()-4]);out.extend(crc(&out).to_le_bytes());if out.len()>CAP{return Err("outer bound".into());}(out,&a[5])
 },
 Some("extract")if a.len()==4=>{let d=read(&a[2])?;let n=outer(&d)?;(d[HEADER..HEADER+n].to_vec(),&a[3])},
 Some("unpack")if a.len()==5=>{
  let d=read(&a[2])?;let n=outer(&d)?;let model=read(&a[3])?;let need=u16::from_le_bytes(d[19..21].try_into().unwrap())as usize;
  if need>21_000||model.len()!=need{return Err("decompressed model length".into());}
  let mut out=d[6..21].to_vec();out.extend(model);out.extend(&d[HEADER+n..d.len()-4]);out.extend(&d[23..27]);
  if out.len()>CAP{return Err("inner bound".into());}base_model(&out)?;(out,&a[4])
 },
 _=>return Err("usage: mdc model BASE OUT | mdc pack zstd|bzip2 BASE COMP OUT | mdc extract FRAME COMP | mdc unpack FRAME MODEL BASE".into())};
 fs::write(path,data).map_err(|e|e.to_string())
}
