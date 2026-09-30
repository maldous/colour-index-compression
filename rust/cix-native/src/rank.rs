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
        return Err("CIX arithmetic sequence coding is not implemented yet".into());
    }
    out.push(0); // canonical rank mode
    out.extend(fixed_bytes(&permutation_rank(data, &counts)?, width));
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
    if mode != 0 {
        return Err(format!("unsupported CIX type-class sequence mode {mode}"));
    }
    let rank = read_fixed(data, pos, width)?;
    permutation_unrank(rank, &counts)
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
