//! Isolated generic learned-record-dictionary control; no production integration.
use num_bigint::BigUint;
use num_traits::{One, Zero};
use std::{env, fs, io::Read};

const MAX_N: usize = 16_384;
const MAX_ARCHIVE: usize = 20_000;
const HEADER: usize = 15;

fn fail(message: &str) -> String {
    message.into()
}

fn bounded(path: &str, cap: usize) -> Result<Vec<u8>, String> {
    let file = fs::File::open(path).map_err(|error| error.to_string())?;
    let mut data = Vec::new();
    file.take((cap + 1) as u64)
        .read_to_end(&mut data)
        .map_err(|error| error.to_string())?;
    if data.len() > cap {
        return Err(fail("input exceeds experimental bound"));
    }
    Ok(data)
}

fn crc(data: &[u8]) -> u32 {
    let mut value = !0u32;
    for &byte in data {
        value ^= byte as u32;
        for _ in 0..8 {
            value = if value & 1 != 0 {
                (value >> 1) ^ 0xedb88320
            } else {
                value >> 1
            };
        }
    }
    !value
}

fn choose(n: usize, k: usize) -> BigUint {
    if k > n {
        return BigUint::zero();
    }
    let k = k.min(n - k);
    let mut value = BigUint::one();
    for divisor in 1..=k {
        value *= n - k + divisor;
        value /= divisor;
    }
    value
}

fn rank_width(cardinality: &BigUint) -> usize {
    if cardinality.is_zero() {
        0
    } else {
        (cardinality - BigUint::one()).bits() as usize
    }
}

fn packed_integer(value: &BigUint, width: usize) -> Result<Vec<u8>, String> {
    if value.bits() > width as u64 {
        return Err(fail("rank width"));
    }
    let bytes = width.div_ceil(8);
    if bytes == 0 {
        return value.is_zero().then(Vec::new).ok_or_else(|| fail("nonzero empty rank"));
    }
    let source = value.to_bytes_be();
    if source.len() > bytes {
        return Err(fail("rank allocation"));
    }
    let mut out = vec![0; bytes];
    out[bytes - source.len()..].copy_from_slice(&source);
    Ok(out)
}

fn unpacked_integer(data: &[u8], width: usize) -> Result<BigUint, String> {
    if data.len() != width.div_ceil(8) {
        return Err(fail("rank width"));
    }
    let value = BigUint::from_bytes_be(data);
    if value.bits() > width as u64 {
        return Err(fail("rank padding"));
    }
    Ok(value)
}

fn symbols(data: &[u8]) -> Option<[u8; 2]> {
    let mut seen = [false; 256];
    for &byte in data {
        seen[byte as usize] = true;
    }
    let mut values = seen
        .iter()
        .enumerate()
        .filter_map(|(value, &present)| present.then_some(value as u8));
    let first = values.next()?;
    let second = values.next()?;
    values.next().is_none().then_some([first, second])
}

fn word(chunk: &[u8], symbols: [u8; 2]) -> usize {
    chunk
        .iter()
        .fold(0usize, |value, &byte| (value << 1) | usize::from(byte == symbols[1]))
}

fn observed_words(data: &[u8], symbols: [u8; 2], bits: usize) -> Vec<usize> {
    let universe = 1usize << bits;
    let mut seen = vec![false; universe];
    for chunk in data.chunks_exact(bits) {
        seen[word(chunk, symbols)] = true;
    }
    seen.iter()
        .enumerate()
        .filter_map(|(value, &present)| present.then_some(value))
        .collect()
}

fn colex_rank(values: &[usize]) -> BigUint {
    values
        .iter()
        .enumerate()
        .fold(BigUint::zero(), |rank, (index, &value)| {
            rank + choose(value, index + 1)
        })
}

fn colex_unrank(mut rank: BigUint, universe: usize, count: usize) -> Result<Vec<usize>, String> {
    let mut values = vec![0; count];
    let mut upper = universe;
    for index in (1..=count).rev() {
        let mut low = index - 1;
        let mut high = upper;
        while low + 1 < high {
            let middle = low + (high - low) / 2;
            if choose(middle, index) <= rank {
                low = middle;
            } else {
                high = middle;
            }
        }
        let term = choose(low, index);
        if term > rank {
            return Err(fail("dictionary rank"));
        }
        rank -= term;
        values[index - 1] = low;
        upper = low;
    }
    if !rank.is_zero() || values.windows(2).any(|pair| pair[0] >= pair[1]) {
        return Err(fail("dictionary rank"));
    }
    Ok(values)
}

fn power(base: usize, exponent: usize) -> BigUint {
    let mut value = BigUint::one();
    let base = BigUint::from(base);
    for _ in 0..exponent {
        value *= &base;
    }
    value
}

fn header(mode: u8, n: usize, bits: usize, count: usize, symbols: [u8; 2]) -> Vec<u8> {
    let mut out = b"RDIC".to_vec();
    out.extend([1, mode]);
    out.extend((n as u32).to_le_bytes());
    out.push(bits as u8);
    out.extend((count as u16).to_le_bytes());
    out.extend(symbols);
    debug_assert_eq!(out.len(), HEADER);
    out
}

fn raw_record(data: &[u8]) -> Vec<u8> {
    let mut out = header(0, data.len(), 0, 0, [0, 0]);
    out.extend_from_slice(data);
    out.extend(crc(&out).to_le_bytes());
    out
}

fn dictionary_record(data: &[u8], symbols: [u8; 2], bits: usize) -> Result<Vec<u8>, String> {
    if !(2..=12).contains(&bits) || data.is_empty() || data.len() % bits != 0 {
        return Err(fail("dictionary parameters"));
    }
    let dictionary = observed_words(data, symbols, bits);
    let count = dictionary.len();
    if count == 0 || count > 256 {
        return Err(fail("dictionary cardinality"));
    }
    let universe = 1usize << bits;
    let dictionary_cardinality = choose(universe, count);
    let dictionary_rank = colex_rank(&dictionary);
    if dictionary_rank >= dictionary_cardinality {
        return Err(fail("dictionary rank"));
    }
    let base = BigUint::from(count);
    let mut sequence_rank = BigUint::zero();
    for chunk in data.chunks_exact(bits) {
        let value = word(chunk, symbols);
        let digit = dictionary
            .binary_search(&value)
            .map_err(|_| fail("source outside dictionary"))?;
        sequence_rank = sequence_rank * &base + digit;
    }
    let records = data.len() / bits;
    let sequence_cardinality = power(count, records);
    if sequence_rank >= sequence_cardinality {
        return Err(fail("sequence rank"));
    }
    let dictionary_body = packed_integer(&dictionary_rank, rank_width(&dictionary_cardinality))?;
    let sequence_body = packed_integer(&sequence_rank, rank_width(&sequence_cardinality))?;
    let mut out = header(1, data.len(), bits, count, symbols);
    out.extend(dictionary_body);
    out.extend(sequence_body);
    out.extend(crc(&out).to_le_bytes());
    if out.len() > MAX_ARCHIVE {
        return Err(fail("archive exceeds experimental bound"));
    }
    Ok(out)
}

fn read_u32(data: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap())
}

fn decode_record(data: &[u8]) -> Result<Vec<u8>, String> {
    if data.len() < HEADER + 4 || data.len() > MAX_ARCHIVE || &data[..4] != b"RDIC" {
        return Err(fail("RDIC envelope"));
    }
    let end = data.len() - 4;
    if crc(&data[..end]) != read_u32(data, end) {
        return Err(fail("CRC"));
    }
    if data[4] != 1 {
        return Err(fail("version"));
    }
    let mode = data[5];
    let n = read_u32(data, 6) as usize;
    let bits = data[10] as usize;
    let count = u16::from_le_bytes(data[11..13].try_into().unwrap()) as usize;
    let alphabet = [data[13], data[14]];
    let body = &data[HEADER..end];
    if n > MAX_N {
        return Err(fail("resource bound"));
    }
    if mode == 0 {
        if bits != 0 || count != 0 || alphabet != [0, 0] || body.len() != n {
            return Err(fail("raw metadata"));
        }
        return Ok(body.to_vec());
    }
    if mode != 1
        || !(2..=12).contains(&bits)
        || n == 0
        || n % bits != 0
        || count == 0
        || count > 256
        || alphabet[0] >= alphabet[1]
    {
        return Err(fail("dictionary metadata"));
    }
    let universe = 1usize << bits;
    if count > universe {
        return Err(fail("dictionary cardinality"));
    }
    let dictionary_cardinality = choose(universe, count);
    let records = n / bits;
    let sequence_cardinality = power(count, records);
    let dictionary_width = rank_width(&dictionary_cardinality);
    let sequence_width = rank_width(&sequence_cardinality);
    let dictionary_bytes = dictionary_width.div_ceil(8);
    let sequence_bytes = sequence_width.div_ceil(8);
    if body.len() != dictionary_bytes.saturating_add(sequence_bytes) {
        return Err(fail("trailing or truncated ranks"));
    }
    let dictionary_rank = unpacked_integer(&body[..dictionary_bytes], dictionary_width)?;
    if dictionary_rank >= dictionary_cardinality {
        return Err(fail("dictionary rank range"));
    }
    let dictionary = colex_unrank(dictionary_rank, universe, count)?;
    let mut sequence_rank = unpacked_integer(&body[dictionary_bytes..], sequence_width)?;
    if sequence_rank >= sequence_cardinality {
        return Err(fail("sequence rank range"));
    }
    let base = BigUint::from(count);
    let mut out = vec![0u8; n];
    for record in (0..records).rev() {
        let digits = (&sequence_rank % &base).to_u32_digits();
        let digit = digits.first().copied().unwrap_or(0) as usize;
        sequence_rank /= &base;
        let value = dictionary[digit];
        for bit in 0..bits {
            out[record * bits + bit] = alphabet[((value >> (bits - 1 - bit)) & 1) as usize];
        }
    }
    if !sequence_rank.is_zero() {
        return Err(fail("terminal sequence rank"));
    }
    Ok(out)
}

fn encode_record(data: &[u8]) -> Result<(Vec<u8>, usize), String> {
    if data.len() > MAX_N {
        return Err(fail("source bound"));
    }
    let mut best = raw_record(data);
    let mut trials = 1;
    if let Some(alphabet) = symbols(data) {
        for bits in 2..=12 {
            if data.len() % bits != 0 {
                continue;
            }
            if observed_words(data, alphabet, bits).len() > 256 {
                continue;
            }
            let candidate = dictionary_record(data, alphabet, bits)?;
            trials += 1;
            if candidate.len() < best.len() {
                best = candidate;
            }
        }
    }
    Ok((best, trials))
}

fn main() -> Result<(), String> {
    let arguments: Vec<String> = env::args().collect();
    match arguments.get(1).map(String::as_str) {
        Some("encode") if arguments.len() == 4 => {
            let input = bounded(&arguments[2], MAX_N)?;
            let (archive, trials) = encode_record(&input)?;
            if decode_record(&archive)? != input {
                return Err(fail("internal round trip"));
            }
            fs::write(&arguments[3], &archive).map_err(|error| error.to_string())?;
            println!(
                "bytes={} trials={} mode={} width={} dictionary={}",
                archive.len(),
                trials,
                archive[5],
                archive[10],
                u16::from_le_bytes(archive[11..13].try_into().unwrap())
            );
            Ok(())
        }
        Some("decode") if arguments.len() == 4 => {
            let archive = bounded(&arguments[2], MAX_ARCHIVE)?;
            let output = decode_record(&archive)?;
            fs::write(&arguments[3], output).map_err(|error| error.to_string())
        }
        _ => Err(fail(
            "usage: rdic encode INPUT ARCHIVE | rdic decode ARCHIVE OUTPUT",
        )),
    }
}
