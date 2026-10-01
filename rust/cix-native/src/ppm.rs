//! Bounded-order PPM compatible with deterministic payload versions 2 through 5.
use crate::rank::{ArithmeticDecoder, ArithmeticEncoder};
use std::collections::HashMap;

type Tables = HashMap<Vec<u8>, Vec<(u8, u32)>>;
type SeeKey = (usize, u8, u8);
type SeeStates = HashMap<SeeKey, (u32, u32)>;

const SEE_PRIOR_ESCAPE: u32 = 1;
const SEE_PRIOR_HIT: u32 = 2;
const SEE_RESCALE_LIMIT: u32 = 256;
const HISTORY_MAX: usize = 65_536;
const HISTORY_MIN: usize = 4_096;

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

fn observe_from(
    tables: &mut Tables,
    history: &mut Vec<u8>,
    symbol: u8,
    max_order: usize,
    min_order: usize,
) {
    let highest = max_order.min(history.len());
    let min_order = min_order.min(highest);
    for order in (min_order..=highest).rev() {
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

fn observe(tables: &mut Tables, history: &mut Vec<u8>, symbol: u8, max_order: usize) {
    observe_from(tables, history, symbol, max_order, 0);
}

fn update_floor(tables: &Tables, history: &[u8], symbol: u8, max_order: usize) -> usize {
    let highest = max_order.min(history.len());
    for order in (0..=highest).rev() {
        if tables.get(&context(history, order)).is_some_and(|counts| {
            counts
                .binary_search_by_key(&symbol, |(value, _)| *value)
                .is_ok()
        }) {
            return order;
        }
    }
    0
}

fn training_start(prefix_length: usize, source_length: usize) -> usize {
    let training = prefix_length
        .min(HISTORY_MAX)
        .min(HISTORY_MIN.max(source_length.saturating_mul(2)));
    prefix_length - training
}

fn prime(
    prefix_history: &[u8],
    source_length: usize,
    max_order: usize,
    update_exclusion: bool,
) -> (Tables, Vec<u8>) {
    let mut tables = Tables::new();
    let mut history = Vec::with_capacity(max_order);
    if prefix_history.is_empty() {
        return (tables, history);
    }
    let start = training_start(prefix_history.len(), source_length);
    if max_order > 0 && start > 0 {
        history.extend_from_slice(&prefix_history[start.saturating_sub(max_order)..start]);
    }
    for &symbol in &prefix_history[start..] {
        let floor = if update_exclusion {
            update_floor(&tables, &history, symbol, max_order)
        } else {
            0
        };
        observe_from(&mut tables, &mut history, symbol, max_order, floor);
    }
    (tables, history)
}

fn escape_mass(symbols: &[(u8, u32)], method: u8) -> Result<usize, String> {
    match method {
        0 => Ok(1),
        1 => Ok(symbols.len().max(1)),
        2 => Ok(symbols.len().div_ceil(2).max(1)),
        3 => Ok(symbols
            .iter()
            .filter(|(_, count)| *count == 1)
            .count()
            .max(1)),
        _ => Err("unsupported PPM escape method".into()),
    }
}

fn bit_bucket(value: usize, maximum: u8) -> u8 {
    let value = value.max(1);
    ((usize::BITS - value.leading_zeros() - 1) as u8).min(maximum)
}

fn see_key(order: usize, symbols: &[(u8, u32)]) -> SeeKey {
    let total = symbols
        .iter()
        .map(|(_, count)| *count as usize)
        .sum::<usize>();
    (order, bit_bucket(symbols.len(), 7), bit_bucket(total, 15))
}

fn see_state(states: &SeeStates, key: SeeKey) -> (u32, u32) {
    states
        .get(&key)
        .copied()
        .unwrap_or((SEE_PRIOR_ESCAPE, SEE_PRIOR_HIT))
}

fn see_update(states: &mut SeeStates, key: SeeKey, escaped: bool) {
    let (mut escape_count, mut hit_count) = see_state(states, key);
    if escaped {
        escape_count += 1;
    } else {
        hit_count += 1;
    }
    if escape_count + hit_count > SEE_RESCALE_LIMIT {
        escape_count = ((escape_count + 1) / 2).max(1);
        hit_count = ((hit_count + 1) / 2).max(1);
    }
    states.insert(key, (escape_count, hit_count));
}

fn prime_see(
    prefix_history: &[u8],
    source_length: usize,
    max_order: usize,
    update_exclusion: bool,
) -> (Tables, Vec<u8>, SeeStates) {
    let mut tables = Tables::new();
    let mut history = Vec::with_capacity(max_order);
    let mut states = SeeStates::new();
    if prefix_history.is_empty() {
        return (tables, history, states);
    }
    let start = training_start(prefix_history.len(), source_length);
    if max_order > 0 && start > 0 {
        history.extend_from_slice(&prefix_history[start.saturating_sub(max_order)..start]);
    }
    for &symbol in &prefix_history[start..] {
        let mut excluded = [false; 256];
        let mut matched_order = 0;
        let highest = max_order.min(history.len());
        for order in (0..=highest).rev() {
            let Some(counts) = tables.get(&context(&history, order)) else {
                continue;
            };
            let symbols = eligible(counts, &excluded);
            if symbols.is_empty() {
                continue;
            }
            let key = see_key(order, &symbols);
            let hit = !excluded[symbol as usize]
                && counts
                    .binary_search_by_key(&symbol, |(value, _)| *value)
                    .is_ok();
            see_update(&mut states, key, !hit);
            if hit {
                matched_order = order;
                break;
            }
            for (value, _) in symbols {
                excluded[value as usize] = true;
            }
        }
        observe_from(
            &mut tables,
            &mut history,
            symbol,
            max_order,
            if update_exclusion { matched_order } else { 0 },
        );
    }
    (tables, history, states)
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
    decode_with_history(blob, source_length, &[])
}
pub fn decode_with_history(
    blob: &[u8],
    source_length: usize,
    prefix_history: &[u8],
) -> Result<Vec<u8>, String> {
    if blob.len() < 3 || !matches!(blob[0], 2..=5) {
        return Err("unsupported PPM payload version".into());
    }
    let version = blob[0];
    let max_order = blob[1] as usize;
    if max_order > 8 {
        return Err("unsupported PPM order".into());
    }
    if version == 5 {
        if blob[2] & !1 != 0 {
            return Err("unsupported PPM SEE flags".into());
        }
    } else if blob[2] > 3 {
        return Err("unsupported PPM escape method".into());
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
    if version == 5 {
        return decode_see(
            &blob[pos..end],
            bit_length,
            source_length,
            prefix_history,
            max_order,
            blob[2] & 1 != 0,
        );
    }
    let escape_method = blob[2];
    let update_exclusion = version == 4;
    let (mut tables, mut history) = if version == 2 {
        (
            Tables::new(),
            prefix_history[prefix_history.len().saturating_sub(max_order)..].to_vec(),
        )
    } else {
        prime(prefix_history, source_length, max_order, update_exclusion)
    };
    let mut decoder = ArithmeticDecoder::new(&blob[pos..end], bit_length);
    let mut out = Vec::with_capacity(source_length);
    for _ in 0..source_length {
        let mut excluded = [false; 256];
        let mut symbol = None;
        let mut matched_order = 0;
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
            let escape = escape_mass(&symbols, escape_method)?;
            let total = mass + escape;
            let target = decoder.target(total);
            if target < mass {
                let mut low = 0usize;
                for (candidate, count) in symbols {
                    let high = low + count as usize;
                    if target < high {
                        decoder.update(low, high, total);
                        symbol = Some(candidate);
                        matched_order = order;
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
        observe_from(
            &mut tables,
            &mut history,
            value,
            max_order,
            if update_exclusion { matched_order } else { 0 },
        );
    }
    Ok(out)
}

fn decode_see(
    payload: &[u8],
    bit_length: usize,
    source_length: usize,
    prefix_history: &[u8],
    max_order: usize,
    update_exclusion: bool,
) -> Result<Vec<u8>, String> {
    let (mut tables, mut history, mut states) =
        prime_see(prefix_history, source_length, max_order, update_exclusion);
    let mut decoder = ArithmeticDecoder::new(payload, bit_length);
    let mut out = Vec::with_capacity(source_length);
    for _ in 0..source_length {
        let mut excluded = [false; 256];
        let mut symbol = None;
        let mut matched_order = 0;
        let highest = max_order.min(history.len());
        for order in (0..=highest).rev() {
            let Some(counts) = tables.get(&context(&history, order)) else {
                continue;
            };
            let symbols = eligible(counts, &excluded);
            if symbols.is_empty() {
                continue;
            }
            let key = see_key(order, &symbols);
            let (escape_count, hit_count) = see_state(&states, key);
            let event_total = (escape_count + hit_count) as usize;
            let target = decoder.target(event_total);
            if target < hit_count as usize {
                decoder.update(0, hit_count as usize, event_total);
                let mass = symbols
                    .iter()
                    .map(|(_, count)| *count as usize)
                    .sum::<usize>();
                let symbol_target = decoder.target(mass);
                let mut low = 0usize;
                for (candidate, count) in symbols {
                    let high = low + count as usize;
                    if symbol_target < high {
                        decoder.update(low, high, mass);
                        symbol = Some(candidate);
                        matched_order = order;
                        break;
                    }
                    low = high;
                }
                if symbol.is_none() {
                    return Err("PPM SEE symbol interval not found".into());
                }
                see_update(&mut states, key, false);
                break;
            }
            decoder.update(hit_count as usize, event_total, event_total);
            see_update(&mut states, key, true);
            for (value, _) in symbols {
                excluded[value as usize] = true;
            }
        }
        let value = if let Some(value) = symbol {
            value
        } else {
            let remaining = (0..=255)
                .filter(|&value| !excluded[value as usize])
                .collect::<Vec<u8>>();
            if remaining.is_empty() {
                return Err("PPM SEE fallback alphabet is empty".into());
            }
            let target = decoder.target(remaining.len());
            let value = *remaining
                .get(target)
                .ok_or("PPM SEE fallback target outside alphabet")?;
            decoder.update(target, target + 1, remaining.len());
            value
        };
        out.push(value);
        observe_from(
            &mut tables,
            &mut history,
            value,
            max_order,
            if update_exclusion { matched_order } else { 0 },
        );
    }
    Ok(out)
}
