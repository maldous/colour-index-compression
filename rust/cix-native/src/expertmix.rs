//! Decoder for legacy CIXM6 mode 17 context-expert payloads.
//!
//! The selected expert is derived from exponentially decayed log loss, so no
//! selector stream is stored.  Keep the floating-point update order identical
//! to the frozen Python reference: changing it can change the selected model
//! and therefore the arithmetic-code intervals.

use crate::rank::ArithmeticDecoder;
use std::collections::HashMap;

const VERSION: u8 = 1;
const CONTEXT_LIMIT: u32 = 4096;
const DECAY: f64 = 0.98;

type Counts = Vec<(u8, u32)>;
type Table = HashMap<Vec<u8>, Counts>;

fn read_varint(data: &[u8], pos: &mut usize) -> Result<usize, String> {
    let mut value = 0usize;
    for shift in (0..=70).step_by(7) {
        let byte = *data
            .get(*pos)
            .ok_or("truncated context-expert bit length")?;
        *pos += 1;
        let part = (byte & 0x7f) as usize;
        value |= part
            .checked_shl(shift as u32)
            .ok_or("context-expert bit length overflow")?;
        if byte < 128 {
            return Ok(value);
        }
    }
    Err("oversized context-expert bit length".into())
}

fn count(counts: Option<&Counts>, symbol: u8) -> u32 {
    counts
        .and_then(|values| {
            values
                .binary_search_by_key(&symbol, |(candidate, _)| *candidate)
                .ok()
                .map(|index| values[index].1)
        })
        .unwrap_or(0)
}

fn total(counts: Option<&Counts>) -> usize {
    counts
        .map(|values| values.iter().map(|(_, n)| *n as usize).sum())
        .unwrap_or(0)
        + 256
}

fn update_loss(loss: f64, counts: Option<&Counts>, symbol: u8) -> f64 {
    let model_total = total(counts) as f64;
    let symbol_mass = (count(counts, symbol) + 1) as f64;
    let instantaneous = model_total.log2() - symbol_mass.log2();
    loss * DECAY + instantaneous
}

fn decode_symbol(
    decoder: &mut ArithmeticDecoder<'_>,
    counts: Option<&Counts>,
) -> Result<u8, String> {
    let model_total = total(counts);
    let target = decoder.target(model_total);
    let mut cumulative = 0usize;
    for symbol in 0..=u8::MAX {
        let frequency = count(counts, symbol) as usize + 1;
        let high = cumulative + frequency;
        if target < high {
            decoder.update(cumulative, high, model_total);
            return Ok(symbol);
        }
        cumulative = high;
    }
    Err("context-expert target outside alphabet".into())
}

fn observe(counts: &mut Counts, symbol: u8) {
    match counts.binary_search_by_key(&symbol, |(candidate, _)| *candidate) {
        Ok(index) => counts[index].1 += 1,
        Err(index) => counts.insert(index, (symbol, 1)),
    }
    let sum: u32 = counts.iter().map(|(_, n)| *n).sum();
    if sum > CONTEXT_LIMIT {
        for (_, n) in counts {
            *n = (*n + 1) / 2;
        }
    }
}

/// Decode while enforcing a cap on the total number of allocated contexts.
///
/// Prefix bytes seed only the causal context window.  The Python reference
/// starts every expert's count tables empty for each payload.
pub fn decode_bounded(
    blob: &[u8],
    source_length: usize,
    prefix_history: &[u8],
    max_contexts: usize,
) -> Result<Vec<u8>, String> {
    if blob.len() < 2 || blob[0] != VERSION {
        return Err("unknown context-expert version".into());
    }
    let order_count = blob[1] as usize;
    if !(1..=9).contains(&order_count) || blob.len() < 2 + order_count {
        return Err("invalid context-expert order count".into());
    }
    let orders = &blob[2..2 + order_count];
    if orders[0] != 0
        || orders.last().copied().unwrap_or(9) > 8
        || orders.windows(2).any(|pair| pair[0] >= pair[1])
    {
        return Err("invalid context-expert orders".into());
    }

    let mut pos = 2 + order_count;
    let bit_length = read_varint(blob, &mut pos)?;
    let byte_length = bit_length
        .checked_add(7)
        .ok_or("context-expert bit length overflow")?
        / 8;
    let end = pos
        .checked_add(byte_length)
        .ok_or("context-expert payload length overflow")?;
    if end != blob.len() {
        return Err("context-expert payload length mismatch".into());
    }

    let max_order = orders[order_count - 1] as usize;
    let history_start = prefix_history.len().saturating_sub(max_order);
    let mut history = prefix_history[history_start..].to_vec();
    let mut tables: Vec<Table> = (0..order_count).map(|_| HashMap::new()).collect();
    let mut losses = vec![0.0f64; order_count];
    let mut contexts = Vec::with_capacity(order_count);
    let mut context_count = 0usize;
    let mut decoder = ArithmeticDecoder::new(&blob[pos..end], bit_length);
    let mut out = Vec::new();
    out.try_reserve_exact(source_length)
        .map_err(|_| "context-expert output exceeds available memory")?;

    for _ in 0..source_length {
        contexts.clear();
        for &order in orders {
            let order = order as usize;
            contexts.push(if order == 0 {
                Vec::new()
            } else {
                history[history.len().saturating_sub(order)..].to_vec()
            });
        }

        let mut selected = 0usize;
        for index in 1..order_count {
            if losses[index] < losses[selected] {
                selected = index;
            }
        }
        let symbol = decode_symbol(&mut decoder, tables[selected].get(&contexts[selected]))?;
        out.push(symbol);

        for index in 0..order_count {
            losses[index] = update_loss(losses[index], tables[index].get(&contexts[index]), symbol);
        }
        for index in 0..order_count {
            if !tables[index].contains_key(&contexts[index]) {
                if context_count >= max_contexts {
                    return Err("context-expert model exceeds memory budget".into());
                }
                tables[index].insert(contexts[index].clone(), Vec::new());
                context_count += 1;
            }
            observe(
                tables[index]
                    .get_mut(&contexts[index])
                    .expect("inserted context is present"),
                symbol,
            );
        }

        if max_order > 0 {
            history.push(symbol);
            if history.len() > max_order {
                history.remove(0);
            }
        }
    }
    Ok(out)
}

pub fn decode_with_history(
    blob: &[u8],
    source_length: usize,
    prefix_history: &[u8],
) -> Result<Vec<u8>, String> {
    decode_bounded(blob, source_length, prefix_history, usize::MAX)
}

pub fn decode(blob: &[u8], source_length: usize) -> Result<Vec<u8>, String> {
    decode_with_history(blob, source_length, &[])
}
