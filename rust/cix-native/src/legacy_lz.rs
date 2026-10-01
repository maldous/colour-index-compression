//! Decoder for the frozen Python CIXM6 mode-3 LZ payload.
//!
//! The payload stores four independently coded substreams: tags, literals,
//! match lengths, and match distances. Exact-rank substreams retain arbitrary-
//! precision combinatorial ranks through `rank`.

use std::collections::HashMap;

fn read_varint(data: &[u8], pos: &mut usize) -> Result<usize, String> {
    let mut value = 0usize;
    for shift in (0..usize::BITS as usize).step_by(7) {
        let byte = *data.get(*pos).ok_or("truncated LZ varint")?;
        *pos += 1;
        let part = ((byte & 0x7f) as usize)
            .checked_shl(shift as u32)
            .ok_or("LZ varint overflow")?;
        value = value.checked_add(part).ok_or("LZ varint overflow")?;
        if byte < 128 {
            return Ok(value);
        }
    }
    Err("oversized LZ varint".into())
}

struct BitReader<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> BitReader<'a> {
    fn read(&mut self, width: usize) -> Result<usize, String> {
        if width >= usize::BITS as usize || self.pos.saturating_add(width) > self.data.len() * 8 {
            return Err("truncated LZ bitstream".into());
        }
        let mut value = 0usize;
        for _ in 0..width {
            value = (value << 1) | (((self.data[self.pos / 8] >> (7 - self.pos % 8)) & 1) as usize);
            self.pos += 1;
        }
        Ok(value)
    }
}

fn decode_bytes(blob: &[u8], count: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    let mode = *blob.first().ok_or("empty LZ byte substream")?;
    let mut pos = 1usize;
    match mode {
        0 => {
            let out = crate::rank::decode_type_class(blob, &mut pos, count)?;
            if pos != blob.len() {
                return Err("trailing static LZ byte-substream bytes".into());
            }
            Ok(out)
        }
        1 => {
            let chunk_size = read_varint(blob, &mut pos)?;
            if chunk_size == 0 {
                return Err("invalid LZ byte-substream chunk size".into());
            }
            let mut out = Vec::with_capacity(count);
            while out.len() < count {
                let n = chunk_size.min(count - out.len());
                out.extend(crate::rank::decode_type_class(blob, &mut pos, n)?);
            }
            if pos != blob.len() {
                return Err("trailing chunked LZ byte-substream bytes".into());
            }
            Ok(out)
        }
        2 => crate::adaptive::decode_general(&blob[1..], count, &[], model_limit),
        3 => {
            if !matches!(blob.get(1), Some(1 | 2)) {
                return Err("invalid context LZ byte-substream order".into());
            }
            crate::adaptive::decode_general(&blob[2..], count, &[], model_limit)
        }
        4 => decode_wavelet(&blob[1..], count),
        5 => decode_histogram_type_class(&blob[1..], count, model_limit),
        other => Err(format!("unsupported LZ byte-substream mode {other}")),
    }
}

fn decode_wavelet_node(
    n: usize,
    depth: usize,
    decoder: &mut crate::rank::ArithmeticDecoder<'_>,
    prefix: u8,
) -> Result<Vec<u8>, String> {
    if n == 0 {
        return Ok(Vec::new());
    }
    if depth == 8 {
        return Ok(vec![prefix; n]);
    }
    let total = n + 1;
    let ones = decoder.target(total);
    if ones > n {
        return Err("LZ wavelet child count out of range".into());
    }
    decoder.update(ones, ones + 1, total);
    let (original_ones, original_zeros) = (ones, n - ones);
    let (mut zero, mut one, mut remaining) = (original_zeros, original_ones, n);
    let mut bits = Vec::with_capacity(n);
    for _ in 0..n {
        let bit = if zero == 0 {
            decoder.update(0, one, remaining);
            one -= 1;
            1
        } else if one == 0 {
            decoder.update(0, zero, remaining);
            zero -= 1;
            0
        } else if decoder.target(remaining) < zero {
            decoder.update(0, zero, remaining);
            zero -= 1;
            0
        } else {
            decoder.update(zero, remaining, remaining);
            one -= 1;
            1
        };
        remaining -= 1;
        bits.push(bit);
    }
    let zeros = decode_wavelet_node(original_zeros, depth + 1, decoder, prefix << 1)?;
    let ones = decode_wavelet_node(original_ones, depth + 1, decoder, (prefix << 1) | 1)?;
    let (mut zero_pos, mut one_pos) = (0usize, 0usize);
    let mut out = Vec::with_capacity(n);
    for bit in bits {
        if bit == 0 {
            out.push(zeros[zero_pos]);
            zero_pos += 1;
        } else {
            out.push(ones[one_pos]);
            one_pos += 1;
        }
    }
    Ok(out)
}

fn decode_wavelet(blob: &[u8], count: usize) -> Result<Vec<u8>, String> {
    if blob.first() != Some(&1) {
        return Err("unknown LZ wavelet version".into());
    }
    let mut pos = 1usize;
    let bit_length = read_varint(blob, &mut pos)?;
    if pos.checked_add(bit_length.div_ceil(8)) != Some(blob.len()) {
        return Err("LZ wavelet payload length mismatch".into());
    }
    let mut decoder = crate::rank::ArithmeticDecoder::new(&blob[pos..], bit_length);
    decode_wavelet_node(count, 0, &mut decoder, 0)
}

fn unzig(value: usize) -> i128 {
    let value = value as i128;
    if value & 1 == 0 {
        value / 2
    } else {
        -(value / 2) - 1
    }
}

fn decode_histogram_counts(
    blob: &[u8],
    total: usize,
    model_limit: usize,
) -> Result<Vec<usize>, String> {
    if blob.len() < 2 || blob[0] != 1 {
        return Err("unknown LZ count-vector version".into());
    }
    let mode = blob[1];
    let mut pos = 2usize;
    let mut counts = vec![0usize; 256];
    if matches!(mode, 0 | 1 | 4) {
        let active_count = read_varint(blob, &mut pos)?;
        if active_count == 0 || active_count > 256 || active_count > total {
            return Err("invalid LZ active count alphabet".into());
        }
        let active = if active_count == 256 {
            (0..256).collect()
        } else {
            crate::rank::decode_colex_positions(blob, &mut pos, 256, active_count)?
        };
        let values = decode_uints(&blob[pos..], active_count - 1, model_limit)?;
        let mut first = Vec::with_capacity(active_count);
        match mode {
            0 => first.extend(values.into_iter().map(|value| value.saturating_add(1))),
            1 => {
                let mut previous = 0i128;
                for value in values {
                    previous += unzig(value);
                    if previous <= 0 {
                        return Err("invalid LZ active count delta".into());
                    }
                    first.push(previous as usize);
                }
            }
            4 => {
                let center = total / active_count;
                for value in values {
                    let count = center as i128 + unzig(value);
                    if count <= 0 {
                        return Err("invalid LZ centered active count".into());
                    }
                    first.push(count as usize);
                }
            }
            _ => unreachable!(),
        }
        let last = total
            .checked_sub(first.iter().sum())
            .ok_or("LZ active histogram exceeds total")?;
        if last == 0 {
            return Err("zero implied LZ active count".into());
        }
        first.push(last);
        for (symbol, count) in active.into_iter().zip(first) {
            counts[symbol] = count;
        }
        return Ok(counts);
    }
    if matches!(mode, 2 | 3 | 5) {
        let values = decode_uints(&blob[pos..], 255, model_limit)?;
        let mut first = Vec::with_capacity(256);
        match mode {
            2 => first = values,
            3 => {
                let mut previous = 0i128;
                for value in values {
                    previous += unzig(value);
                    if previous < 0 {
                        return Err("negative LZ dense histogram count".into());
                    }
                    first.push(previous as usize);
                }
            }
            5 => {
                let center = total / 256;
                for value in values {
                    let count = center as i128 + unzig(value);
                    if count < 0 {
                        return Err("negative LZ centered histogram count".into());
                    }
                    first.push(count as usize);
                }
            }
            _ => unreachable!(),
        }
        let last = total
            .checked_sub(first.iter().sum())
            .ok_or("LZ dense histogram exceeds total")?;
        first.push(last);
        return Ok(first);
    }
    Err(format!("unknown LZ count-vector mode {mode}"))
}

fn decode_histogram_type_class(
    blob: &[u8],
    total: usize,
    model_limit: usize,
) -> Result<Vec<u8>, String> {
    let mut pos = 0usize;
    let length = read_varint(blob, &mut pos)?;
    let end = pos
        .checked_add(length)
        .ok_or("LZ histogram length overflow")?;
    if end > blob.len() {
        return Err("truncated LZ histogram".into());
    }
    let counts = decode_histogram_counts(&blob[pos..end], total, model_limit)?;
    crate::rank::decode_type_class_with_counts(&blob[end..], total, &counts)
}

fn decode_uints(blob: &[u8], count: usize, model_limit: usize) -> Result<Vec<usize>, String> {
    if count == 0 {
        return Ok(Vec::new());
    }
    let mode = *blob.first().ok_or("empty LZ integer substream")?;
    let mut pos = 1usize;
    match mode {
        0 => {
            let mut out = Vec::with_capacity(count);
            for _ in 0..count {
                out.push(read_varint(blob, &mut pos)?);
            }
            if pos != blob.len() {
                return Err("trailing LZ integer varints".into());
            }
            Ok(out)
        }
        1 => {
            let k = *blob.get(pos).ok_or("missing LZ Rice parameter")? as usize;
            pos += 1;
            if k >= usize::BITS as usize {
                return Err("LZ Rice parameter is too wide".into());
            }
            let mut bits = BitReader {
                data: &blob[pos..],
                pos: 0,
            };
            let mut out = Vec::with_capacity(count);
            for _ in 0..count {
                let mut quotient = 0usize;
                while bits.read(1)? != 0 {
                    quotient = quotient.checked_add(1).ok_or("LZ Rice quotient overflow")?;
                }
                let low = bits.read(k)?;
                out.push(
                    quotient
                        .checked_shl(k as u32)
                        .ok_or("LZ Rice value overflow")?
                        | low,
                );
            }
            Ok(out)
        }
        2 | 3 => {
            let class_len = read_varint(blob, &mut pos)?;
            let end = pos
                .checked_add(class_len)
                .ok_or("LZ integer class length overflow")?;
            if end > blob.len() {
                return Err("truncated LZ integer class stream".into());
            }
            let classes = if mode == 2 {
                let mut class_pos = pos;
                let out = crate::rank::decode_type_class(blob, &mut class_pos, count)?;
                if class_pos != end {
                    return Err("trailing LZ integer class bytes".into());
                }
                out
            } else {
                decode_bytes(&blob[pos..end], count, model_limit)?
            };
            let mut bits = BitReader {
                data: &blob[end..],
                pos: 0,
            };
            let mut out = Vec::with_capacity(count);
            for class in classes {
                let width = class as usize;
                if width >= usize::BITS as usize {
                    return Err("LZ integer class is too wide".into());
                }
                let low = bits.read(width)?;
                out.push(
                    (1usize << width)
                        .checked_add(low)
                        .and_then(|value| value.checked_sub(1))
                        .ok_or("LZ integer value overflow")?,
                );
            }
            Ok(out)
        }
        other => Err(format!("unsupported LZ integer substream mode {other}")),
    }
}

fn decode_tags(blob: &[u8], count: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    let mode = *blob.first().ok_or("empty LZ tag stream")?;
    match mode {
        0 => {
            let mut pos = 1usize;
            let out = crate::rank::decode_type_class(blob, &mut pos, count)?;
            if pos != blob.len() {
                return Err("trailing LZ tag bytes".into());
            }
            Ok(out)
        }
        1 => {
            let first = *blob.get(1).ok_or("truncated LZ run tag stream")?;
            if first > 1 {
                return Err("invalid LZ run tag".into());
            }
            let mut pos = 2usize;
            let run_count = read_varint(blob, &mut pos)?;
            let runs = decode_uints(&blob[pos..], run_count, model_limit)?;
            let mut out = Vec::with_capacity(count);
            let mut tag = first;
            for encoded_length in runs {
                let run_length = encoded_length
                    .checked_add(1)
                    .ok_or("LZ tag run length overflow")?;
                if out.len().saturating_add(run_length) > count {
                    return Err("LZ run tags exceed token count".into());
                }
                out.resize(out.len() + run_length, tag);
                tag ^= 1;
            }
            if out.len() != count {
                return Err("LZ run tags length mismatch".into());
            }
            Ok(out)
        }
        2 => decode_bytes(&blob[1..], count, model_limit),
        other => Err(format!("unsupported LZ tag mode {other}")),
    }
}

fn decode_bucketed(
    blob: &[u8],
    pos: &mut usize,
    bucket_count: usize,
    total_items: usize,
) -> Result<HashMap<usize, Vec<u8>>, String> {
    let q = read_varint(blob, pos)?;
    if q > bucket_count.min(total_items) {
        return Err("invalid active LZ literal bucket count".into());
    }
    if q == 0 {
        return if total_items == 0 {
            Ok(HashMap::new())
        } else {
            Err("non-empty LZ literal stream has no active buckets".into())
        };
    }
    let ids = if q == bucket_count {
        (0..bucket_count).collect::<Vec<_>>()
    } else {
        crate::rank::decode_colex_positions(blob, pos, bucket_count, q)?
    };
    let lengths = if q == 1 {
        vec![total_items]
    } else {
        let cuts = crate::rank::decode_colex_positions(blob, pos, total_items - 1, q - 1)?;
        let mut lengths = Vec::with_capacity(q);
        let mut previous = 0usize;
        for cut in cuts {
            let boundary = cut + 1;
            lengths.push(boundary - previous);
            previous = boundary;
        }
        lengths.push(total_items - previous);
        lengths
    };
    let mut streams = HashMap::with_capacity(q);
    for (id, length) in ids.into_iter().zip(lengths) {
        streams.insert(id, crate::rank::decode_type_class(blob, pos, length)?);
    }
    Ok(streams)
}

struct LiteralDecoder {
    plain: Option<Vec<u8>>,
    plain_pos: usize,
    lanes: HashMap<usize, Vec<u8>>,
    lane_pos: HashMap<usize, usize>,
    order: usize,
    bucket_bits: usize,
}

impl LiteralDecoder {
    fn plain(values: Vec<u8>) -> Self {
        Self {
            plain: Some(values),
            plain_pos: 0,
            lanes: HashMap::new(),
            lane_pos: HashMap::new(),
            order: 0,
            bucket_bits: 0,
        }
    }

    fn next(&mut self, prefix: &[u8], produced: &[u8]) -> Result<u8, String> {
        if let Some(values) = &self.plain {
            let value = *values
                .get(self.plain_pos)
                .ok_or("LZ literal stream exhausted")?;
            self.plain_pos += 1;
            return Ok(value);
        }
        if produced.len() >= self.order {
            self.next_for_tail(&produced[produced.len() - self.order..])
        } else {
            let missing = self.order - produced.len();
            let start = prefix.len().saturating_sub(missing);
            let mut joined = Vec::with_capacity(prefix.len() - start + produced.len());
            joined.extend_from_slice(&prefix[start..]);
            joined.extend_from_slice(produced);
            self.next_for_tail(&joined)
        }
    }

    fn next_for_tail(&mut self, tail: &[u8]) -> Result<u8, String> {
        let bucket = if self.order == 1 && self.bucket_bits >= 8 {
            tail.last().copied().unwrap_or(0) as usize
        } else {
            let mut hash = 1469598103934665603u64;
            for &byte in tail {
                hash ^= byte as u64;
                hash = hash.wrapping_mul(1099511628211);
            }
            (hash & ((1u64 << self.bucket_bits) - 1)) as usize
        };
        let values = self
            .lanes
            .get(&bucket)
            .ok_or("LZ literal context selected absent bucket")?;
        let cursor = self
            .lane_pos
            .get_mut(&bucket)
            .ok_or("missing LZ literal bucket cursor")?;
        let value = *values
            .get(*cursor)
            .ok_or("LZ literal context bucket exhausted")?;
        *cursor += 1;
        Ok(value)
    }

    fn finish(&self, expected: usize) -> Result<(), String> {
        if let Some(values) = &self.plain {
            if self.plain_pos != expected || values.len() != expected {
                return Err("unused LZ literal symbols".into());
            }
        } else if self
            .lanes
            .iter()
            .any(|(bucket, values)| self.lane_pos.get(bucket).copied() != Some(values.len()))
        {
            return Err("unused LZ literal-context symbols".into());
        }
        Ok(())
    }
}

fn decode_literals(
    blob: &[u8],
    count: usize,
    model_limit: usize,
) -> Result<LiteralDecoder, String> {
    let mode = *blob.first().ok_or("empty LZ literal stream")?;
    match mode {
        0 => {
            let mut pos = 1usize;
            let values = crate::rank::decode_type_class(blob, &mut pos, count)?;
            if pos != blob.len() {
                return Err("trailing LZ literal bytes".into());
            }
            Ok(LiteralDecoder::plain(values))
        }
        1 => {
            if blob.len() < 3 {
                return Err("truncated LZ literal context parameters".into());
            }
            let order = blob[1] as usize;
            let bucket_bits = blob[2] as usize;
            if order > 16 || !(1..=16).contains(&bucket_bits) {
                return Err("invalid LZ literal context parameters".into());
            }
            let mut pos = 3usize;
            let lanes = decode_bucketed(blob, &mut pos, 1usize << bucket_bits, count)?;
            if pos != blob.len() {
                return Err("trailing LZ literal-context bytes".into());
            }
            let lane_pos = lanes.keys().map(|&bucket| (bucket, 0usize)).collect();
            Ok(LiteralDecoder {
                plain: None,
                plain_pos: 0,
                lanes,
                lane_pos,
                order,
                bucket_bits,
            })
        }
        2 => Ok(LiteralDecoder::plain(decode_bytes(
            &blob[1..],
            count,
            model_limit,
        )?)),
        3 => Ok(LiteralDecoder::plain(crate::ppm::decode(
            &blob[1..],
            count,
        )?)),
        4 => Ok(LiteralDecoder::plain(crate::fixedmix::decode(
            &blob[1..],
            count,
        )?)),
        other => Err(format!("unsupported LZ literal mode {other}")),
    }
}

fn decode_distances_legacy(blob: &[u8], count: usize) -> Result<Vec<usize>, String> {
    if count == 0 {
        return Ok(Vec::new());
    }
    let mut pos = 0usize;
    let symbol_len = read_varint(blob, &mut pos)?;
    let end = pos
        .checked_add(symbol_len)
        .ok_or("LZ distance class length overflow")?;
    if end > blob.len() {
        return Err("truncated LZ distance classes".into());
    }
    let mut symbol_pos = pos;
    let symbols = crate::rank::decode_type_class(blob, &mut symbol_pos, count)?;
    if symbol_pos != end {
        return Err("trailing LZ distance class bytes".into());
    }
    decode_distance_symbols(&symbols, &blob[end..], 4)
}

fn decode_distances_best(
    blob: &[u8],
    count: usize,
    model_limit: usize,
) -> Result<Vec<usize>, String> {
    if count == 0 {
        return Ok(Vec::new());
    }
    let cache_size = *blob.first().ok_or("empty adaptive LZ distance stream")? as usize;
    let mut pos = 1usize;
    let symbol_len = read_varint(blob, &mut pos)?;
    let end = pos
        .checked_add(symbol_len)
        .ok_or("LZ distance symbol length overflow")?;
    if end > blob.len() {
        return Err("truncated adaptive LZ distance classes".into());
    }
    let symbols = decode_bytes(&blob[pos..end], count, model_limit)?;
    decode_distance_symbols(&symbols, &blob[end..], cache_size)
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
                return Err("invalid LZ distance cache reference".into());
            }
            let distance = cache.remove(symbol);
            cache.insert(0, distance);
            distance
        } else {
            let width = symbol - cache_size;
            if width >= usize::BITS as usize {
                return Err("LZ distance class is too wide".into());
            }
            let low = reader.read(width)?;
            let distance = (1usize << width)
                .checked_add(low)
                .ok_or("LZ distance overflow")?;
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

/// Decode a frozen Python CIXM6 mode-3 payload.
///
/// `prefix_history` is already reconstructed stream history visible to the
/// block. `model_limit` bounds adaptive substream context tables.
pub fn decode(
    blob: &[u8],
    source_length: usize,
    prefix_history: &[u8],
    model_limit: usize,
) -> Result<Vec<u8>, String> {
    if blob.len() < 2 || !matches!(blob[0], 1 | 3) {
        return Err("unknown LZ block version".into());
    }
    let version = blob[0];
    let min_match = blob[1] as usize;
    let mut pos = 2usize;
    let token_count = read_varint(blob, &mut pos)?;
    let literal_count = read_varint(blob, &mut pos)?;
    let match_count = read_varint(blob, &mut pos)?;
    if token_count > source_length
        || literal_count > token_count
        || match_count > token_count
        || literal_count.saturating_add(match_count) != token_count
    {
        return Err("invalid LZ token counts".into());
    }
    let mut streams = Vec::with_capacity(4);
    for _ in 0..4 {
        let length = read_varint(blob, &mut pos)?;
        let end = pos
            .checked_add(length)
            .ok_or("LZ substream length overflow")?;
        if end > blob.len() {
            return Err("truncated LZ substream".into());
        }
        streams.push(&blob[pos..end]);
        pos = end;
    }
    if pos != blob.len() {
        return Err("trailing LZ block bytes".into());
    }

    let tags = if version == 1 {
        let mut tag_pos = 0usize;
        let out = crate::rank::decode_type_class(streams[0], &mut tag_pos, token_count)?;
        if tag_pos != streams[0].len() {
            return Err("trailing version-1 LZ tag bytes".into());
        }
        out
    } else {
        decode_tags(streams[0], token_count, model_limit)?
    };
    let mut literals = decode_literals(streams[1], literal_count, model_limit)?;
    let lengths = decode_uints(streams[2], match_count, model_limit)?;
    let distances = if version >= 3 {
        decode_distances_best(streams[3], match_count, model_limit)?
    } else {
        decode_distances_legacy(streams[3], match_count)?
    };

    let mut produced = Vec::with_capacity(source_length);
    let mut literal_used = 0usize;
    let mut match_used = 0usize;
    for tag in tags {
        match tag {
            0 => {
                produced.push(literals.next(prefix_history, &produced)?);
                literal_used += 1;
            }
            1 => {
                let encoded_length = *lengths
                    .get(match_used)
                    .ok_or("LZ match-length stream exhausted")?;
                let distance = *distances
                    .get(match_used)
                    .ok_or("LZ distance stream exhausted")?;
                match_used += 1;
                let length = encoded_length
                    .checked_add(min_match)
                    .ok_or("LZ match length overflow")?;
                if distance == 0
                    || distance > prefix_history.len().saturating_add(produced.len())
                    || produced
                        .len()
                        .checked_add(length)
                        .is_none_or(|end| end > source_length)
                {
                    return Err("invalid LZ match descriptor".into());
                }
                for _ in 0..length {
                    let source = prefix_history.len() + produced.len() - distance;
                    let value = if source < prefix_history.len() {
                        prefix_history[source]
                    } else {
                        produced[source - prefix_history.len()]
                    };
                    produced.push(value);
                }
            }
            _ => return Err("invalid LZ tag".into()),
        }
    }
    if produced.len() != source_length || literal_used != literal_count || match_used != match_count
    {
        return Err("LZ decoded length or token count mismatch".into());
    }
    literals.finish(literal_count)?;
    Ok(produced)
}

#[cfg(test)]
mod tests {
    use super::decode;

    #[test]
    fn rejects_unknown_version() {
        assert!(decode(&[2, 4], 1, &[], 1024).is_err());
    }

    #[test]
    fn rejects_inconsistent_counts_before_stream_allocation() {
        assert!(decode(&[3, 4, 2, 2, 1], 2, &[], 1024).is_err());
    }
}
