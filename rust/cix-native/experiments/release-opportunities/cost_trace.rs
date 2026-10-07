//! PRED-COST-1: physical payload accounting for existing native routes only.
use std::{env, fs};

const CAP: usize = 16 * 1024;
mod combinatorics { include!(concat!(env!("CIX_RELEASE_SOURCE"), "/combinatorics.rs")); }
mod rank { include!(concat!(env!("CIX_RELEASE_SOURCE"), "/rank.rs")); }
mod limits { include!(concat!(env!("CIX_RELEASE_SOURCE"), "/limits.rs")); }
mod zpaq_context { include!(concat!(env!("CIX_RELEASE_SOURCE"), "/zpaq_context.rs")); }
mod adaptive { include!(concat!(env!("CIX_RELEASE_SOURCE"), "/adaptive.rs")); }
mod ppm { include!(concat!(env!("CIX_RELEASE_SOURCE"), "/ppm.rs")); }
mod fixedmix { include!(concat!(env!("CIX_RELEASE_SOURCE"), "/fixedmix.rs")); }

fn varint_end(blob: &[u8], mut pos: usize) -> Result<usize, String> {
    for _ in 0..10 { let byte=*blob.get(pos).ok_or("truncated varint")?; pos+=1; if byte<128 { return Ok(pos); } }
    Err("oversized varint".into())
}
fn crc32(bytes: &[u8]) -> u32 {
    let mut crc=!0u32; for &byte in bytes { crc^=u32::from(byte); for _ in 0..8 { crc=(crc>>1)^(0xedb8_8320u32 & (0u32.wrapping_sub(crc&1))); } } !crc
}
fn row(name: &str, blob: Vec<u8>, metadata: usize, restored: Vec<u8>, source: &[u8], ideal: Option<f64>) -> Result<String,String> {
    if restored != source { return Err(format!("{name} fresh in-process decode mismatch")); }
    let payload=blob.len().checked_sub(metadata).ok_or("metadata exceeds blob")?;
    Ok(format!("{{\"route\":\"{name}\",\"payload_total_bytes\":{},\"metadata_header_bytes\":{metadata},\"arithmetic_payload_bytes\":{payload},\"termination_not_separable\":true,\"finite_precision_and_termination_residual_bytes\":null,\"payload_crc32\":\"{:08x}\",\"ideal_loss_bits\":{}}}", blob.len(),crc32(&blob),ideal.map_or("null".into(),|v|format!("{v:.17e}"))))
}
fn main() -> Result<(),String> {
    let mut args=env::args().skip(1); let input=args.next().ok_or("usage: cost_trace INPUT OUTPUT.json")?; let output=args.next().ok_or("usage: cost_trace INPUT OUTPUT.json")?;
    if args.next().is_some(){return Err("usage: cost_trace INPUT OUTPUT.json".into());}
    let source=fs::read(input).map_err(|e|format!("read input: {e}"))?; if source.len()>CAP{return Err(format!("input exceeds {CAP}-byte cap"));}
    let mut rows=Vec::new();
    let o0=adaptive::encode_general(&source,0,8,&[],1)?; rows.push(row("adaptive_o0",o0.clone(),varint_end(&o0,3)?,adaptive::decode(&o0,source.len())?,&source,None)?);
    let o1=adaptive::encode_general(&source,1,8,&[],256)?; rows.push(row("adaptive_o1",o1.clone(),varint_end(&o1,3)?,adaptive::decode_general(&o1,source.len(),&[],256)?,&source,None)?);
    let p=ppm::encode_fixed(&source,3,&[],1,false)?; rows.push(row("ppm_o3_e1",p.clone(),varint_end(&p,3)?,ppm::decode(&p,source.len())?,&source,None)?);
    let v1=fixedmix::encode_with_history_eta(&source,&[],6)?; rows.push(row("fixedmix_v1_eta6",v1.clone(),varint_end(&v1,2)?,fixedmix::decode(&v1,source.len())?,&source,None)?);
    for (name,config) in [("fixedmix_v3_n1_eta6",zpaq_context::Config{bucket_bits:4,max_distance:1024}), ("fixedmix_v3_n2_eta6",zpaq_context::Config{bucket_bits:6,max_distance:16384})] {
        let blob=fixedmix::encode_with_recurrence_eta(&source,&[],6,config)?; rows.push(row(name,blob.clone(),varint_end(&blob,9)?,fixedmix::decode(&blob,source.len())?,&source,None)?);
    }
    fs::write(output,format!("{{\"experiment\":\"PRED-COST-1\",\"input_bytes\":{},\"complete_archive_claim\":false,\"rows\":[{}]}}\n",source.len(),rows.join(","))).map_err(|e|format!("write output: {e}"))?; Ok(())
}
