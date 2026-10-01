//! Hierarchical Colour-Index decoder for legacy CIXM6 mode 18.
use crate::rank::ArithmeticDecoder;
fn node(
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
    let total = n + 1;
    let ones = decoder.target(total);
    if ones > n {
        return Err("wavelet child count out of range".into());
    }
    decoder.update(ones, ones + 1, total);
    let original_ones = ones;
    let original_zeros = n - ones;
    let (mut zero, mut one, mut remaining) = (original_zeros, original_ones, n);
    let mut bits = Vec::with_capacity(n);
    for _ in 0..n {
        let bit;
        if zero == 0 {
            bit = 1;
            decoder.update(0, one, remaining);
            one -= 1;
        } else if one == 0 {
            bit = 0;
            decoder.update(0, zero, remaining);
            zero -= 1;
        } else {
            let target = decoder.target(remaining);
            if target < zero {
                bit = 0;
                decoder.update(0, zero, remaining);
                zero -= 1;
            } else {
                bit = 1;
                decoder.update(zero, remaining, remaining);
                one -= 1;
            }
        }
        remaining -= 1;
        bits.push(bit);
    }
    let z = node(original_zeros, depth + 1, decoder, prefix << 1)?;
    let o = node(original_ones, depth + 1, decoder, (prefix << 1) | 1)?;
    let (mut zi, mut oi) = (0, 0);
    let mut out = Vec::with_capacity(n);
    for b in bits {
        if b == 1 {
            out.push(o[oi]);
            oi += 1;
        } else {
            out.push(z[zi]);
            zi += 1;
        }
    }
    Ok(out)
}
pub fn decode(data: &[u8], n: usize) -> Result<Vec<u8>, String> {
    if data.is_empty() || data[0] != 1 {
        return Err("unknown wavelet version".into());
    }
    let mut p = 1;
    let bits = super::unvar(data, &mut p)?;
    if p + (bits + 7) / 8 != data.len() {
        return Err("wavelet payload length mismatch".into());
    }
    let mut decoder = ArithmeticDecoder::new(&data[p..], bits);
    node(n, 0, &mut decoder, 0)
}
