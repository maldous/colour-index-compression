//! Historic MyISAM-specialist admission and CIXD envelopes.
//!
//! The transform itself is intentionally a separate callback seam while the
//! shared exact composition/range primitives are finalised.  That prevents a
//! near-equivalent rank implementation from creating archives this decoder
//! cannot read.

use super::arithmetic::{
    fixed_be, multinomial_cardinality, read_fixed, vdecode, vencode, verify_frame,
    ArithmeticDecoder, ArithmeticEncoder, Fenwick,
};
use num_bigint::BigUint;
use num_traits::{ToPrimitive, Zero};

pub const RECORD_MAGIC: &[u8] = b"CIXD\x01";
pub const FIXED_MAGIC: &[u8] = b"CIXD\x02";
pub const RECORD_RAW_MAGIC: &[u8] = b"MYCS1";
pub const FIXED_RAW_MAGIC: &[u8] = b"MYCC1";
pub type EncodeBackend<'a> = dyn Fn(&[u8]) -> Result<Vec<u8>, String> + 'a;
pub type DecodeBackend<'a> = dyn Fn(&[u8], usize) -> Result<Vec<u8>, String> + 'a;

pub fn admit_mysql_records(data: &[u8]) -> bool {
    data.len() >= 3 && matches!(data[0], 1 | 3) && u16::from_be_bytes([data[1], data[2]]) != 0
}
pub fn admit_mysql_record_constraints(data: &[u8]) -> bool {
    admit_mysql_records(data)
}
pub fn admit_mysql_remaining_counts(data: &[u8]) -> bool {
    admit_mysql_records(data)
}
pub fn admit_mysql_fixed_columns(data: &[u8]) -> bool {
    admit_mysql_records(data)
}
pub fn recognizes_frame(frame: &[u8]) -> bool {
    frame.starts_with(RECORD_MAGIC) || frame.starts_with(FIXED_MAGIC)
}

/// Exact `mysql_remaining_counts.order_encode` port.  Modes match the legacy
/// transform: 1 literal; 2 static arithmetic; 3 dynamic arithmetic; 4 exact
/// type-class/permutation rank where bounded.
pub fn remaining_count_order_encode(
    ids: &[usize],
    counts: &[usize],
    mode: u8,
) -> Result<Vec<u8>, String> {
    let count = counts.iter().try_fold(0usize, |sum, &n| {
        sum.checked_add(n).ok_or("ordering length overflow")
    })?;
    if count != ids.len() {
        return Err("ordering composition mismatch".into());
    }
    let mut observed = vec![0usize; counts.len()];
    for &id in ids {
        let tally = observed
            .get_mut(id)
            .ok_or("ordering symbol outside composition")?;
        *tally = tally.checked_add(1).ok_or("ordering count overflow")?;
    }
    if observed != counts {
        return Err("ordering composition mismatch".into());
    }
    if ids.iter().any(|&id| id >= counts.len()) {
        return Err("ordering symbol outside composition".into());
    }
    if mode == 1 {
        let mut out = vec![0];
        for &id in ids {
            out.extend(vencode(id as u64));
        }
        return Ok(out);
    }
    if mode == 4 && counts.iter().all(|&n| n == 1) {
        return permutation_blocks_encode(ids, counts);
    }
    if mode == 4 && ids.len() <= 4096 {
        return type_class_rank_encode(ids, counts);
    }
    let dynamic = mode != 2;
    let mut tree = Fenwick::new(counts)?;
    let mut mutable = counts.to_vec();
    let mut remaining = ids.len();
    let mut coder = ArithmeticEncoder::new();
    for &id in ids {
        if mutable[id] == 0 {
            return Err("ordering composition mismatch".into());
        };
        let low = u64::try_from(tree.prefix(id)?).map_err(|_| "negative arithmetic prefix")?;
        let hi = low
            .checked_add(mutable[id] as u64)
            .ok_or("arithmetic interval overflow")?;
        coder.encode(low, hi, remaining as u64)?;
        if dynamic {
            mutable[id] -= 1;
            tree.add(id, -1)?;
            remaining -= 1;
        }
    }
    let (payload, bits) = coder.finish();
    let mut out = vec![if dynamic { 2 } else { 1 }];
    out.extend(vencode(bits as u64));
    out.extend(payload);
    Ok(out)
}
pub fn remaining_count_order_decode(blob: &[u8], counts: &[usize]) -> Result<Vec<usize>, String> {
    let kind = *blob.first().ok_or("missing ordering mode")?;
    let n: usize = counts.iter().try_fold(0usize, |a, &v| {
        a.checked_add(v).ok_or("ordering length overflow")
    })?;
    let out = match kind {
        0 => {
            let mut p = 1;
            let mut v = Vec::with_capacity(n);
            for _ in 0..n {
                let (x, q) = vdecode(blob, p)?;
                p = q;
                let x = usize::try_from(x).map_err(|_| "ordering symbol overflow")?;
                v.push(x)
            }
            if p != blob.len() {
                return Err("trailing IDs".into());
            }
            v
        }
        1 | 2 => {
            let (bits, p) = vdecode(blob, 1)?;
            let bits = usize::try_from(bits).map_err(|_| "arithmetic bit length overflow")?;
            if blob.len().saturating_sub(p) != bits.div_ceil(8) {
                return Err("order arithmetic length".into());
            }
            let mut d = ArithmeticDecoder::new(&blob[p..], bits)?;
            let mut tree = Fenwick::new(counts)?;
            let mut m = counts.to_vec();
            let mut rem = n;
            let mut v = Vec::with_capacity(n);
            for _ in 0..n {
                let t = i128::try_from(d.target(rem as u64)?)
                    .map_err(|_| "arithmetic target overflow")?;
                let s = tree.select(t)?;
                let lo =
                    u64::try_from(tree.prefix(s)?).map_err(|_| "negative arithmetic prefix")?;
                d.update(lo, lo + m[s] as u64, rem as u64)?;
                v.push(s);
                if kind == 2 {
                    if m[s] == 0 {
                        return Err("ordering composition mismatch".into());
                    };
                    m[s] -= 1;
                    tree.add(s, -1)?;
                    rem -= 1
                }
            }
            v
        }
        3 => type_class_rank_decode(blob, counts)?,
        4 => permutation_blocks_decode(blob, counts)?,
        _ => return Err("invalid ordering mode".into()),
    };
    let mut observed = vec![0usize; counts.len()];
    for &id in &out {
        if id >= counts.len() {
            return Err("ordering symbol outside composition".into());
        }
        observed[id] = observed[id]
            .checked_add(1)
            .ok_or("ordering count overflow")?
    }
    if observed != counts {
        return Err("ordering composition mismatch".into());
    }
    Ok(out)
}
fn type_class_rank_encode(ids: &[usize], counts: &[usize]) -> Result<Vec<u8>, String> {
    let card = multinomial_cardinality(counts)?;
    let mut total = card.clone();
    let mut tree = Fenwick::new(counts)?;
    let mut m = counts.to_vec();
    let mut rem = ids.len();
    let mut rank = BigUint::zero();
    for &s in ids {
        if m[s] == 0 {
            return Err("ordering composition mismatch".into());
        }
        let prefix = u64::try_from(tree.prefix(s)?).map_err(|_| "negative rank prefix")?;
        rank += (&total * BigUint::from(prefix)) / rem;
        total = (&total * BigUint::from(m[s])) / rem;
        m[s] -= 1;
        tree.add(s, -1)?;
        rem -= 1
    }
    let mut out = vec![3];
    out.extend(fixed_be(
        &rank,
        (&card - BigUint::from(1u8)).bits() as usize,
    )?);
    Ok(out)
}
fn type_class_rank_decode(blob: &[u8], counts: &[usize]) -> Result<Vec<usize>, String> {
    let n: usize = counts.iter().try_fold(0usize, |a, &v| {
        a.checked_add(v).ok_or("ordering length overflow")
    })?;
    if n > 4096 {
        return Err("oversized exact rank".into());
    }
    let card = multinomial_cardinality(counts)?;
    let (bits, p) = read_fixed(blob, 1, (&card - BigUint::from(1u8)).bits() as usize)?;
    if p != blob.len() || bits >= card {
        return Err("invalid type-class rank".into());
    }
    let mut rank = bits;
    let mut total = card;
    let mut tree = Fenwick::new(counts)?;
    let mut m = counts.to_vec();
    let mut rem = n;
    let mut out = Vec::with_capacity(n);
    while rem > 0 {
        let target = ((&rank * rem) / &total)
            .to_i128()
            .ok_or("rank select overflow")?;
        let s = tree.select(target)?;
        let prefix = u64::try_from(tree.prefix(s)?).map_err(|_| "negative rank prefix")?;
        rank -= (&total * BigUint::from(prefix)) / rem;
        total = (&total * BigUint::from(m[s])) / rem;
        out.push(s);
        m[s] -= 1;
        tree.add(s, -1)?;
        rem -= 1
    }
    Ok(out)
}
fn permutation_blocks_encode(ids: &[usize], counts: &[usize]) -> Result<Vec<u8>, String> {
    if counts.iter().any(|&n| n != 1) {
        return Err("not a permutation".into());
    }
    let mut out = vec![4];
    let mut tree = Fenwick::new(counts)?;
    let mut remaining = ids.len();
    for chunk in ids.chunks(1024) {
        let mut rank = BigUint::zero();
        let mut product = BigUint::from(1u8);
        for &symbol in chunk {
            let digit =
                usize::try_from(tree.prefix(symbol)?).map_err(|_| "permutation digit overflow")?;
            rank = rank * remaining + digit;
            product *= remaining;
            tree.add(symbol, -1)?;
            remaining -= 1;
        }
        out.extend(fixed_be(
            &rank,
            (&product - BigUint::from(1u8)).bits() as usize,
        )?);
    }
    Ok(out)
}

fn permutation_blocks_decode(blob: &[u8], counts: &[usize]) -> Result<Vec<usize>, String> {
    if counts.iter().any(|&n| n != 1) {
        return Err("not a permutation".into());
    }
    let mut position = 1;
    let mut tree = Fenwick::new(counts)?;
    let mut remaining = counts.len();
    let mut out = Vec::with_capacity(remaining);
    while remaining > 0 {
        let length = remaining.min(1024);
        let mut product = BigUint::from(1u8);
        for base in (remaining - length + 1)..=remaining {
            product *= base;
        }
        let (mut rank, end) = read_fixed(
            blob,
            position,
            (&product - BigUint::from(1u8)).bits() as usize,
        )?;
        position = end;
        if rank >= product {
            return Err("invalid conditional permutation rank".into());
        }
        let mut digits = vec![0usize; length];
        for index in (0..length).rev() {
            let base = BigUint::from(remaining - index);
            digits[index] = (&rank % &base)
                .to_usize()
                .ok_or("permutation digit overflow")?;
            rank /= base;
        }
        for digit in digits {
            let symbol = tree.select(digit as i128)?;
            out.push(symbol);
            tree.add(symbol, -1)?;
            remaining -= 1;
        }
    }
    if position != blob.len() {
        return Err("trailing permutation ranks".into());
    }
    Ok(out)
}

fn pack(
    magic: &[u8],
    backend_id: Option<u8>,
    source: &[u8],
    transformed: &[u8],
    encode: &EncodeBackend<'_>,
) -> Result<Vec<u8>, String> {
    let payload = encode(transformed)?;
    let mut out = Vec::with_capacity(magic.len() + 17 + payload.len());
    out.extend_from_slice(magic);
    if let Some(id) = backend_id {
        out.push(id);
    }
    out.extend(vencode(source.len() as u64));
    out.extend_from_slice(&crc32fast::hash(source).to_be_bytes());
    out.extend_from_slice(&payload);
    Ok(out)
}
fn unpack(
    magic: &[u8],
    backend_id: Option<u8>,
    frame: &[u8],
    limit: usize,
    memory: usize,
    decode: &DecodeBackend<'_>,
) -> Result<(usize, u32, Vec<u8>), String> {
    if !frame.starts_with(magic) || memory == 0 {
        return Err("invalid MyISAM frame".into());
    }
    let mut at = magic.len();
    if let Some(expected) = backend_id {
        let actual = *frame.get(at).ok_or("truncated MyISAM backend")?;
        if actual != expected {
            return Err("unexpected MyISAM backend".into());
        }
        at += 1;
    }
    let (n, p) = vdecode(frame, at)?;
    at = p;
    let n = usize::try_from(n).map_err(|_| "MyISAM output size overflow")?;
    if n > limit || n > memory {
        return Err("MyISAM output exceeds admission limit".into());
    }
    let checksum = u32::from_be_bytes(
        frame
            .get(at..at + 4)
            .ok_or("truncated MyISAM frame")?
            .try_into()
            .unwrap(),
    );
    at += 4;
    let transformed = decode(frame.get(at..).ok_or("truncated MyISAM payload")?, memory)?;
    if transformed.len() > memory {
        return Err("backend ignored transformed-output limit".into());
    }
    Ok((n, checksum, transformed))
}

/// Historic CIXD01: backend byte 0=Brotli, 1=the separately-qualified PAQ wrapper.
pub fn encode_mysql_record_constraints(
    source: &[u8],
    transformed: &[u8],
    backend_id: u8,
    backend: &EncodeBackend<'_>,
) -> Result<Vec<u8>, String> {
    if backend_id > 1 {
        return Err("invalid record backend".into());
    }
    pack(RECORD_MAGIC, Some(backend_id), source, transformed, backend)
}
pub fn decode_mysql_record_constraints(
    frame: &[u8],
    limit: usize,
    memory: usize,
    backend: &DecodeBackend<'_>,
    inverse: impl FnOnce(&[u8]) -> Result<Vec<u8>, String>,
) -> Result<Vec<u8>, String> {
    if !frame.starts_with(RECORD_MAGIC) {
        return Err("invalid MyISAM frame".into());
    };
    let id = *frame
        .get(RECORD_MAGIC.len())
        .ok_or("truncated MyISAM backend")?;
    if id > 1 {
        return Err("invalid record backend".into());
    };
    let (n, crc, t) = unpack(RECORD_MAGIC, Some(id), frame, limit, memory, backend)?;
    let out = inverse(&t)?;
    verify_frame(&out, n, crc)?;
    Ok(out)
}
/// Historic CIXD02 fixed-column frame; the codec always uses its declared Brotli provider.
pub fn encode_mysql_fixed_columns(
    source: &[u8],
    transformed: &[u8],
    backend: &EncodeBackend<'_>,
) -> Result<Vec<u8>, String> {
    pack(FIXED_MAGIC, None, source, transformed, backend)
}
pub fn decode_mysql_fixed_columns(
    frame: &[u8],
    limit: usize,
    memory: usize,
    backend: &DecodeBackend<'_>,
    inverse: impl FnOnce(&[u8]) -> Result<Vec<u8>, String>,
) -> Result<Vec<u8>, String> {
    let (n, crc, t) = unpack(FIXED_MAGIC, None, frame, limit, memory, backend)?;
    let out = inverse(&t)?;
    verify_frame(&out, n, crc)?;
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn each_order_code_restores_nontrivial_composition() {
        let ids = [2, 0, 2, 1, 0, 2];
        let counts = [2, 1, 3];
        for mode in 1..=4 {
            let encoded = remaining_count_order_encode(&ids, &counts, mode).unwrap();
            assert_eq!(
                remaining_count_order_decode(&encoded, &counts).unwrap(),
                ids
            );
        }
        assert!(remaining_count_order_encode(&[0, 0], &[1, 1], 2).is_err());
    }
    #[test]
    fn permutation_crosses_rank_block_boundary() {
        let ids: Vec<usize> = (0..1025).rev().collect();
        let counts = vec![1; ids.len()];
        let encoded = remaining_count_order_encode(&ids, &counts, 4).unwrap();
        assert_eq!(
            remaining_count_order_decode(&encoded, &counts).unwrap(),
            ids
        );
        assert!(remaining_count_order_decode(&encoded[..encoded.len() - 1], &counts).is_err());
    }
}
