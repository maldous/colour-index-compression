//! Decoder for legacy CIXM6 mode 4 (BWT/MTF payload versions 1 through 6).
//!
//! This is deliberately separate from the CIXG1 BWT route. CIXM6 uses local
//! byte/integer substreams and libdivsufsort's one-based primary-index
//! convention; the CIXG1 route has different framing.

use super::rank::{self, ArithmeticDecoder};

fn read_varint(data: &[u8], pos: &mut usize) -> Result<usize, String> {
    let mut value = 0usize;
    for shift in (0..usize::BITS as usize).step_by(7) {
        let byte = *data.get(*pos).ok_or("truncated BWT varint")?;
        *pos += 1;
        let low = (byte & 0x7f) as usize;
        if shift + 7 > usize::BITS as usize && low > (usize::MAX >> shift) {
            return Err("BWT varint overflow".into());
        }
        value |= low.checked_shl(shift as u32).ok_or("BWT varint overflow")?;
        if byte < 128 {
            return Ok(value);
        }
    }
    Err("oversized BWT varint".into())
}

struct BitReader<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> BitReader<'a> {
    fn new(data: &'a [u8]) -> Self {
        Self { data, pos: 0 }
    }

    fn bit(&mut self) -> Result<usize, String> {
        if self.pos >= self.data.len().saturating_mul(8) {
            return Err("truncated BWT bitstream".into());
        }
        let value = ((self.data[self.pos / 8] >> (7 - self.pos % 8)) & 1) as usize;
        self.pos += 1;
        Ok(value)
    }

    fn bits(&mut self, width: usize) -> Result<usize, String> {
        if width >= usize::BITS as usize {
            return Err("BWT integer class too wide".into());
        }
        let mut value = 0usize;
        for _ in 0..width {
            value = (value << 1) | self.bit()?;
        }
        Ok(value)
    }
}

fn decode_wavelet_node(
    n: usize,
    depth: usize,
    decoder: &mut ArithmeticDecoder<'_>,
    prefix: u8,
) -> Result<Vec<u8>, String> {
    if n == 0 {
        return Ok(Vec::new());
    }
    if depth == 8 {
        return Ok(vec![prefix; n]);
    }
    let total = n.checked_add(1).ok_or("BWT wavelet size overflow")?;
    let ones = decoder.target(total);
    if ones > n {
        return Err("BWT wavelet child count out of range".into());
    }
    decoder.update(ones, ones + 1, total);
    let (original_ones, original_zeros) = (ones, n - ones);
    let (mut one, mut zero, mut remaining) = (original_ones, original_zeros, n);
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
        } else {
            let target = decoder.target(remaining);
            if target < zero {
                decoder.update(0, zero, remaining);
                zero -= 1;
                0
            } else {
                decoder.update(zero, remaining, remaining);
                one -= 1;
                1
            }
        };
        remaining -= 1;
        bits.push(bit);
    }
    let zero_values = decode_wavelet_node(original_zeros, depth + 1, decoder, prefix << 1)?;
    let one_values = decode_wavelet_node(original_ones, depth + 1, decoder, (prefix << 1) | 1)?;
    let (mut zero_pos, mut one_pos) = (0usize, 0usize);
    let mut out = Vec::with_capacity(n);
    for bit in bits {
        if bit == 0 {
            out.push(zero_values[zero_pos]);
            zero_pos += 1;
        } else {
            out.push(one_values[one_pos]);
            one_pos += 1;
        }
    }
    Ok(out)
}

fn decode_wavelet(blob: &[u8], count: usize) -> Result<Vec<u8>, String> {
    if blob.first() != Some(&1) {
        return Err("unknown BWT wavelet version".into());
    }
    let mut pos = 1;
    let bit_length = read_varint(blob, &mut pos)?;
    let byte_length = bit_length.div_ceil(8);
    if pos.checked_add(byte_length) != Some(blob.len()) {
        return Err("BWT wavelet payload length mismatch".into());
    }
    let mut decoder = ArithmeticDecoder::new(&blob[pos..], bit_length);
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
        return Err("unknown BWT count-vector version".into());
    }
    let mode = blob[1];
    let mut pos = 2;
    let mut counts = vec![0usize; 256];
    if matches!(mode, 0 | 1 | 4) {
        let active_count = read_varint(blob, &mut pos)?;
        if active_count == 0 || active_count > 256 || active_count > total {
            return Err("invalid BWT active count alphabet".into());
        }
        let active = if active_count == 256 {
            (0..256).collect()
        } else {
            rank::decode_colex_positions(blob, &mut pos, 256, active_count)?
        };
        let encoded = decode_uints(&blob[pos..], active_count - 1, model_limit)?;
        let mut first = Vec::with_capacity(active_count);
        match mode {
            0 => {
                for value in encoded {
                    first.push(value.checked_add(1).ok_or("BWT count overflow")?);
                }
            }
            1 => {
                let mut previous = 0i128;
                for value in encoded {
                    previous += unzig(value);
                    if previous <= 0 || previous > usize::MAX as i128 {
                        return Err("invalid BWT active count delta".into());
                    }
                    first.push(previous as usize);
                }
            }
            4 => {
                let center = total / active_count;
                for value in encoded {
                    let count = center as i128 + unzig(value);
                    if count <= 0 || count > usize::MAX as i128 {
                        return Err("invalid BWT centered active count".into());
                    }
                    first.push(count as usize);
                }
            }
            _ => unreachable!(),
        }
        let used = first
            .iter()
            .try_fold(0usize, |sum, &value| sum.checked_add(value))
            .ok_or("BWT count total overflow")?;
        let last = total
            .checked_sub(used)
            .ok_or("BWT histogram exceeds total")?;
        if last == 0 {
            return Err("zero implied BWT active count".into());
        }
        first.push(last);
        for (symbol, count) in active.into_iter().zip(first) {
            counts[symbol] = count;
        }
        return Ok(counts);
    }
    if matches!(mode, 2 | 3 | 5) {
        let encoded = decode_uints(&blob[pos..], 255, model_limit)?;
        let mut first = Vec::with_capacity(256);
        match mode {
            2 => first = encoded,
            3 => {
                let mut previous = 0i128;
                for value in encoded {
                    previous += unzig(value);
                    if previous < 0 || previous > usize::MAX as i128 {
                        return Err("negative BWT dense histogram count".into());
                    }
                    first.push(previous as usize);
                }
            }
            5 => {
                let center = total / 256;
                for value in encoded {
                    let count = center as i128 + unzig(value);
                    if count < 0 || count > usize::MAX as i128 {
                        return Err("negative BWT centered histogram count".into());
                    }
                    first.push(count as usize);
                }
            }
            _ => unreachable!(),
        }
        let used = first
            .iter()
            .try_fold(0usize, |sum, &value| sum.checked_add(value))
            .ok_or("BWT count total overflow")?;
        first.push(
            total
                .checked_sub(used)
                .ok_or("BWT dense histogram exceeds total")?,
        );
        return Ok(first);
    }
    Err(format!("unknown BWT count-vector mode {mode}"))
}

fn decode_histogram(blob: &[u8], total: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    let mut pos = 0;
    let count_length = read_varint(blob, &mut pos)?;
    let end = pos
        .checked_add(count_length)
        .ok_or("BWT histogram length overflow")?;
    if end > blob.len() {
        return Err("truncated BWT histogram".into());
    }
    let counts = decode_histogram_counts(&blob[pos..end], total, model_limit)?;
    rank::decode_type_class_with_counts(&blob[end..], total, &counts)
}

fn decode_bytes(blob: &[u8], count: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    let mode = *blob.first().ok_or("empty BWT byte substream")?;
    let mut pos = 1;
    match mode {
        0 => {
            let out = rank::decode_type_class(blob, &mut pos, count)?;
            if pos != blob.len() {
                return Err("unused static BWT byte-substream bytes".into());
            }
            Ok(out)
        }
        1 => {
            let chunk_size = read_varint(blob, &mut pos)?;
            if chunk_size == 0 {
                return Err("invalid BWT byte-substream chunk size".into());
            }
            let mut out = Vec::with_capacity(count);
            while out.len() < count {
                let size = chunk_size.min(count - out.len());
                out.extend(rank::decode_type_class(blob, &mut pos, size)?);
            }
            if pos != blob.len() {
                return Err("unused chunked BWT byte-substream bytes".into());
            }
            Ok(out)
        }
        2 => super::adaptive::decode_general(&blob[1..], count, &[], model_limit),
        3 => {
            if blob.len() < 2 || !matches!(blob[1], 1 | 2) {
                return Err("invalid BWT context byte-substream order".into());
            }
            super::adaptive::decode_general(&blob[2..], count, &[], model_limit)
        }
        4 => decode_wavelet(&blob[1..], count),
        5 => decode_histogram(&blob[1..], count, model_limit),
        _ => Err(format!("unknown BWT byte-substream mode {mode}")),
    }
}

fn decode_uints(blob: &[u8], count: usize, model_limit: usize) -> Result<Vec<usize>, String> {
    if count == 0 {
        return Ok(Vec::new());
    }
    let mode = *blob.first().ok_or("empty BWT integer stream")?;
    let mut pos = 1;
    match mode {
        0 => {
            let mut out = Vec::with_capacity(count);
            for _ in 0..count {
                out.push(read_varint(blob, &mut pos)?);
            }
            if pos != blob.len() {
                return Err("trailing BWT integer varints".into());
            }
            Ok(out)
        }
        1 => {
            let width = *blob.get(pos).ok_or("missing BWT Rice parameter")? as usize;
            pos += 1;
            if width >= usize::BITS as usize {
                return Err("BWT Rice parameter too wide".into());
            }
            let mut reader = BitReader::new(&blob[pos..]);
            let mut out = Vec::with_capacity(count);
            for _ in 0..count {
                let mut quotient = 0usize;
                while reader.bit()? != 0 {
                    quotient = quotient
                        .checked_add(1)
                        .ok_or("BWT Rice quotient overflow")?;
                }
                let low = reader.bits(width)?;
                out.push(
                    quotient
                        .checked_shl(width as u32)
                        .and_then(|value| value.checked_add(low))
                        .ok_or("BWT Rice value overflow")?,
                );
            }
            Ok(out)
        }
        2 | 3 => {
            let class_length = read_varint(blob, &mut pos)?;
            let end = pos
                .checked_add(class_length)
                .ok_or("BWT integer class length overflow")?;
            if end > blob.len() {
                return Err("truncated BWT integer class stream".into());
            }
            let classes = if mode == 2 {
                let mut class_pos = 0;
                let values = rank::decode_type_class(&blob[pos..end], &mut class_pos, count)?;
                if class_pos != class_length {
                    return Err("unused BWT integer class bytes".into());
                }
                values
            } else {
                decode_bytes(&blob[pos..end], count, model_limit)?
            };
            let mut reader = BitReader::new(&blob[end..]);
            let mut out = Vec::with_capacity(count);
            for width in classes {
                let width = width as usize;
                let low = reader.bits(width)?;
                out.push(
                    (1usize << width)
                        .checked_add(low)
                        .and_then(|value| value.checked_sub(1))
                        .ok_or("BWT integer overflow")?,
                );
            }
            Ok(out)
        }
        _ => Err(format!("unknown BWT integer stream mode {mode}")),
    }
}

fn decode_binary_tags(blob: &[u8], count: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    let mode = *blob.first().ok_or("empty BWT tag stream")?;
    match mode {
        0 => decode_bytes(&blob[1..], count, model_limit),
        1 => {
            let first = *blob.get(1).ok_or("truncated BWT run-tag stream")?;
            if first > 1 {
                return Err("invalid BWT run-tag stream".into());
            }
            let mut pos = 2;
            let run_count = read_varint(blob, &mut pos)?;
            let runs = decode_uints(&blob[pos..], run_count, model_limit)?;
            let mut tag = first;
            let mut out = Vec::with_capacity(count);
            for encoded_length in runs {
                let length = encoded_length
                    .checked_add(1)
                    .ok_or("BWT tag run overflow")?;
                let end = out
                    .len()
                    .checked_add(length)
                    .filter(|&end| end <= count)
                    .ok_or("BWT run-tag length mismatch")?;
                out.resize(end, tag);
                tag ^= 1;
            }
            if out.len() != count {
                return Err("BWT run-tag length mismatch".into());
            }
            Ok(out)
        }
        _ => Err("unknown BWT tag stream mode".into()),
    }
}

fn join_zero_runs(
    tags: &[u8],
    nonzero: &[u8],
    runs: &[usize],
    source_length: usize,
) -> Result<Vec<u8>, String> {
    let (mut nonzero_pos, mut run_pos) = (0usize, 0usize);
    let mut out = Vec::with_capacity(source_length);
    for &tag in tags {
        match tag {
            1 => {
                let value = *nonzero
                    .get(nonzero_pos)
                    .ok_or("nonzero BWT MTF stream exhausted")?;
                out.push(value);
                nonzero_pos += 1;
            }
            0 => {
                let run = runs
                    .get(run_pos)
                    .ok_or("BWT zero-run stream exhausted")?
                    .checked_add(1)
                    .ok_or("BWT zero-run overflow")?;
                let end = out
                    .len()
                    .checked_add(run)
                    .filter(|&end| end <= source_length)
                    .ok_or("BWT transformed length mismatch")?;
                out.resize(end, 0);
                run_pos += 1;
            }
            _ => return Err("invalid BWT tag value".into()),
        }
    }
    if nonzero_pos != nonzero.len() || run_pos != runs.len() {
        return Err("unused BWT substream symbols".into());
    }
    Ok(out)
}

fn decode_runa_runb(
    tokens: &[u8],
    side_bits: &[usize],
    source_length: usize,
) -> Result<Vec<u8>, String> {
    let (mut pos, mut side_pos) = (0usize, 0usize);
    let mut out = Vec::with_capacity(source_length);
    while pos < tokens.len() {
        let token = tokens[pos];
        if token <= 1 {
            let mut value = 0usize;
            let mut weight = 1usize;
            while pos < tokens.len() && tokens[pos] <= 1 {
                let factor = if tokens[pos] == 0 { 1 } else { 2 };
                value = value
                    .checked_add(weight.checked_mul(factor).ok_or("BWT run overflow")?)
                    .ok_or("BWT run overflow")?;
                weight = weight.checked_mul(2).ok_or("BWT run overflow")?;
                pos += 1;
            }
            let end = out
                .len()
                .checked_add(value)
                .filter(|&end| end <= source_length)
                .ok_or("BWT RUNA/RUNB transformed length mismatch")?;
            out.resize(end, 0);
            continue;
        }
        if token < 255 {
            out.push(token - 1);
        } else {
            let side = *side_bits
                .get(side_pos)
                .ok_or("BWT RUNA/RUNB side stream exhausted")?;
            out.push(254 + side as u8);
            side_pos += 1;
        }
        if out.len() > source_length {
            return Err("BWT RUNA/RUNB transformed length mismatch".into());
        }
        pos += 1;
    }
    if side_pos != side_bits.len() {
        return Err("unused BWT RUNA/RUNB side bits".into());
    }
    Ok(out)
}

fn mtf_decode(data: &[u8]) -> Vec<u8> {
    let mut symbols: Vec<u8> = (0..=255).collect();
    let mut out = Vec::with_capacity(data.len());
    for &index in data {
        let index = index as usize;
        let symbol = symbols[index];
        out.push(symbol);
        if index > 0 {
            symbols.copy_within(0..index, 1);
            symbols[0] = symbol;
        }
    }
    out
}

fn bwt_inverse(primary: usize, transformed: &[u8]) -> Result<Vec<u8>, String> {
    let n = transformed.len();
    if n == 0 {
        return if matches!(primary, 0 | 1) {
            Ok(Vec::new())
        } else {
            Err("invalid empty BWT primary index".into())
        };
    }
    if primary == 0 || primary > n {
        return Err("invalid BWT primary index".into());
    }
    let last: Vec<(u8, usize)> = transformed
        .iter()
        .copied()
        .enumerate()
        .map(|(index, byte)| (byte, index))
        .collect();
    let mut first = last.clone();
    first.sort_unstable();
    let mut inverse_last = vec![0usize; n];
    for (index, &(_, original_index)) in last.iter().enumerate() {
        inverse_last[original_index] = index + usize::from(index >= primary);
    }
    let mut current = first[primary - 1];
    let mut out = Vec::with_capacity(n);
    for _ in 0..n {
        out.push(current.0);
        let index = inverse_last[current.1];
        current = first[if index == 0 { n - 1 } else { index - 1 }];
    }
    Ok(out)
}

/// Decode one CIXM6 mode-4 payload.
///
/// `model_limit` bounds the number of adaptive context models used by nested
/// byte substreams. Callers should derive it from their total working-memory
/// budget, as the other legacy decoders do.
pub fn decode(blob: &[u8], source_length: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    let version = *blob.first().ok_or("empty BWT block")?;
    if !matches!(version, 1..=6) {
        return Err("unknown BWT block version".into());
    }
    let mut pos = 1;
    let primary = read_varint(blob, &mut pos)?;
    let mtf = if matches!(version, 5 | 6) {
        let token_count = read_varint(blob, &mut pos)?;
        let side_count = read_varint(blob, &mut pos)?;
        if token_count > source_length || side_count > token_count {
            return Err("invalid BWT RUNA/RUNB stream counts".into());
        }
        let token_length = read_varint(blob, &mut pos)?;
        let token_end = pos
            .checked_add(token_length)
            .ok_or("BWT token length overflow")?;
        if token_end > blob.len() {
            return Err("truncated BWT RUNA/RUNB token stream".into());
        }
        let tokens = if version == 5 {
            decode_bytes(&blob[pos..token_end], token_count, model_limit)?
        } else {
            let stream = &blob[pos..token_end];
            match stream.first() {
                Some(0) => decode_bytes(&stream[1..], token_count, model_limit)?,
                Some(1) => super::ppm::decode(&stream[1..], token_count)?,
                Some(_) => return Err("unknown BWT token coding mode".into()),
                None => return Err("missing BWT token coding mode".into()),
            }
        };
        pos = token_end;
        let side_bytes = side_count.div_ceil(8);
        if pos.checked_add(side_bytes) != Some(blob.len()) {
            return Err("BWT RUNA/RUNB side length mismatch".into());
        }
        let mut reader = BitReader::new(&blob[pos..]);
        let mut side_bits = Vec::with_capacity(side_count);
        for _ in 0..side_count {
            side_bits.push(reader.bit()?);
        }
        let decoded = decode_runa_runb(&tokens, &side_bits, source_length)?;
        if decoded.len() != source_length {
            return Err("BWT RUNA/RUNB transformed length mismatch".into());
        }
        decoded
    } else {
        let tag_count = read_varint(blob, &mut pos)?;
        let nonzero_count = read_varint(blob, &mut pos)?;
        let run_count = read_varint(blob, &mut pos)?;
        if tag_count > source_length || nonzero_count > source_length || run_count > source_length {
            return Err("invalid BWT substream counts".into());
        }
        let mut streams: Vec<&[u8]> = Vec::with_capacity(3);
        for _ in 0..3 {
            let length = read_varint(blob, &mut pos)?;
            let end = pos
                .checked_add(length)
                .ok_or("BWT substream length overflow")?;
            if end > blob.len() {
                return Err("truncated BWT substream".into());
            }
            streams.push(&blob[pos..end]);
            pos = end;
        }
        if pos != blob.len() {
            return Err("trailing BWT bytes".into());
        }
        let tags = if version == 1 {
            let mut tag_pos = 0;
            let values = rank::decode_type_class(streams[0], &mut tag_pos, tag_count)?;
            if tag_pos != streams[0].len() {
                return Err("unused BWT tag bytes".into());
            }
            values
        } else if version >= 4 {
            decode_binary_tags(streams[0], tag_count, model_limit)?
        } else {
            decode_bytes(streams[0], tag_count, model_limit)?
        };
        let nonzero = if version == 1 {
            let mut nonzero_pos = 0;
            let values = rank::decode_type_class(streams[1], &mut nonzero_pos, nonzero_count)?;
            if nonzero_pos != streams[1].len() {
                return Err("unused BWT nonzero bytes".into());
            }
            values
        } else if version == 2 {
            decode_bytes(streams[1], nonzero_count, model_limit)?
        } else {
            match streams[1].first() {
                Some(0) => decode_bytes(&streams[1][1..], nonzero_count, model_limit)?,
                Some(1) => {
                    let values = decode_uints(&streams[1][1..], nonzero_count, model_limit)?;
                    let mut out = Vec::with_capacity(values.len());
                    for value in values {
                        if value > 254 {
                            return Err("BWT MTF rank outside byte range".into());
                        }
                        out.push((value + 1) as u8);
                    }
                    out
                }
                Some(_) => return Err("unknown BWT nonzero stream mode".into()),
                None => return Err("missing BWT nonzero stream mode".into()),
            }
        };
        let runs = decode_uints(streams[2], run_count, model_limit)?;
        let decoded = join_zero_runs(&tags, &nonzero, &runs, source_length)?;
        if decoded.len() != source_length {
            return Err("BWT transformed length mismatch".into());
        }
        decoded
    };
    let restored = bwt_inverse(primary, &mtf_decode(&mtf))?;
    if restored.len() != source_length {
        return Err("BWT source length mismatch".into());
    }
    Ok(restored)
}

#[cfg(test)]
mod tests {
    use super::decode;
    use std::path::PathBuf;

    #[test]
    fn frozen_python_fixtures() {
        let Some(path) = std::env::var_os("CIX_BWT_FIXTURES") else {
            return;
        };
        let data = std::fs::read(PathBuf::from(path)).expect("read Python BWT fixtures");
        assert!(data.starts_with(b"CIXBWT1\0"));
        let mut pos = 8usize;
        let count = u32::from_le_bytes(data[pos..pos + 4].try_into().unwrap()) as usize;
        pos += 4;
        for _ in 0..count {
            let source_length = u32::from_le_bytes(data[pos..pos + 4].try_into().unwrap()) as usize;
            pos += 4;
            let payload_length =
                u32::from_le_bytes(data[pos..pos + 4].try_into().unwrap()) as usize;
            pos += 4;
            let source = &data[pos..pos + source_length];
            pos += source_length;
            let payload = &data[pos..pos + payload_length];
            pos += payload_length;
            assert_eq!(decode(payload, source_length, 1 << 16).unwrap(), source);
        }
        assert_eq!(pos, data.len());
    }

    #[test]
    fn rejects_bad_version_and_truncation() {
        assert!(decode(&[], 0, 16).is_err());
        assert!(decode(&[7], 0, 16).is_err());
        assert!(decode(&[5, 1], 1, 16).is_err());
    }
}
