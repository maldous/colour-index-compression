//! CIXG1 adaptive multinomial byte substream (order 0, bucket bits 8).
use crate::rank::{ArithmeticDecoder, ArithmeticEncoder};

struct Model {
    counts: [u32; 256],
    tree: [u32; 257],
    seen: u32,
}
impl Model {
    fn new() -> Self {
        Self {
            counts: [0; 256],
            tree: [0; 257],
            seen: 0,
        }
    }
    fn prefix(&self, symbol: usize) -> u32 {
        let mut i = symbol;
        let mut sum = 0;
        while i > 0 {
            sum += self.tree[i];
            i &= i - 1;
        }
        sum
    }
    fn interval(&self, symbol: usize) -> (usize, usize, usize) {
        let low = 2 * self.prefix(symbol) as usize + symbol;
        (
            low,
            low + 2 * self.counts[symbol] as usize + 1,
            2 * self.seen as usize + 256,
        )
    }
    fn add(&mut self, symbol: usize) {
        self.counts[symbol] += 1;
        self.seen += 1;
        let mut i = symbol + 1;
        while i <= 256 {
            self.tree[i] += 1;
            i += i & i.wrapping_neg();
        }
    }
    fn select(&self, target: usize) -> Result<(usize, usize, usize, usize), String> {
        let mut lo = 0usize;
        let mut hi = 255usize;
        while lo < hi {
            let mid = (lo + hi + 1) / 2;
            if 2 * self.prefix(mid) as usize + mid <= target {
                lo = mid;
            } else {
                hi = mid - 1;
            }
        }
        let (a, b, t) = self.interval(lo);
        if !(a <= target && target < b) {
            return Err("adaptive target outside symbol interval".into());
        }
        Ok((lo, a, b, t))
    }
}
fn put_varint(mut value: usize, out: &mut Vec<u8>) {
    while value >= 128 {
        out.push((value as u8 & 127) | 128);
        value >>= 7;
    }
    out.push(value as u8);
}
fn get_varint(data: &[u8], pos: &mut usize) -> Result<usize, String> {
    let mut value = 0usize;
    for shift in (0..usize::BITS as usize).step_by(7) {
        let byte = *data.get(*pos).ok_or("truncated adaptive bit length")?;
        *pos += 1;
        value |= ((byte & 127) as usize)
            .checked_shl(shift as u32)
            .ok_or("adaptive varint overflow")?;
        if byte < 128 {
            return Ok(value);
        }
    }
    Err("oversized adaptive varint".into())
}
pub fn encode(data: &[u8]) -> Vec<u8> {
    let mut model = Model::new();
    let mut coder = ArithmeticEncoder::new();
    for &b in data {
        let (low, high, total) = model.interval(b as usize);
        coder.encode(low, high, total);
        model.add(b as usize);
    }
    let (payload, bits) = coder.finish();
    let mut out = vec![1, 0, 8];
    put_varint(bits, &mut out);
    out.extend(payload);
    out
}
pub fn decode(blob: &[u8], n: usize) -> Result<Vec<u8>, String> {
    if blob.len() < 4 || blob[0] != 1 || blob[1] != 0 || blob[2] != 8 {
        return Err("unsupported adaptive substream model".into());
    }
    let mut pos = 3;
    let bits = get_varint(blob, &mut pos)?;
    let bytes = bits.div_ceil(8);
    if pos.checked_add(bytes) != Some(blob.len()) {
        return Err("adaptive payload length mismatch".into());
    }
    let mut model = Model::new();
    let mut coder = ArithmeticDecoder::new(&blob[pos..], bits);
    let mut out = Vec::with_capacity(n);
    for _ in 0..n {
        let target = coder.target(2 * model.seen as usize + 256);
        let (symbol, low, high, total) = model.select(target)?;
        coder.update(low, high, total);
        model.add(symbol);
        out.push(symbol as u8);
    }
    Ok(out)
}
