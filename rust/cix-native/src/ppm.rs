//! Bounded-order PPM route, compatible with CIXG1's deterministic version-3 payload.
use crate::rank::{ArithmeticDecoder, ArithmeticEncoder};
use std::collections::HashMap;

type Tables = HashMap<Vec<u8>, Vec<(u8, u32)>>;

fn context(history: &[u8], order: usize) -> Vec<u8> {
    if order == 0 {
        Vec::new()
    } else {
        history[history.len() - order..].to_vec()
    }
}

fn eligible(counts: &[(u8, u32)], excluded: &[bool; 256]) -> Vec<(u8, u32)> {
    counts
        .iter()
        .copied()
        .filter(|(symbol, _)| !excluded[*symbol as usize])
        .collect()
}

fn observe(tables: &mut Tables, history: &mut Vec<u8>, symbol: u8, max_order: usize) {
    let highest = max_order.min(history.len());
    for order in (0..=highest).rev() {
        let key = context(history, order);
        let counts = tables.entry(key).or_default();
        match counts.binary_search_by_key(&symbol, |(value, _)| *value) {
            Ok(index) => counts[index].1 += 1,
            Err(index) => counts.insert(index, (symbol, 1)),
        }
        if counts
            .iter()
            .map(|(_, count)| *count as usize)
            .sum::<usize>()
            > 16384
        {
            for (_, count) in counts.iter_mut() {
                *count = ((*count + 1) / 2).max(1);
            }
        }
    }
    if max_order > 0 {
        history.push(symbol);
        if history.len() > max_order {
            history.drain(..history.len() - max_order);
        }
    }
}

fn put_varint(mut value: usize, out: &mut Vec<u8>) {
    while value >= 128 {
        out.push((value as u8 & 0x7f) | 0x80);
        value >>= 7;
    }
    out.push(value as u8);
}

fn read_varint(data: &[u8], pos: &mut usize) -> Result<usize, String> {
    let mut value = 0usize;
    for shift in (0..70).step_by(7) {
        let byte = *data.get(*pos).ok_or("truncated PPM bit length")?;
        *pos += 1;
        value |= ((byte & 0x7f) as usize)
            .checked_shl(shift as u32)
            .ok_or("oversized PPM varint")?;
        if byte < 128 {
            return Ok(value);
        }
    }
    Err("oversized PPM varint".into())
}

pub fn encode(data: &[u8], max_order: usize) -> Result<Vec<u8>, String> {
    if max_order > 8 {
        return Err("PPM order exceeds supported maximum".into());
    }
    let mut tables = Tables::new();
    let mut history = Vec::with_capacity(max_order);
    let mut encoder = ArithmeticEncoder::new();
    for &symbol in data {
        let mut excluded = [false; 256];
        let mut coded = false;
        let highest = max_order.min(history.len());
        for order in (0..=highest).rev() {
            let key = context(&history, order);
            let Some(counts) = tables.get(&key) else {
                continue;
            };
            let symbols = eligible(counts, &excluded);
            if symbols.is_empty() {
                continue;
            }
            let mass: usize = symbols.iter().map(|(_, count)| *count as usize).sum();
            let total = mass + 1; // escape method 0: escape mass is one
            if let Some(index) = symbols.iter().position(|(value, _)| *value == symbol) {
                let low: usize = symbols[..index]
                    .iter()
                    .map(|(_, count)| *count as usize)
                    .sum();
                let high = low + symbols[index].1 as usize;
                encoder.encode(low, high, total);
                coded = true;
                break;
            }
            encoder.encode(mass, total, total);
            for (value, _) in symbols {
                excluded[value as usize] = true;
            }
        }
        if !coded {
            let mut remaining = 0usize;
            let mut target_rank = None;
            for symbol_id in 0..256 {
                if !excluded[symbol_id] {
                    if symbol_id == symbol as usize {
                        target_rank = Some(remaining);
                    }
                    remaining += 1;
                }
            }
            let rank = target_rank.ok_or("PPM escape excluded source symbol")?;
            encoder.encode(rank, rank + 1, remaining);
        }
        observe(&mut tables, &mut history, symbol, max_order);
    }
    let (payload, bit_length) = encoder.finish();
    let mut out = vec![3, max_order as u8, 0]; // PPM v3, fixed escape mass one
    put_varint(bit_length, &mut out);
    out.extend_from_slice(&payload);
    Ok(out)
}

pub fn decode(blob: &[u8], source_length: usize) -> Result<Vec<u8>, String> {
    if blob.len() < 3 || blob[0] != 3 {
        return Err("unsupported PPM payload version".into());
    }
    let max_order = blob[1] as usize;
    if max_order > 8 || blob[2] != 0 {
        return Err("unsupported PPM order or escape method".into());
    }
    let mut pos = 3;
    let bit_length = read_varint(blob, &mut pos)?;
    let byte_length = bit_length.div_ceil(8);
    let end = pos
        .checked_add(byte_length)
        .ok_or("PPM payload length overflow")?;
    if end != blob.len() {
        return Err("PPM payload length mismatch".into());
    }
    let mut tables = Tables::new();
    let mut history = Vec::with_capacity(max_order);
    let mut decoder = ArithmeticDecoder::new(&blob[pos..end], bit_length);
    let mut out = Vec::with_capacity(source_length);
    for _ in 0..source_length {
        let mut excluded = [false; 256];
        let mut symbol = None;
        let highest = max_order.min(history.len());
        for order in (0..=highest).rev() {
            let key = context(&history, order);
            let Some(counts) = tables.get(&key) else {
                continue;
            };
            let symbols = eligible(counts, &excluded);
            if symbols.is_empty() {
                continue;
            }
            let mass: usize = symbols.iter().map(|(_, count)| *count as usize).sum();
            let total = mass + 1;
            let target = decoder.target(total);
            if target < mass {
                let mut low = 0usize;
                for (candidate, count) in symbols {
                    let high = low + count as usize;
                    if target < high {
                        decoder.update(low, high, total);
                        symbol = Some(candidate);
                        break;
                    }
                    low = high;
                }
                if symbol.is_none() {
                    return Err("PPM symbol interval not found".into());
                }
                break;
            }
            decoder.update(mass, total, total);
            for (value, _) in symbols {
                excluded[value as usize] = true;
            }
        }
        let value = if let Some(value) = symbol {
            value
        } else {
            let remaining: Vec<u8> = (0..=255)
                .filter(|&value| !excluded[value as usize])
                .collect();
            if remaining.is_empty() {
                return Err("PPM fallback alphabet is empty".into());
            }
            let target = decoder.target(remaining.len());
            let value = *remaining
                .get(target)
                .ok_or("PPM fallback target outside alphabet")?;
            decoder.update(target, target + 1, remaining.len());
            value
        };
        out.push(value);
        observe(&mut tables, &mut history, value, max_order);
    }
    Ok(out)
}
