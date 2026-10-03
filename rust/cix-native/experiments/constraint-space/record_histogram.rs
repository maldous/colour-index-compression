//! Isolated RHC1 record-dictionary plus paid-usage-histogram control.
use num_bigint::BigUint;
use num_traits::{One, Zero};
use std::{env, fs, io::Read};

const MAX_SOURCE: usize = 16_384;
const MAX_ARCHIVE: usize = 40_000;
const MAX_DICTIONARY: usize = 256;
const HEADER: usize = 15;
const MODE_RAW: u8 = 0;
const MODE_HISTOGRAM: u8 = 1;
const MODE_UNIFORM: u8 = 2;

fn fail(message: &str) -> String { message.into() }

fn bounded(path: &str, cap: usize) -> Result<Vec<u8>, String> {
    let file = fs::File::open(path).map_err(|error| error.to_string())?;
    let mut data = Vec::new();
    file.take((cap + 1) as u64).read_to_end(&mut data).map_err(|error| error.to_string())?;
    if data.len() > cap { return Err(fail("input exceeds bounded control limit")); }
    Ok(data)
}

fn crc(data: &[u8]) -> u32 {
    let mut value = !0u32;
    for &byte in data {
        value ^= u32::from(byte);
        for _ in 0..8 { value = if value & 1 != 0 { (value >> 1) ^ 0xedb88320 } else { value >> 1 }; }
    }
    !value
}

fn width(cardinality: &BigUint) -> usize {
    if cardinality.is_zero() { 0 } else { (cardinality - BigUint::one()).bits() as usize }
}

fn pack(value: &BigUint, bits: usize) -> Result<Vec<u8>, String> {
    if value.bits() > bits as u64 { return Err(fail("rank width")); }
    let bytes = bits.div_ceil(8);
    if bytes == 0 { return value.is_zero().then(Vec::new).ok_or_else(|| fail("nonzero empty rank")); }
    let source = value.to_bytes_be();
    if source.len() > bytes { return Err(fail("rank allocation")); }
    let mut out = vec![0; bytes];
    out[bytes - source.len()..].copy_from_slice(&source);
    Ok(out)
}

fn unpack(data: &[u8], bits: usize) -> Result<BigUint, String> {
    if data.len() != bits.div_ceil(8) { return Err(fail("rank width")); }
    let value = BigUint::from_bytes_be(data);
    if value.bits() > bits as u64 { return Err(fail("nonzero rank padding")); }
    Ok(value)
}

fn alphabet(data: &[u8]) -> Option<[u8; 2]> {
    let mut used = [false; 256];
    for &byte in data { used[byte as usize] = true; }
    let values: Vec<u8> = used.iter().enumerate().filter_map(|(value, present)| present.then_some(value as u8)).collect();
    (values.len() == 2).then_some([values[0], values[1]])
}

fn word(chunk: &[u8], symbols: [u8; 2]) -> usize {
    chunk.iter().fold(0usize, |value, &byte| (value << 1) | usize::from(byte == symbols[1]))
}

fn dictionary(data: &[u8], symbols: [u8; 2], b: usize) -> Vec<u16> {
    let mut used = vec![false; 1usize << b];
    for chunk in data.chunks_exact(b) { used[word(chunk, symbols)] = true; }
    used.iter().enumerate().filter_map(|(value, present)| present.then_some(value as u16)).collect()
}

fn counts(data: &[u8], symbols: [u8; 2], b: usize, words: &[u16]) -> Result<Vec<u16>, String> {
    let mut out = vec![0u16; words.len()];
    for chunk in data.chunks_exact(b) {
        let index = words.binary_search(&(word(chunk, symbols) as u16)).map_err(|_| fail("dictionary omission"))?;
        out[index] = out[index].checked_add(1).ok_or_else(|| fail("histogram count overflow"))?;
    }
    Ok(out)
}

fn multinomial(counts: &[u16]) -> BigUint {
    let mut total = BigUint::one();
    let mut seen = 0usize;
    for &count in counts {
        for denominator in 1..=usize::from(count) {
            seen += 1;
            total *= seen;
            total /= denominator;
        }
    }
    total
}

fn histogram_rank(digits: &[usize], counts: &[u16]) -> Result<(BigUint, BigUint), String> {
    let mut remaining = counts.iter().map(|&count| usize::from(count)).sum::<usize>();
    let mut left = counts.iter().map(|&count| usize::from(count)).collect::<Vec<_>>();
    let mut cardinality = multinomial(counts);
    let initial = cardinality.clone();
    let mut rank = BigUint::zero();
    for &digit in digits {
        if digit >= left.len() || left[digit] == 0 || remaining == 0 { return Err(fail("histogram sequence")); }
        for smaller in 0..digit {
            if left[smaller] != 0 { rank += (&cardinality * left[smaller]) / remaining; }
        }
        cardinality = (&cardinality * left[digit]) / remaining;
        left[digit] -= 1;
        remaining -= 1;
    }
    if !cardinality.is_one() { return Err(fail("histogram terminal cardinality")); }
    Ok((rank, initial))
}

fn histogram_unrank(mut rank: BigUint, counts: &[u16]) -> Result<Vec<usize>, String> {
    let mut remaining = counts.iter().map(|&count| usize::from(count)).sum::<usize>();
    let mut left = counts.iter().map(|&count| usize::from(count)).collect::<Vec<_>>();
    let mut cardinality = multinomial(counts);
    if rank >= cardinality { return Err(fail("histogram rank range")); }
    let mut out = Vec::with_capacity(remaining);
    while remaining != 0 {
        let mut chosen = None;
        for digit in 0..left.len() {
            if left[digit] == 0 { continue; }
            let ways = (&cardinality * left[digit]) / remaining;
            if rank < ways { chosen = Some((digit, ways)); break; }
            rank -= ways;
        }
        let (digit, ways) = chosen.ok_or_else(|| fail("impossible histogram rank"))?;
        out.push(digit);
        left[digit] -= 1;
        cardinality = ways;
        remaining -= 1;
    }
    if !rank.is_zero() || !cardinality.is_one() || left.iter().any(|&count| count != 0) { return Err(fail("histogram terminal rank")); }
    Ok(out)
}

fn uniform_rank(digits: &[usize], dictionary_size: usize) -> (BigUint, BigUint) {
    let base = BigUint::from(dictionary_size);
    let mut rank = BigUint::zero();
    for &digit in digits { rank = rank * &base + BigUint::from(digit); }
    (rank, base.pow(digits.len() as u32))
}

fn uniform_unrank(mut rank: BigUint, dictionary_size: usize, records: usize) -> Result<Vec<usize>, String> {
    let base = BigUint::from(dictionary_size);
    let card = base.pow(records as u32);
    if rank >= card { return Err(fail("uniform rank range")); }
    let mut out = vec![0; records];
    for position in (0..records).rev() {
        let digit = (&rank % &base).to_u32_digits().first().copied().unwrap_or(0) as usize;
        out[position] = digit;
        rank /= &base;
    }
    rank.is_zero().then_some(out).ok_or_else(|| fail("uniform terminal rank"))
}

fn header(mode: u8, source_len: usize, b: usize, symbols: [u8; 2], dictionary_size: usize) -> Vec<u8> {
    let mut out = b"RHC1".to_vec();
    out.extend([1, mode]);
    out.extend((source_len as u32).to_le_bytes());
    out.push(b as u8);
    out.extend(symbols);
    out.extend((dictionary_size as u16).to_le_bytes());
    debug_assert_eq!(out.len(), HEADER);
    out
}

fn raw(data: &[u8]) -> Vec<u8> {
    let mut out = header(MODE_RAW, data.len(), 0, [0, 0], 0);
    out.extend(data);
    out.extend(crc(&out).to_le_bytes());
    out
}

fn structural(data: &[u8], symbols: [u8; 2], b: usize, mode: u8) -> Result<Vec<u8>, String> {
    let words = dictionary(data, symbols, b);
    if words.is_empty() || words.len() > MAX_DICTIONARY { return Err(fail("dictionary candidate bound")); }
    let usage = counts(data, symbols, b, &words)?;
    if usage.iter().any(|&count| count == 0) { return Err(fail("noncanonical unused dictionary word")); }
    let digits = data
        .chunks_exact(b)
        .map(|chunk| words.binary_search(&(word(chunk, symbols) as u16)).map_err(|_| fail("dictionary omission")))
        .collect::<Result<Vec<_>, _>>()?;
    let (rank, cardinality) = match mode {
        MODE_HISTOGRAM => histogram_rank(&digits, &usage)?,
        MODE_UNIFORM => uniform_rank(&digits, words.len()),
        _ => return Err(fail("structural mode")),
    };
    let mut out = header(mode, data.len(), b, symbols, words.len());
    for value in &words { out.extend(value.to_le_bytes()); }
    if mode == MODE_HISTOGRAM { for count in &usage { out.extend(count.to_le_bytes()); } }
    out.extend(pack(&rank, width(&cardinality))?);
    out.extend(crc(&out).to_le_bytes());
    (out.len() <= MAX_ARCHIVE).then_some(out).ok_or_else(|| fail("archive bound"))
}

fn candidate(data: &[u8], b: usize, mode: u8) -> Option<Result<Vec<u8>, String>> {
    let symbols = alphabet(data)?;
    if data.is_empty() || data.len() % b != 0 { return None; }
    let size = dictionary(data, symbols, b).len();
    (size <= MAX_DICTIONARY).then(|| structural(data, symbols, b, mode))
}

fn encode_record(data: &[u8], uniform_only: bool) -> Result<(Vec<u8>, usize), String> {
    if data.len() > MAX_SOURCE { return Err(fail("source bound")); }
    let target_mode = if uniform_only { MODE_UNIFORM } else { MODE_HISTOGRAM };
    let mut best = raw(data);
    let mut trials = 1;
    let mut structural_best = None;
    for b in 2..=12 {
        if let Some(result) = candidate(data, b, target_mode) {
            let archive = result?;
            trials += 1;
            if structural_best.as_ref().map_or(true, |current: &Vec<u8>| archive.len() < current.len()) { structural_best = Some(archive); }
        }
    }
    if uniform_only {
        // The matched dense-rank control is retained whenever an eligible
        // dictionary exists; raw remains the generic fallback when none does.
        if let Some(archive) = structural_best { best = archive; }
    } else if let Some(archive) = structural_best.filter(|archive| archive.len() < best.len()) {
        best = archive;
    }
    Ok((best, trials))
}

fn decode_record(data: &[u8]) -> Result<Vec<u8>, String> {
    if data.len() < HEADER + 4 || data.len() > MAX_ARCHIVE || &data[..4] != b"RHC1" || data[4] != 1 { return Err(fail("RHC1 envelope")); }
    let end = data.len() - 4;
    if crc(&data[..end]) != u32::from_le_bytes(data[end..].try_into().unwrap()) { return Err(fail("CRC")); }
    let mode = data[5];
    let source_len = u32::from_le_bytes(data[6..10].try_into().unwrap()) as usize;
    let b = data[10] as usize;
    let symbols = [data[11], data[12]];
    let size = u16::from_le_bytes(data[13..15].try_into().unwrap()) as usize;
    if source_len > MAX_SOURCE { return Err(fail("source bound")); }
    if mode == MODE_RAW {
        if b != 0 || symbols != [0, 0] || size != 0 || end - HEADER != source_len { return Err(fail("raw metadata")); }
        return Ok(data[HEADER..end].to_vec());
    }
    if !(MODE_HISTOGRAM..=MODE_UNIFORM).contains(&mode) || !(2..=12).contains(&b) || source_len == 0 || source_len % b != 0 || symbols[0] >= symbols[1] || size == 0 || size > MAX_DICTIONARY || size > (1usize << b) { return Err(fail("structural metadata")); }
    let dictionary_bytes = 2 * size;
    let histogram_bytes = if mode == MODE_HISTOGRAM { 2 * size } else { 0 };
    if HEADER + dictionary_bytes + histogram_bytes > end { return Err(fail("truncated model")); }
    let mut words = Vec::with_capacity(size);
    for index in 0..size { words.push(u16::from_le_bytes(data[HEADER + 2 * index..HEADER + 2 * index + 2].try_into().unwrap())); }
    if words.windows(2).any(|pair| pair[0] >= pair[1]) || words.iter().any(|&value| usize::from(value) >= (1usize << b)) { return Err(fail("noncanonical dictionary")); }
    let histogram_start = HEADER + dictionary_bytes;
    let counts = if mode == MODE_HISTOGRAM {
        let values = (0..size).map(|index| u16::from_le_bytes(data[histogram_start + 2 * index..histogram_start + 2 * index + 2].try_into().unwrap())).collect::<Vec<_>>();
        if values.iter().any(|&count| count == 0) || values.iter().map(|&count| usize::from(count)).sum::<usize>() != source_len / b { return Err(fail("histogram counts")); }
        values
    } else { Vec::new() };
    let body = &data[histogram_start + histogram_bytes..end];
    let records = source_len / b;
    let cardinality = if mode == MODE_HISTOGRAM { multinomial(&counts) } else { BigUint::from(size).pow(records as u32) };
    let rank = unpack(body, width(&cardinality))?;
    let digits = if mode == MODE_HISTOGRAM { histogram_unrank(rank, &counts)? } else { uniform_unrank(rank, size, records)? };
    let mut out = vec![0; source_len];
    for (record, digit) in digits.into_iter().enumerate() {
        let value = words[digit];
        for bit in 0..b { out[record * b + bit] = symbols[((value >> (b - 1 - bit)) & 1) as usize]; }
    }
    // Rebuild from the output so every stored dictionary word, histogram value,
    // rank byte and candidate choice is paid and canonical.
    if alphabet(&out) != Some(symbols) || structural(&out, symbols, b, mode)? != data {
        return Err(fail("noncanonical RHC1 representation"));
    }
    Ok(out)
}

fn statistics(archive: &[u8]) -> (usize, usize, usize) {
    if archive[5] == MODE_RAW { return (0, 0, archive.len() - HEADER - 4); }
    let size = u16::from_le_bytes(archive[13..15].try_into().unwrap()) as usize;
    let model = 2 * size;
    let histogram = if archive[5] == MODE_HISTOGRAM { 2 * size } else { 0 };
    (model, histogram, archive.len() - HEADER - 4 - model - histogram)
}

fn main() -> Result<(), String> {
    let arguments: Vec<String> = env::args().collect();
    match arguments.get(1).map(String::as_str) {
        Some("encode") => {
            let mut uniform = false;
            let mut forced_width = None;
            let mut position = 2;
            while position < arguments.len() {
                match arguments[position].as_str() {
                    "--uniform" if !uniform => { uniform = true; position += 1; }
                    "--width" if forced_width.is_none() && position + 1 < arguments.len() => {
                        forced_width = Some(arguments[position + 1].parse::<usize>().map_err(|_| fail("invalid forced width"))?);
                        position += 2;
                    }
                    _ => break,
                }
            }
            if arguments.len() != position + 2 { return Err(fail("encode arguments")); }
            let input_path = &arguments[position];
            let output_path = &arguments[position + 1];
            let input = bounded(input_path, MAX_SOURCE)?;
            let (archive, trials) = if let Some(b) = forced_width {
                if !(2..=12).contains(&b) { return Err(fail("forced width must be in 2..=12")); }
                let mode = if uniform { MODE_UNIFORM } else { MODE_HISTOGRAM };
                let archive = candidate(&input, b, mode)
                    .ok_or_else(|| fail("forced width is not a binary-aligned bounded dictionary candidate"))??;
                (archive, 1)
            } else {
                encode_record(&input, uniform)?
            };
            if decode_record(&archive)? != input { return Err(fail("internal round trip")); }
            let (model, histogram, payload) = statistics(&archive);
            fs::write(output_path, &archive).map_err(|error| error.to_string())?;
            println!("{{\"complete_bytes\":{},\"model_bytes\":{},\"histogram_bytes\":{},\"payload_bytes\":{},\"trials\":{},\"mode\":{},\"width\":{},\"dictionary\":{}}}", archive.len(), model, histogram, payload, trials, archive[5], archive[10], u16::from_le_bytes(archive[13..15].try_into().unwrap()));
            Ok(())
        }
        Some("decode") if arguments.len() == 4 => {
            let archive = bounded(&arguments[2], MAX_ARCHIVE)?;
            let output = decode_record(&archive)?;
            fs::write(&arguments[3], output).map_err(|error| error.to_string())
        }
        _ => Err(fail("usage: record_histogram encode [--uniform] [--width B] INPUT ARCHIVE | record_histogram decode ARCHIVE OUTPUT")),
    }
}
