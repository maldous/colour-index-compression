//! Bounded NCSL v2 support diagnostic.
//!
//! NCSL v2 has one support per archive: `(source length, stride, mask)` is
//! already global header state, and lane payloads are opaque self-contained
//! coder frames.  There is no transmitted support alphabet, support table, or
//! repeated support sequence to factor.  This file deliberately reports that
//! boundary instead of defining a new uniform-support codec and crediting its
//! model bytes to the existing lane experiment.

use std::{
    env,
    fs::{self, File},
    io::Read,
};

const MAGIC: &[u8; 4] = b"NCSL";
const VERSION: u8 = 2;
const HEADER_BYTES: usize = 17;
const LANE_METADATA_BYTES: usize = 9;
const MAX_SOURCE: usize = 4096;
const MAX_ARCHIVE: usize = 32768;

fn read(path: &str) -> Result<Vec<u8>, String> {
    let metadata = fs::metadata(path).map_err(|error| format!("input metadata: {error}"))?;
    if !metadata.is_file() || metadata.len() > MAX_ARCHIVE as u64 {
        return Err("input exceeds archive bound".into());
    }
    let file = File::open(path).map_err(|error| format!("input open: {error}"))?;
    let mut bytes = Vec::new();
    file.take((MAX_ARCHIVE + 1) as u64)
        .read_to_end(&mut bytes)
        .map_err(|error| format!("input read: {error}"))?;
    if bytes.len() > MAX_ARCHIVE {
        Err("input exceeds archive bound".into())
    } else {
        Ok(bytes)
    }
}
fn u32at(bytes: &[u8], position: &mut usize) -> Result<usize, String> {
    let end = position.checked_add(4).ok_or("u32 offset overflow")?;
    let field = bytes.get(*position..end).ok_or("truncated u32")?;
    *position = end;
    Ok(u32::from_le_bytes(field.try_into().map_err(|_| "invalid u32")?) as usize)
}
fn inspect(bytes: &[u8]) -> Result<(usize, usize, u8, usize, usize), String> {
    if bytes.len() < HEADER_BYTES
        || bytes.len() > MAX_ARCHIVE
        || bytes.get(..4) != Some(MAGIC)
        || bytes[4] != VERSION
    {
        return Err("requires bounded NCSL v2 archive".into());
    }
    let mut position = 5;
    let source_len = u32at(bytes, &mut position)?;
    let _source_crc = u32at(bytes, &mut position)?;
    let stride = *bytes.get(position).ok_or("truncated stride")? as usize;
    position += 1;
    let mask = *bytes.get(position).ok_or("truncated mask")?;
    position += 1;
    let count_end = position
        .checked_add(2)
        .ok_or("lane count offset overflow")?;
    let lane_count = u16::from_le_bytes(
        bytes
            .get(position..count_end)
            .ok_or("truncated lane count")?
            .try_into()
            .map_err(|_| "invalid lane count")?,
    ) as usize;
    position = count_end;
    if source_len > MAX_SOURCE
        || !(1..=8).contains(&stride)
        || mask & 1 != 0
        || (mask as usize >> stride) != 0
    {
        return Err("invalid NCSL support".into());
    }
    if source_len == 0 {
        if stride != 1 || mask != 0 || lane_count != 0 {
            return Err("noncanonical empty NCSL".into());
        }
    } else if stride > source_len || lane_count != stride {
        return Err("invalid NCSL lane count".into());
    }
    let mut payload_bytes = 0usize;
    for offset in 0..lane_count {
        let route = *bytes.get(position).ok_or("truncated route")?;
        if route > 3 {
            return Err("invalid route".into());
        }
        position += 1;
        let decoded_len = u32at(bytes, &mut position)?;
        let payload_len = u32at(bytes, &mut position)?;
        if decoded_len != (source_len - offset).div_ceil(stride) || decoded_len > MAX_SOURCE {
            return Err("invalid lane length".into());
        }
        let end = position
            .checked_add(payload_len)
            .ok_or("payload offset overflow")?;
        bytes.get(position..end).ok_or("truncated payload")?;
        position = end;
        payload_bytes = payload_bytes
            .checked_add(payload_len)
            .ok_or("payload size overflow")?;
    }
    if position != bytes.len() {
        return Err("trailing NCSL bytes".into());
    }
    Ok((source_len, stride, mask, lane_count, payload_bytes))
}
fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    let [command, input] = args.as_slice() else {
        return Err("usage: shared_lane_supports inspect NCSL_V2_ARCHIVE".into());
    };
    if command != "inspect" {
        return Err("usage: shared_lane_supports inspect NCSL_V2_ARCHIVE".into());
    }
    let archive = read(input)?;
    let (source_bytes, stride, mask, lane_count, payload_bytes) = inspect(&archive)?;
    let metadata_bytes = lane_count * LANE_METADATA_BYTES;
    println!("{{\"source_bytes\":{},\"archive_bytes\":{},\"stride\":{},\"mask\":{},\"lane_count\":{},\"header_bytes\":17,\"lane_metadata_bytes\":{},\"payload_bytes\":{},\"support_scope\":\"single-global-stride-mask\",\"shared_support_status\":\"already-transmitted-once\",\"compressed_metadata_control\":\"not-run-no-separate-model\",\"diagram_status\":\"not-applicable-single-support\",\"new_archive\":false}}", source_bytes, archive.len(), stride, mask, lane_count, metadata_bytes, payload_bytes);
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("shared_lane_supports: {error}");
        std::process::exit(1);
    }
}
