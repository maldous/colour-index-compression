//! Decoder for the frozen CIXM6 transform-chain representation (mode 7).
//!
//! The chain header selects one reversible byte/word transform followed by one
//! of the legacy CIX inner codecs.  Decoding is deliberately self-contained so
//! every length-delimited inner stream is checked before transform inversion.

use super::{adaptive, bitplane, bwt_legacy, fixedmix, histogram, ppm, rank, wavelet};
use num_bigint::BigUint;
use num_traits::{One, Zero};
use std::collections::HashMap;

const CHAIN_VERSION: u8 = 1;
const INNER_MULTINOMIAL: u8 = 1;
const INNER_CONTEXT: u8 = 2;
const INNER_LZ: u8 = 3;
const INNER_BWT: u8 = 4;
const INNER_BITPLANE: u8 = 5;
const INNER_SPARSE: u8 = 6;
const INNER_RUNS: u8 = 7;

#[derive(Clone, Copy)]
enum Endian {
    Little,
    Big,
}

#[derive(Clone, Copy)]
enum Operation {
    Xor,
    Delta,
    Delta2,
    Delta2Zigzag,
    MatchXor,
}

#[derive(Clone, Copy)]
struct Transform {
    width: usize,
    endian: Endian,
    operation: Operation,
    shuffle: bool,
    byte_lag: Option<usize>,
}

fn transform(id: u8) -> Option<Transform> {
    use Endian::{Big, Little};
    use Operation::{Delta, Delta2, Delta2Zigzag, MatchXor, Xor};
    let (width, endian, operation, shuffle, byte_lag) = match id {
        1 => (1, Little, Xor, false, Some(1)),
        2 => (2, Little, Xor, false, Some(2)),
        3 => (4, Little, Xor, false, Some(4)),
        4 => (1, Little, Delta, false, Some(1)),
        5 => (2, Little, Delta, true, None),
        6 => (4, Little, Delta, true, None),
        7 => (8, Little, Delta, true, None),
        8 => (2, Big, Delta, true, None),
        9 => (4, Big, Delta, true, None),
        10 => (8, Big, Delta, true, None),
        11 => (2, Little, Delta2, true, None),
        12 => (4, Little, Delta2, true, None),
        13 => (8, Little, Delta2, true, None),
        14 => (2, Big, Delta2, true, None),
        15 => (4, Big, Delta2, true, None),
        16 => (8, Big, Delta2, true, None),
        17 => (4, Little, Xor, true, None),
        18 => (8, Little, Xor, true, None),
        19 => (8, Little, Xor, false, Some(8)),
        20 => (12, Little, Xor, false, Some(12)),
        21 => (16, Little, Xor, false, Some(16)),
        22 => (24, Little, Xor, false, Some(24)),
        23 => (32, Little, Xor, false, Some(32)),
        24 => (64, Little, Xor, false, Some(64)),
        25 => (2, Little, Delta, false, Some(2)),
        26 => (4, Little, Delta, false, Some(4)),
        27 => (8, Little, Delta, false, Some(8)),
        28 => (16, Little, Delta, false, Some(16)),
        29 => (4, Little, Delta2Zigzag, true, None),
        30 => (8, Little, Delta2Zigzag, true, None),
        31 => (8, Big, Delta2Zigzag, true, None),
        33 => (1, Little, MatchXor, false, None),
        _ => return None,
    };
    Some(Transform {
        width,
        endian,
        operation,
        shuffle,
        byte_lag,
    })
}

fn unvar(data: &[u8], pos: &mut usize) -> Result<usize, String> {
    let mut value = 0usize;
    for shift in (0..usize::BITS as usize).step_by(7) {
        let byte = *data.get(*pos).ok_or("truncated transform-chain varint")?;
        *pos += 1;
        let low = (byte & 0x7f) as usize;
        if shift + 7 > usize::BITS as usize && low > (usize::MAX >> shift) {
            return Err("transform-chain varint overflow".into());
        }
        value |= low
            .checked_shl(shift as u32)
            .ok_or("transform-chain varint overflow")?;
        if byte < 128 {
            return Ok(value);
        }
    }
    Err("oversized transform-chain varint".into())
}

struct BitReader<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> BitReader<'a> {
    fn bit(&mut self) -> Result<usize, String> {
        if self.pos >= self.data.len().saturating_mul(8) {
            return Err("truncated transform-chain bitstream".into());
        }
        let value = ((self.data[self.pos >> 3] >> (7 - (self.pos & 7))) & 1) as usize;
        self.pos += 1;
        Ok(value)
    }

    fn bits(&mut self, width: usize) -> Result<usize, String> {
        if width >= usize::BITS as usize {
            return Err("transform-chain integer is too wide".into());
        }
        let mut value = 0usize;
        for _ in 0..width {
            value = (value << 1) | self.bit()?;
        }
        Ok(value)
    }
}

fn decode_bytes(data: &[u8], count: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    let mode = *data.first().ok_or("empty transform-chain byte substream")?;
    let mut pos = 1;
    match mode {
        0 => {
            let out = rank::decode_type_class(data, &mut pos, count)?;
            if pos != data.len() {
                return Err("trailing static byte-substream bytes".into());
            }
            Ok(out)
        }
        1 => {
            let chunk = unvar(data, &mut pos)?;
            if chunk == 0 {
                return Err("invalid byte-substream chunk size".into());
            }
            let mut out = Vec::with_capacity(count);
            while out.len() < count {
                let n = chunk.min(count - out.len());
                out.extend(rank::decode_type_class(data, &mut pos, n)?);
            }
            if pos != data.len() {
                return Err("trailing chunked byte-substream bytes".into());
            }
            Ok(out)
        }
        2 => adaptive::decode_general(&data[1..], count, &[], model_limit),
        3 => {
            if !matches!(data.get(1), Some(1 | 2)) {
                return Err("invalid context byte-substream order".into());
            }
            adaptive::decode_general(&data[2..], count, &[], model_limit)
        }
        4 => wavelet::decode(&data[1..], count),
        5 => histogram::decode_type_class(&data[1..], count),
        _ => Err(format!(
            "unsupported transform-chain byte substream mode {mode}"
        )),
    }
}

fn decode_uints(data: &[u8], count: usize, model_limit: usize) -> Result<Vec<usize>, String> {
    if count == 0 {
        return Ok(Vec::new());
    }
    let mode = *data.first().ok_or("empty transform-chain integer stream")?;
    let mut pos = 1;
    match mode {
        0 => {
            let mut out = Vec::with_capacity(count);
            for _ in 0..count {
                out.push(unvar(data, &mut pos)?);
            }
            if pos != data.len() {
                return Err("trailing transform-chain varints".into());
            }
            Ok(out)
        }
        1 => {
            let k = *data.get(pos).ok_or("missing Rice parameter")? as usize;
            pos += 1;
            let mut reader = BitReader {
                data: &data[pos..],
                pos: 0,
            };
            let mut out = Vec::with_capacity(count);
            for _ in 0..count {
                let mut quotient = 0usize;
                while reader.bit()? != 0 {
                    quotient = quotient.checked_add(1).ok_or("Rice quotient overflow")?;
                }
                let low = reader.bits(k)?;
                out.push(
                    quotient
                        .checked_shl(k as u32)
                        .ok_or("Rice integer overflow")?
                        | low,
                );
            }
            Ok(out)
        }
        2 | 3 => {
            let class_len = unvar(data, &mut pos)?;
            let end = pos
                .checked_add(class_len)
                .ok_or("integer class length overflow")?;
            if end > data.len() {
                return Err("truncated integer class stream".into());
            }
            let classes = if mode == 2 {
                let mut class_pos = 0;
                let out = rank::decode_type_class(&data[pos..end], &mut class_pos, count)?;
                if class_pos != class_len {
                    return Err("trailing integer class bytes".into());
                }
                out
            } else {
                decode_bytes(&data[pos..end], count, model_limit)?
            };
            let mut reader = BitReader {
                data: &data[end..],
                pos: 0,
            };
            let mut out = Vec::with_capacity(count);
            for width in classes {
                let width = width as usize;
                let low = reader.bits(width)?;
                out.push(
                    (1usize << width)
                        .checked_add(low)
                        .and_then(|value| value.checked_sub(1))
                        .ok_or("integer stream overflow")?,
                );
            }
            Ok(out)
        }
        _ => Err(format!("unsupported transform-chain integer mode {mode}")),
    }
}

fn decode_runs(data: &[u8], source_len: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    if data.first() != Some(&1) {
        return Err("unknown chained run-block version".into());
    }
    let mut pos = 1;
    let run_count = unvar(data, &mut pos)?;
    if run_count == 0 || run_count > source_len {
        return Err("invalid chained run count".into());
    }
    let symbol_len = unvar(data, &mut pos)?;
    let end = pos
        .checked_add(symbol_len)
        .ok_or("run symbol length overflow")?;
    if end > data.len() {
        return Err("truncated chained run symbols".into());
    }
    let mut symbol_pos = 0;
    let symbols = rank::decode_type_class(&data[pos..end], &mut symbol_pos, run_count)?;
    if symbol_pos != symbol_len {
        return Err("unused chained run-symbol bytes".into());
    }
    let lengths = decode_uints(&data[end..], run_count, model_limit)?;
    let mut out = Vec::with_capacity(source_len);
    for (symbol, minus_one) in symbols.into_iter().zip(lengths) {
        let length = minus_one.checked_add(1).ok_or("run length overflow")?;
        let new_len = out.len().checked_add(length).ok_or("run length overflow")?;
        if new_len > source_len {
            return Err("chained runs exceed source length".into());
        }
        out.resize(new_len, symbol);
    }
    if out.len() != source_len {
        return Err("chained run source length mismatch".into());
    }
    Ok(out)
}

fn choose(n: usize, k: usize) -> BigUint {
    if k > n {
        return BigUint::zero();
    }
    let k = k.min(n - k);
    let mut value = BigUint::one();
    for i in 1..=k {
        value *= n - k + i;
        value /= i;
    }
    value
}

fn fixed_width(value: &BigUint) -> usize {
    value.bits() as usize
}

fn read_fixed(data: &[u8], pos: &mut usize, width: usize) -> Result<BigUint, String> {
    let bytes = width.div_ceil(8);
    let end = pos.checked_add(bytes).ok_or("rank offset overflow")?;
    if end > data.len() {
        return Err("truncated transform-chain rank".into());
    }
    if width % 8 != 0 && bytes > 0 && data[*pos] >> (width % 8) != 0 {
        return Err("nonzero transform-chain rank padding".into());
    }
    let value = BigUint::from_bytes_be(&data[*pos..end]);
    *pos = end;
    Ok(value)
}

fn colex_unrank(
    mut rank_value: BigUint,
    count: usize,
    universe: usize,
) -> Result<Vec<usize>, String> {
    if count > universe || rank_value >= choose(universe, count) {
        return Err("colex rank outside transform-chain universe".into());
    }
    let mut result = vec![0usize; count];
    let mut upper = universe;
    for i in (1..=count).rev() {
        let mut low = i - 1;
        let mut high = upper;
        while low + 1 < high {
            let mid = low + (high - low) / 2;
            if choose(mid, i) <= rank_value {
                low = mid;
            } else {
                high = mid;
            }
        }
        result[i - 1] = low;
        rank_value -= choose(low, i);
        upper = low;
    }
    if !rank_value.is_zero() {
        return Err("invalid transform-chain colex rank".into());
    }
    Ok(result)
}

fn composition_unrank(
    rank_value: BigUint,
    total: usize,
    parts: usize,
) -> Result<Vec<usize>, String> {
    if parts == 0 || total < parts || rank_value >= choose(total - 1, parts - 1) {
        return Err("composition rank outside transform-chain class".into());
    }
    if parts == 1 {
        return Ok(vec![total]);
    }
    let bars = colex_unrank(rank_value, parts - 1, total - 1)?;
    let mut result = Vec::with_capacity(parts);
    let mut previous = 0usize;
    for bar in bars {
        let boundary = bar + 1;
        result.push(boundary - previous);
        previous = boundary;
    }
    result.push(total - previous);
    Ok(result)
}

fn decode_bucketed(
    data: &[u8],
    pos: &mut usize,
    bucket_count: usize,
    total: usize,
) -> Result<HashMap<usize, Vec<u8>>, String> {
    let q = unvar(data, pos)?;
    if q > bucket_count.min(total) {
        return Err("too many active literal buckets".into());
    }
    if q == 0 {
        if total != 0 {
            return Err("non-empty literal stream has no buckets".into());
        }
        return Ok(HashMap::new());
    }
    let ids = if q == bucket_count {
        (0..bucket_count).collect::<Vec<_>>()
    } else {
        let width = fixed_width(&(choose(bucket_count, q) - BigUint::one()));
        colex_unrank(read_fixed(data, pos, width)?, q, bucket_count)?
    };
    let lengths = if q == 1 {
        vec![total]
    } else {
        let width = fixed_width(&(choose(total - 1, q - 1) - BigUint::one()));
        composition_unrank(read_fixed(data, pos, width)?, total, q)?
    };
    let mut streams = HashMap::with_capacity(q);
    for (id, count) in ids.into_iter().zip(lengths) {
        streams.insert(id, rank::decode_type_class(data, pos, count)?);
    }
    Ok(streams)
}

fn context_bucket(tail: &[u8], order: usize, bucket_bits: usize) -> usize {
    let start = tail.len().saturating_sub(order);
    if order == 1 && bucket_bits >= 8 {
        return tail.last().copied().unwrap_or(0) as usize;
    }
    let mut hash = 1469598103934665603u64;
    for &byte in &tail[start..] {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(1099511628211);
    }
    (hash & ((1u64 << bucket_bits) - 1)) as usize
}

enum Literals {
    Plain {
        bytes: Vec<u8>,
        pos: usize,
    },
    Context {
        streams: HashMap<usize, Vec<u8>>,
        cursors: HashMap<usize, usize>,
        order: usize,
        bucket_bits: usize,
    },
}

impl Literals {
    fn next(&mut self, produced: &[u8]) -> Result<u8, String> {
        match self {
            Self::Plain { bytes, pos } => {
                let value = *bytes
                    .get(*pos)
                    .ok_or("chained LZ literal stream exhausted")?;
                *pos += 1;
                Ok(value)
            }
            Self::Context {
                streams,
                cursors,
                order,
                bucket_bits,
            } => {
                let bucket = context_bucket(produced, *order, *bucket_bits);
                let stream = streams
                    .get(&bucket)
                    .ok_or("chained LZ selected absent literal bucket")?;
                let cursor = cursors.entry(bucket).or_default();
                let value = *stream
                    .get(*cursor)
                    .ok_or("chained LZ literal bucket exhausted")?;
                *cursor += 1;
                Ok(value)
            }
        }
    }

    fn fully_consumed(&self) -> bool {
        match self {
            Self::Plain { bytes, pos } => *pos == bytes.len(),
            Self::Context {
                streams, cursors, ..
            } => streams
                .iter()
                .all(|(bucket, stream)| cursors.get(bucket).copied().unwrap_or(0) == stream.len()),
        }
    }
}

fn decode_literals(data: &[u8], count: usize, model_limit: usize) -> Result<Literals, String> {
    let mode = *data.first().ok_or("empty chained LZ literal stream")?;
    match mode {
        0 => {
            let mut pos = 1;
            let bytes = rank::decode_type_class(data, &mut pos, count)?;
            if pos != data.len() {
                return Err("unused chained LZ literal bytes".into());
            }
            Ok(Literals::Plain { bytes, pos: 0 })
        }
        1 => {
            let order = *data.get(1).ok_or("missing literal context order")? as usize;
            let bucket_bits = *data.get(2).ok_or("missing literal context bucket bits")? as usize;
            if !(1..=16).contains(&order) || !(1..=16).contains(&bucket_bits) {
                return Err("invalid literal context parameters".into());
            }
            let mut pos = 3;
            let streams = decode_bucketed(data, &mut pos, 1usize << bucket_bits, count)?;
            if pos != data.len() {
                return Err("unused literal-context bytes".into());
            }
            let cursors = streams.keys().map(|&bucket| (bucket, 0)).collect();
            Ok(Literals::Context {
                streams,
                cursors,
                order,
                bucket_bits,
            })
        }
        2 => Ok(Literals::Plain {
            bytes: decode_bytes(&data[1..], count, model_limit)?,
            pos: 0,
        }),
        3 => Ok(Literals::Plain {
            bytes: ppm::decode(&data[1..], count)?,
            pos: 0,
        }),
        4 => Ok(Literals::Plain {
            bytes: fixedmix::decode(&data[1..], count)?,
            pos: 0,
        }),
        _ => Err(format!("unsupported chained LZ literal mode {mode}")),
    }
}

fn decode_tags(data: &[u8], count: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    let mode = *data.first().ok_or("empty chained LZ tag stream")?;
    match mode {
        0 => {
            let mut pos = 1;
            let tags = rank::decode_type_class(data, &mut pos, count)?;
            if pos != data.len() {
                return Err("unused chained LZ tag bytes".into());
            }
            Ok(tags)
        }
        1 => {
            let mut tag = *data.get(1).ok_or("missing chained LZ initial tag")?;
            if tag > 1 {
                return Err("invalid chained LZ initial tag".into());
            }
            let mut pos = 2;
            let run_count = unvar(data, &mut pos)?;
            let lengths = decode_uints(&data[pos..], run_count, model_limit)?;
            let mut tags = Vec::with_capacity(count);
            for minus_one in lengths {
                let length = minus_one.checked_add(1).ok_or("tag run overflow")?;
                if tags.len().saturating_add(length) > count {
                    return Err("chained LZ tag runs exceed token count".into());
                }
                tags.resize(tags.len() + length, tag);
                tag ^= 1;
            }
            if tags.len() != count {
                return Err("chained LZ tag-run length mismatch".into());
            }
            Ok(tags)
        }
        2 => decode_bytes(&data[1..], count, model_limit),
        _ => Err(format!("unsupported chained LZ tag mode {mode}")),
    }
}

fn decode_distances_v1(data: &[u8], count: usize) -> Result<Vec<usize>, String> {
    if count == 0 {
        return Ok(Vec::new());
    }
    let mut pos = 0;
    let symbol_len = unvar(data, &mut pos)?;
    let end = pos
        .checked_add(symbol_len)
        .ok_or("distance symbol length overflow")?;
    if end > data.len() {
        return Err("truncated chained LZ distance classes".into());
    }
    let mut symbol_pos = 0;
    let symbols = rank::decode_type_class(&data[pos..end], &mut symbol_pos, count)?;
    if symbol_pos != symbol_len {
        return Err("unused chained LZ distance classes".into());
    }
    decode_distance_symbols(&symbols, &data[end..], 4)
}

fn decode_distances_v3(
    data: &[u8],
    count: usize,
    model_limit: usize,
) -> Result<Vec<usize>, String> {
    if count == 0 {
        return Ok(Vec::new());
    }
    let cache_size = *data
        .first()
        .ok_or("empty chained LZ adaptive distance stream")? as usize;
    let mut pos = 1;
    let symbol_len = unvar(data, &mut pos)?;
    let end = pos
        .checked_add(symbol_len)
        .ok_or("adaptive distance length overflow")?;
    if end > data.len() {
        return Err("truncated chained LZ adaptive distance classes".into());
    }
    let symbols = decode_bytes(&data[pos..end], count, model_limit)?;
    decode_distance_symbols(&symbols, &data[end..], cache_size)
}

fn decode_distance_symbols(
    symbols: &[u8],
    low_bits: &[u8],
    cache_size: usize,
) -> Result<Vec<usize>, String> {
    let mut reader = BitReader {
        data: low_bits,
        pos: 0,
    };
    let mut cache = Vec::<usize>::new();
    let mut out = Vec::with_capacity(symbols.len());
    for &symbol in symbols {
        let symbol = symbol as usize;
        let distance = if symbol < cache_size {
            if symbol >= cache.len() {
                return Err("invalid chained LZ distance cache reference".into());
            }
            let distance = cache.remove(symbol);
            cache.insert(0, distance);
            distance
        } else {
            let width = symbol - cache_size;
            if width >= usize::BITS as usize {
                return Err("chained LZ distance class too wide".into());
            }
            let low = reader.bits(width)?;
            let distance = (1usize << width)
                .checked_add(low)
                .ok_or("chained LZ distance overflow")?;
            if cache_size > 0 {
                cache.insert(0, distance);
                cache.truncate(cache_size);
            }
            distance
        };
        out.push(distance);
    }
    Ok(out)
}

fn decode_lz(data: &[u8], source_len: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    if data.len() < 2 || !matches!(data[0], 1 | 3) {
        return Err("unknown chained LZ version".into());
    }
    let version = data[0];
    let min_match = data[1] as usize;
    let mut pos = 2;
    let token_count = unvar(data, &mut pos)?;
    let literal_count = unvar(data, &mut pos)?;
    let match_count = unvar(data, &mut pos)?;
    let mut streams = Vec::with_capacity(4);
    for _ in 0..4 {
        let length = unvar(data, &mut pos)?;
        let end = pos
            .checked_add(length)
            .ok_or("LZ substream length overflow")?;
        if end > data.len() {
            return Err("truncated chained LZ substream".into());
        }
        streams.push(&data[pos..end]);
        pos = end;
    }
    if pos != data.len() {
        return Err("trailing chained LZ bytes".into());
    }
    let tags = if version == 1 {
        let mut tag_pos = 0;
        let tags = rank::decode_type_class(streams[0], &mut tag_pos, token_count)?;
        if tag_pos != streams[0].len() {
            return Err("unused chained LZ v1 tag bytes".into());
        }
        tags
    } else {
        decode_tags(streams[0], token_count, model_limit)?
    };
    let mut literals = decode_literals(streams[1], literal_count, model_limit)?;
    let lengths = decode_uints(streams[2], match_count, model_limit)?;
    let distances = if version == 1 {
        decode_distances_v1(streams[3], match_count)?
    } else {
        decode_distances_v3(streams[3], match_count, model_limit)?
    };
    let mut output = Vec::with_capacity(source_len);
    let mut literals_used = 0usize;
    let mut matches_used = 0usize;
    for tag in tags {
        match tag {
            0 => {
                output.push(literals.next(&output)?);
                literals_used += 1;
            }
            1 => {
                let encoded_length = *lengths
                    .get(matches_used)
                    .ok_or("chained LZ match stream exhausted")?;
                let distance = *distances
                    .get(matches_used)
                    .ok_or("chained LZ distance stream exhausted")?;
                matches_used += 1;
                if distance == 0 || distance > output.len() {
                    return Err("chained LZ distance before available history".into());
                }
                let length = encoded_length
                    .checked_add(min_match)
                    .ok_or("chained LZ match length overflow")?;
                for _ in 0..length {
                    let source = output.len() - distance;
                    let value = output[source];
                    output.push(value);
                    if output.len() > source_len {
                        return Err("chained LZ expands beyond source length".into());
                    }
                }
            }
            _ => return Err("invalid chained LZ tag".into()),
        }
    }
    if output.len() != source_len
        || literals_used != literal_count
        || matches_used != match_count
        || !literals.fully_consumed()
    {
        return Err("chained LZ decoded counts or length mismatch".into());
    }
    Ok(output)
}

fn unshuffle(data: &[u8], width: usize) -> Vec<u8> {
    let usable = data.len() / width * width;
    let words = usable / width;
    let mut out = vec![0u8; usable];
    for lane in 0..width {
        for word in 0..words {
            out[word * width + lane] = data[lane * words + word];
        }
    }
    out.extend_from_slice(&data[usable..]);
    out
}

fn read_word(data: &[u8], endian: Endian) -> u64 {
    match endian {
        Endian::Little => data.iter().enumerate().fold(0u64, |value, (shift, &byte)| {
            value | ((byte as u64) << (8 * shift))
        }),
        Endian::Big => data
            .iter()
            .fold(0u64, |value, &byte| (value << 8) | byte as u64),
    }
}

fn write_word(value: u64, width: usize, endian: Endian, out: &mut Vec<u8>) {
    match endian {
        Endian::Little => {
            for shift in 0..width {
                out.push((value >> (8 * shift)) as u8);
            }
        }
        Endian::Big => {
            for shift in (0..width).rev() {
                out.push((value >> (8 * shift)) as u8);
            }
        }
    }
}

fn matchxor_decode(data: &[u8]) -> Vec<u8> {
    let mut table = HashMap::<[u8; 4], usize>::new();
    let mut active = None::<usize>;
    let mut out = Vec::with_capacity(data.len());
    for (pos, &residual) in data.iter().enumerate() {
        let source = if active.is_some_and(|source| source < pos) {
            active
        } else if pos >= 4 {
            let key: [u8; 4] = out[pos - 4..pos].try_into().unwrap();
            table.get(&key).copied()
        } else {
            None
        };
        let prediction = source.map_or(0, |source| out[source]);
        let byte = residual ^ prediction;
        out.push(byte);
        if pos >= 4 {
            let key: [u8; 4] = out[pos - 4..pos].try_into().unwrap();
            table.insert(key, pos);
        }
        active = source
            .filter(|_| prediction == byte)
            .and_then(|source| source.checked_add(1));
    }
    out
}

fn invert(data: &[u8], spec: Transform) -> Result<Vec<u8>, String> {
    if matches!(spec.operation, Operation::MatchXor) {
        return Ok(matchxor_decode(data));
    }
    let mut raw = if spec.shuffle {
        unshuffle(data, spec.width)
    } else {
        data.to_vec()
    };
    if let Some(lag) = spec.byte_lag {
        match spec.operation {
            Operation::Xor => {
                for i in lag..raw.len() {
                    raw[i] ^= raw[i - lag];
                }
            }
            Operation::Delta => {
                for i in lag..raw.len() {
                    raw[i] = raw[i].wrapping_add(raw[i - lag]);
                }
            }
            _ => return Err("invalid byte-lag transform operation".into()),
        }
        return Ok(raw);
    }
    let usable = raw.len() / spec.width * spec.width;
    let mut values = raw[..usable]
        .chunks_exact(spec.width)
        .map(|word| read_word(word, spec.endian));
    let Some(first) = values.next() else {
        return Ok(raw);
    };
    let bits = 8 * spec.width;
    let mask = if bits == 64 {
        u64::MAX
    } else {
        (1u64 << bits) - 1
    };
    let add = |left: u64, right: u64| left.wrapping_add(right) & mask;
    let mut restored = Vec::with_capacity(usable / spec.width);
    restored.push(first);
    match spec.operation {
        Operation::Xor => {
            for encoded in values {
                restored.push(restored.last().copied().unwrap() ^ encoded);
            }
        }
        Operation::Delta => {
            for delta in values {
                restored.push(add(restored.last().copied().unwrap(), delta));
            }
        }
        Operation::Delta2 => {
            if let Some(mut previous_delta) = values.next() {
                restored.push(add(restored[0], previous_delta));
                for delta_delta in values {
                    previous_delta = add(previous_delta, delta_delta);
                    restored.push(add(restored.last().copied().unwrap(), previous_delta));
                }
            }
        }
        Operation::Delta2Zigzag => {
            let unzigzag = |encoded: u64| {
                if encoded & 1 == 0 {
                    encoded >> 1
                } else {
                    0u64.wrapping_sub((encoded >> 1) + 1) & mask
                }
            };
            if let Some(encoded_delta) = values.next() {
                let mut previous_delta = unzigzag(encoded_delta);
                restored.push(add(restored[0], previous_delta));
                for encoded_delta_delta in values {
                    previous_delta = add(previous_delta, unzigzag(encoded_delta_delta));
                    restored.push(add(restored.last().copied().unwrap(), previous_delta));
                }
            }
        }
        Operation::MatchXor => unreachable!(),
    }
    let mut out = Vec::with_capacity(raw.len());
    for word in restored {
        write_word(word, spec.width, spec.endian, &mut out);
    }
    out.extend_from_slice(&raw[usable..]);
    Ok(out)
}

/// Decode one CIXM6 mode-7 payload.
///
/// `model_limit` bounds adaptive context tables used by nested byte streams.
/// Transform-chain blocks do not inherit preceding CIXM6 history: the frozen
/// Python encoder invokes every inner codec with an empty prefix.
pub fn decode(data: &[u8], source_len: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    if data.len() < 3 || data[0] != CHAIN_VERSION {
        return Err("unknown transform-chain version".into());
    }
    let spec = transform(data[1]).ok_or("unknown transform-chain transform")?;
    let payload = &data[3..];
    let transformed = match data[2] {
        INNER_MULTINOMIAL => {
            let mut pos = 0;
            let out = rank::decode_type_class(payload, &mut pos, source_len)?;
            if pos != payload.len() {
                return Err("unused chained multinomial bytes".into());
            }
            out
        }
        INNER_CONTEXT => rank::decode_context_type_classes(payload, source_len, &[])?,
        INNER_LZ => decode_lz(payload, source_len, model_limit)?,
        INNER_BWT => bwt_legacy::decode(payload, source_len, model_limit)?,
        INNER_BITPLANE => bitplane::decode(payload, source_len)?,
        INNER_SPARSE => rank::decode_sparse_blob(payload, source_len)?,
        INNER_RUNS => decode_runs(payload, source_len, model_limit)?,
        mode => return Err(format!("unsupported transform-chain inner mode {mode}")),
    };
    if transformed.len() != source_len {
        return Err("transform-chain inner source length mismatch".into());
    }
    let restored = invert(&transformed, spec)?;
    if restored.len() != source_len {
        return Err("transform-chain source length mismatch".into());
    }
    Ok(restored)
}
