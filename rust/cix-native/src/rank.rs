//! Exact CIX type-class rank coding used by CIXG1 composition substreams.
//!
//! Combinatorial ranks are arbitrary precision. The 1024-symbol tiles used by
//! CIXG1 can produce ranks thousands of bits wide; converting them to machine
//! integers would silently corrupt archives.

use num_bigint::BigUint;
use num_traits::{One, Zero};

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

fn fixed_bytes(value: &BigUint, width_bits: usize) -> Vec<u8> {
    let size = width_bits.div_ceil(8);
    if size == 0 {
        return Vec::new();
    }
    let bytes = value.to_bytes_be();
    let mut out = vec![0; size.saturating_sub(bytes.len())];
    out.extend_from_slice(&bytes);
    out
}

fn read_fixed(data: &[u8], pos: &mut usize, width_bits: usize) -> Result<BigUint, String> {
    let size = width_bits.div_ceil(8);
    let end = pos.checked_add(size).ok_or("rank offset overflow")?;
    if end > data.len() {
        return Err("truncated CIX rank".into());
    }
    let value = BigUint::from_bytes_be(&data[*pos..end]);
    if width_bits % 8 != 0 && size > 0 {
        let excess = 8 - width_bits % 8;
        if data[*pos] >> (8 - excess) != 0 {
            return Err("nonzero padding in CIX rank".into());
        }
    }
    *pos = end;
    Ok(value)
}

fn varint(value: usize, out: &mut Vec<u8>) {
    let mut v = value;
    while v >= 128 {
        out.push((v as u8 & 0x7f) | 0x80);
        v >>= 7;
    }
    out.push(v as u8);
}

fn read_varint(data: &[u8], pos: &mut usize) -> Result<usize, String> {
    let mut value = 0usize;
    for shift in (0..35).step_by(7) {
        let byte = *data.get(*pos).ok_or("truncated CIX varint")?;
        *pos += 1;
        value |= ((byte & 0x7f) as usize)
            .checked_shl(shift)
            .ok_or("oversized CIX varint")?;
        if byte < 128 {
            return Ok(value);
        }
    }
    Err("oversized CIX varint".into())
}

struct BitWriter {
    data: Vec<u8>,
    current: u8,
    used: u8,
    bit_length: usize,
}

impl BitWriter {
    fn new() -> Self {
        Self {
            data: Vec::new(),
            current: 0,
            used: 0,
            bit_length: 0,
        }
    }
    fn write(&mut self, bit: u8) {
        self.current = (self.current << 1) | (bit & 1);
        self.used += 1;
        self.bit_length += 1;
        if self.used == 8 {
            self.data.push(self.current);
            self.current = 0;
            self.used = 0;
        }
    }
    fn finish(mut self) -> (Vec<u8>, usize) {
        if self.used > 0 {
            self.data.push(self.current << (8 - self.used));
        }
        (self.data, self.bit_length)
    }
}

pub struct ArithmeticEncoder {
    low: u64,
    high: u64,
    pending: usize,
    writer: BitWriter,
}

impl ArithmeticEncoder {
    const HALF: u64 = 1 << 31;
    const Q1: u64 = 1 << 30;
    const Q3: u64 = 3 << 30;
    const MAX: u64 = (1 << 32) - 1;

    pub fn new() -> Self {
        Self {
            low: 0,
            high: Self::MAX,
            pending: 0,
            writer: BitWriter::new(),
        }
    }
    fn emit(&mut self, bit: u8) {
        self.writer.write(bit);
        while self.pending > 0 {
            self.writer.write(bit ^ 1);
            self.pending -= 1;
        }
    }
    pub fn encode(&mut self, low_count: usize, high_count: usize, total: usize) {
        let interval = self.high - self.low + 1;
        self.high = self.low + (interval * high_count as u64 / total as u64) - 1;
        self.low += interval * low_count as u64 / total as u64;
        loop {
            if self.high < Self::HALF {
                self.emit(0);
            } else if self.low >= Self::HALF {
                self.emit(1);
                self.low -= Self::HALF;
                self.high -= Self::HALF;
            } else if self.low >= Self::Q1 && self.high < Self::Q3 {
                self.pending += 1;
                self.low -= Self::Q1;
                self.high -= Self::Q1;
            } else {
                break;
            }
            self.low <<= 1;
            self.high = (self.high << 1) + 1;
        }
    }
    pub fn finish(mut self) -> (Vec<u8>, usize) {
        self.pending += 1;
        self.emit(if self.low < Self::Q1 { 0 } else { 1 });
        self.writer.finish()
    }
}

struct BitReader<'a> {
    data: &'a [u8],
    bit_length: usize,
    pos: usize,
}

impl<'a> BitReader<'a> {
    fn read(&mut self) -> u8 {
        if self.pos >= self.bit_length {
            self.pos += 1;
            return 0;
        }
        let bit = (self.data[self.pos >> 3] >> (7 - (self.pos & 7))) & 1;
        self.pos += 1;
        bit
    }
}

pub struct ArithmeticDecoder<'a> {
    reader: BitReader<'a>,
    low: u64,
    high: u64,
    value: u64,
}

impl<'a> ArithmeticDecoder<'a> {
    pub fn new(data: &'a [u8], bit_length: usize) -> Self {
        let mut result = Self {
            reader: BitReader {
                data,
                bit_length,
                pos: 0,
            },
            low: 0,
            high: ArithmeticEncoder::MAX,
            value: 0,
        };
        for _ in 0..32 {
            result.value = (result.value << 1) | result.reader.read() as u64;
        }
        result
    }
    pub fn target(&self, total: usize) -> usize {
        let interval = self.high - self.low + 1;
        (((self.value - self.low + 1) * total as u64 - 1) / interval) as usize
    }
    pub fn update(&mut self, low_count: usize, high_count: usize, total: usize) {
        let interval = self.high - self.low + 1;
        self.high = self.low + interval * high_count as u64 / total as u64 - 1;
        self.low += interval * low_count as u64 / total as u64;
        loop {
            if self.high < ArithmeticEncoder::HALF {
            } else if self.low >= ArithmeticEncoder::HALF {
                self.low -= ArithmeticEncoder::HALF;
                self.high -= ArithmeticEncoder::HALF;
                self.value -= ArithmeticEncoder::HALF;
            } else if self.low >= ArithmeticEncoder::Q1 && self.high < ArithmeticEncoder::Q3 {
                self.low -= ArithmeticEncoder::Q1;
                self.high -= ArithmeticEncoder::Q1;
                self.value -= ArithmeticEncoder::Q1;
            } else {
                break;
            }
            self.low <<= 1;
            self.high = (self.high << 1) + 1;
            self.value = (self.value << 1) | self.reader.read() as u64;
        }
    }
}

fn encode_sequence_range(data: &[u8], counts: &[usize]) -> (Vec<u8>, usize) {
    let mut mutable = counts.to_vec();
    let mut fenwick = Fenwick::new(&mutable);
    let mut remaining = data.len();
    let mut encoder = ArithmeticEncoder::new();
    for &symbol in data {
        let i = symbol as usize;
        let low = fenwick.prefix(i);
        let high = low + mutable[i];
        encoder.encode(low, high, remaining);
        mutable[i] -= 1;
        fenwick.add(i, -1);
        remaining -= 1;
    }
    encoder.finish()
}

/// Python CIXG1's matched-information count-range control (coder 5).
pub fn encode_count_range(data: &[u8]) -> Result<Vec<u8>, String> {
    let mut out = Vec::new();
    for tile in data.chunks(1024) {
        let exact = encode_type_class(tile)?;
        let mut counts = [0usize; 256];
        for &value in tile {
            counts[value as usize] += 1;
        }
        let ways = cardinality(&counts);
        let width = fixed_width(&(&ways - BigUint::one()));
        let sequence_bytes = width.div_ceil(8);
        let header_end = exact
            .len()
            .checked_sub(sequence_bytes + 1)
            .ok_or("invalid exact-rank header")?;
        let (payload, bit_length) = encode_sequence_range(tile, &counts);
        let mut encoded = exact[..header_end].to_vec();
        encoded.push(1);
        varint(bit_length, &mut encoded);
        encoded.extend_from_slice(&payload);
        varint(encoded.len(), &mut out);
        out.extend_from_slice(&encoded);
    }
    Ok(out)
}

fn decode_sequence_range(
    payload: &[u8],
    bit_length: usize,
    counts: &[usize],
) -> Result<Vec<u8>, String> {
    let mut mutable = counts.to_vec();
    let mut fenwick = Fenwick::new(&mutable);
    let mut remaining: usize = counts.iter().sum();
    let mut decoder = ArithmeticDecoder::new(payload, bit_length);
    let mut out = Vec::with_capacity(remaining);
    while remaining > 0 {
        let target = decoder.target(remaining);
        let symbol = fenwick.select(target)?;
        let low = fenwick.prefix(symbol);
        let high = low + mutable[symbol];
        decoder.update(low, high, remaining);
        out.push(symbol as u8);
        mutable[symbol] -= 1;
        fenwick.add(symbol, -1);
        remaining -= 1;
    }
    Ok(out)
}

fn colex_rank(values: &[usize]) -> BigUint {
    values
        .iter()
        .enumerate()
        .fold(BigUint::zero(), |sum, (i, &v)| sum + choose(v, i + 1))
}

fn colex_unrank(mut rank: BigUint, k: usize, universe: usize) -> Result<Vec<usize>, String> {
    let limit = choose(universe, k);
    if k > universe || rank >= limit {
        return Err("combination rank outside range".into());
    }
    let mut result = Vec::with_capacity(k);
    let mut x = universe.saturating_sub(1);
    for i in (1..=k).rev() {
        while choose(x, i) > rank {
            if x == 0 {
                return Err("invalid combination rank".into());
            }
            x -= 1;
        }
        rank -= choose(x, i);
        result.push(x);
        x = x.saturating_sub(1);
    }
    result.reverse();
    Ok(result)
}

fn composition_rank(parts: &[usize]) -> Result<BigUint, String> {
    if parts.is_empty() || parts.iter().any(|&x| x == 0) {
        return Err("invalid CIX composition".into());
    }
    let mut total = 0usize;
    let mut cuts = Vec::with_capacity(parts.len().saturating_sub(1));
    for &part in &parts[..parts.len() - 1] {
        total = total.checked_add(part).ok_or("composition overflow")?;
        cuts.push(total - 1);
    }
    Ok(colex_rank(&cuts))
}

fn composition_unrank(rank: BigUint, total: usize, count: usize) -> Result<Vec<usize>, String> {
    if count == 0 || total == 0 || count > total {
        return Err("invalid CIX composition dimensions".into());
    }
    if count == 1 {
        return if rank.is_zero() {
            Ok(vec![total])
        } else {
            Err("invalid one-part composition rank".into())
        };
    }
    let cuts = colex_unrank(rank, count - 1, total - 1)?
        .into_iter()
        .map(|x| x + 1);
    let mut previous = 0;
    let mut parts = Vec::with_capacity(count);
    for cut in cuts {
        parts.push(cut - previous);
        previous = cut;
    }
    parts.push(total - previous);
    Ok(parts)
}

#[derive(Clone)]
struct Fenwick {
    tree: Vec<usize>,
}

impl Fenwick {
    fn new(counts: &[usize]) -> Self {
        let mut result = Self {
            tree: vec![0; counts.len() + 1],
        };
        for (i, &count) in counts.iter().enumerate() {
            if count > 0 {
                result.add(i, count as isize);
            }
        }
        result
    }

    fn add(&mut self, index: usize, delta: isize) {
        let mut i = index + 1;
        while i < self.tree.len() {
            if delta >= 0 {
                self.tree[i] += delta as usize;
            } else {
                self.tree[i] -= (-delta) as usize;
            }
            i += i & i.wrapping_neg();
        }
    }

    fn prefix(&self, end: usize) -> usize {
        let mut i = end;
        let mut sum = 0;
        while i > 0 {
            sum += self.tree[i];
            i &= i - 1;
        }
        sum
    }

    fn select(&self, mut order: usize) -> Result<usize, String> {
        let n = self.tree.len() - 1;
        let mut index = 0;
        let mut bit = 1usize << (usize::BITS - n.leading_zeros() - 1);
        while bit > 0 {
            let next = index + bit;
            if next <= n && self.tree[next] <= order {
                order -= self.tree[next];
                index = next;
            }
            bit >>= 1;
        }
        if index >= n {
            Err("CIX rank selected outside active alphabet".into())
        } else {
            Ok(index)
        }
    }
}

fn cardinality(counts: &[usize]) -> BigUint {
    let mut remaining: usize = counts.iter().sum();
    let mut total = BigUint::one();
    for &count in counts {
        if count > 0 {
            total *= choose(remaining, count);
            remaining -= count;
        }
    }
    total
}

fn permutation_rank(data: &[u8], counts: &[usize]) -> Result<BigUint, String> {
    let mut mutable = counts.to_vec();
    let mut fenwick = Fenwick::new(&mutable);
    let mut remaining = data.len();
    let mut ways = cardinality(counts);
    let mut rank = BigUint::zero();
    for &symbol in data {
        let i = symbol as usize;
        let before = fenwick.prefix(i);
        if before > 0 {
            rank += (&ways * before) / remaining;
        }
        let occurrences = mutable[i];
        if occurrences == 0 || remaining == 0 {
            return Err("symbol absent from CIX histogram".into());
        }
        ways = (ways * occurrences) / remaining;
        mutable[i] -= 1;
        fenwick.add(i, -1);
        remaining -= 1;
    }
    Ok(rank)
}

fn permutation_unrank(mut rank: BigUint, counts: &[usize]) -> Result<Vec<u8>, String> {
    let mut mutable = counts.to_vec();
    let mut fenwick = Fenwick::new(&mutable);
    let mut remaining: usize = counts.iter().sum();
    let mut ways = cardinality(counts);
    if rank >= ways {
        return Err("permutation rank outside type class".into());
    }
    let mut output = Vec::with_capacity(remaining);
    while remaining > 0 {
        let order = ((&rank * remaining) / &ways)
            .try_into()
            .map_err(|_| "CIX rank selection overflow")?;
        let symbol = fenwick.select(order)?;
        let before = fenwick.prefix(symbol);
        rank -= (&ways * before) / remaining;
        let occurrences = mutable[symbol];
        ways = (ways * occurrences) / remaining;
        mutable[symbol] -= 1;
        fenwick.add(symbol, -1);
        remaining -= 1;
        output.push(symbol as u8);
    }
    Ok(output)
}

pub fn encode_type_class(data: &[u8]) -> Result<Vec<u8>, String> {
    let mut counts = [0usize; 256];
    for &byte in data {
        counts[byte as usize] += 1;
    }
    let active: Vec<usize> = counts
        .iter()
        .enumerate()
        .filter_map(|(symbol, &count)| (count > 0).then_some(symbol))
        .collect();
    let m = active.len();
    let mut out = Vec::new();
    varint(m, &mut out);
    if data.is_empty() {
        return Ok(out);
    }
    if m < 256 {
        let width = fixed_width(&(choose(256, m) - BigUint::one()));
        out.extend(fixed_bytes(&colex_rank(&active), width));
    }
    let parts: Vec<usize> = active.iter().map(|&s| counts[s]).collect();
    if m > 1 {
        let width = fixed_width(&(choose(data.len() - 1, m - 1) - BigUint::one()));
        out.extend(fixed_bytes(&composition_rank(&parts)?, width));
    }
    let ways = cardinality(&counts);
    let width = fixed_width(&(&ways - BigUint::one()));
    if data.len() >= 2048 && ways > BigUint::one() {
        let (payload, bit_length) = encode_sequence_range(data, &counts);
        out.push(1);
        varint(bit_length, &mut out);
        out.extend_from_slice(&payload);
    } else {
        out.push(0); // canonical rank mode
        out.extend(fixed_bytes(&permutation_rank(data, &counts)?, width));
    }
    Ok(out)
}

pub fn decode_type_class(data: &[u8], pos: &mut usize, n: usize) -> Result<Vec<u8>, String> {
    let m = read_varint(data, pos)?;
    if n == 0 {
        if m != 0 {
            return Err("active symbols in empty CIX type class".into());
        }
        return Ok(Vec::new());
    }
    if m == 0 || m > 256 || m > n {
        return Err("invalid CIX active alphabet".into());
    }
    let active = if m == 256 {
        (0..256).collect()
    } else {
        let width = fixed_width(&(choose(256, m) - BigUint::one()));
        colex_unrank(read_fixed(data, pos, width)?, m, 256)?
    };
    let parts = if m == 1 {
        vec![n]
    } else {
        let width = fixed_width(&(choose(n - 1, m - 1) - BigUint::one()));
        composition_unrank(read_fixed(data, pos, width)?, n, m)?
    };
    let mut counts = vec![0usize; 256];
    for (&symbol, count) in active.iter().zip(parts) {
        counts[symbol] = count;
    }
    let ways = cardinality(&counts);
    let width = fixed_width(&(&ways - BigUint::one()));
    let mode = *data.get(*pos).ok_or("missing CIX sequence mode")?;
    *pos += 1;
    match mode {
        0 => {
            let rank = read_fixed(data, pos, width)?;
            permutation_unrank(rank, &counts)
        }
        1 => {
            let bit_length = read_varint(data, pos)?;
            let byte_length = bit_length.div_ceil(8);
            let end = pos
                .checked_add(byte_length)
                .ok_or("range stream length overflow")?;
            if end > data.len() {
                return Err("truncated CIX range stream".into());
            }
            let result = decode_sequence_range(&data[*pos..end], bit_length, &counts)?;
            *pos = end;
            Ok(result)
        }
        _ => Err(format!("unsupported CIX type-class sequence mode {mode}")),
    }
}

pub fn encode_composition_tiles(data: &[u8]) -> Result<Vec<u8>, String> {
    let mut out = Vec::new();
    for tile in data.chunks(1024) {
        let encoded = encode_type_class(tile)?;
        varint(encoded.len(), &mut out);
        out.extend_from_slice(&encoded);
    }
    Ok(out)
}

pub fn decode_composition_tiles(data: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let mut pos = 0;
    let mut output = Vec::with_capacity(n);
    while output.len() < n {
        let size = read_varint(data, &mut pos)?;
        let end = pos.checked_add(size).ok_or("CIX tile length overflow")?;
        if end > data.len() {
            return Err("truncated CIX composition tile".into());
        }
        let mut tile_pos = 0;
        let tile_n = (n - output.len()).min(1024);
        let decoded = decode_type_class(&data[pos..end], &mut tile_pos, tile_n)?;
        if tile_pos != size {
            return Err("trailing bytes in CIX composition tile".into());
        }
        output.extend(decoded);
        pos = end;
    }
    if pos != data.len() {
        return Err("trailing CIX composition data".into());
    }
    Ok(output)
}

/// Decode the legacy CIX sparse dominant-symbol representation.
pub fn decode_sparse_blob(data: &[u8], n: usize) -> Result<Vec<u8>, String> {
    if data.len() < 2 || data[0] != 1 {
        return Err("unknown sparse block version".into());
    }
    let dominant = data[1];
    let mut pos = 2;
    let k = read_varint(data, &mut pos)?;
    if k > n {
        return Err("too many sparse exceptions".into());
    }
    let width = fixed_width(&(choose(n, k) - BigUint::one()));
    let ranks = colex_unrank(read_fixed(data, &mut pos, width)?, k, n)?;
    let mut value_pos = pos;
    let values = decode_type_class(data, &mut value_pos, k)?;
    if value_pos != data.len() {
        return Err("unused sparse payload bytes".into());
    }
    let mut out = vec![dominant; n];
    for (index, value) in ranks.into_iter().zip(values) {
        out[index] = value;
    }
    Ok(out)
}
