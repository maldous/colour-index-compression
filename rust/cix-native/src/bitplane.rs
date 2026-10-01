//! Legacy CIXM6 bit-plane block decoder (exact-rank v1 and arithmetic v2).
use crate::rank::{self, ArithmeticDecoder};
fn read_v(data: &[u8], p: &mut usize) -> Result<usize, String> {
    super::unvar(data, p)
}
pub fn decode(data: &[u8], n: usize) -> Result<Vec<u8>, String> {
    if data.is_empty() || !matches!(data[0], 1 | 2) {
        return Err("unknown bit-plane version".into());
    }
    let version = data[0];
    let mut p = 1;
    let mut out = vec![0u8; n];
    if version == 1 {
        for shift in (0..8).rev() {
            let majority = *data.get(p).ok_or("truncated bit-plane header")?;
            p += 1;
            if majority > 1 {
                return Err("invalid bit-plane majority".into());
            }
            let k = read_v(data, &mut p)?;
            if k > n {
                return Err("invalid bit-plane minority".into());
            }
            let positions = rank::decode_colex_positions(data, &mut p, n, k)?;
            if majority == 1 {
                for b in &mut out {
                    *b |= 1 << shift;
                }
                for i in positions {
                    out[i] &= !(1 << shift);
                }
            } else {
                for i in positions {
                    out[i] |= 1 << shift;
                }
            }
        }
        if p != data.len() {
            return Err("trailing bit-plane data".into());
        }
        return Ok(out);
    }
    let mut ones = Vec::with_capacity(8);
    for _ in 0..8 {
        let majority = *data.get(p).ok_or("truncated bit-plane header")?;
        p += 1;
        if majority > 1 {
            return Err("invalid bit-plane majority".into());
        }
        let minority = read_v(data, &mut p)?;
        if minority > n {
            return Err("invalid bit-plane minority".into());
        }
        ones.push(if majority == 1 {
            n - minority
        } else {
            minority
        });
    }
    let bit_length = read_v(data, &mut p)?;
    if p + (bit_length + 7) / 8 != data.len() {
        return Err("bit-plane arithmetic payload length mismatch".into());
    }
    let mut decoder = ArithmeticDecoder::new(&data[p..], bit_length);
    for (plane, &one_count) in ones.iter().enumerate() {
        let mut one = one_count;
        let mut zero = n - one_count;
        for i in 0..n {
            let total = one + zero;
            let target = decoder.target(total);
            if target < zero {
                decoder.update(0, zero, total);
                zero -= 1;
            } else {
                decoder.update(zero, total, total);
                one -= 1;
                out[i] |= 1 << (7 - plane);
            }
        }
    }
    Ok(out)
}
