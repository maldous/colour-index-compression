//! Decoder for legacy CIXM6 count-vector histogram type classes (mode 20).
use crate::rank;
fn unzig(value: usize) -> i128 {
    let v = value as i128;
    if value & 1 == 0 {
        v / 2
    } else {
        -(v / 2) - 1
    }
}
fn read_counts(blob: &[u8], total: usize) -> Result<Vec<usize>, String> {
    if blob.len() < 2 || blob[0] != 1 {
        return Err("unknown count-vector version".into());
    }
    let mode = blob[1];
    let mut p = 2;
    let mut counts = vec![0usize; 256];
    if matches!(mode, 0 | 1 | 4) {
        let m = super::unvar(blob, &mut p)?;
        if m == 0 || m > 256 || m > total {
            return Err("invalid active count alphabet".into());
        }
        let active = if m == 256 {
            (0..256).collect()
        } else {
            rank::decode_colex_positions(blob, &mut p, 256, m)?
        };
        let values = super::m6_decode_uints(&blob[p..], m - 1, 1 << 16)?;
        let mut first = Vec::with_capacity(m);
        match mode {
            0 => first.extend(values.into_iter().map(|v| v.saturating_add(1))),
            1 => {
                let mut previous = 0i128;
                for v in values {
                    previous += unzig(v);
                    if previous <= 0 {
                        return Err("invalid active count delta".into());
                    }
                    first.push(previous as usize);
                }
            }
            4 => {
                let center = total / m;
                for v in values {
                    let c = center as i128 + unzig(v);
                    if c <= 0 {
                        return Err("invalid centered active count".into());
                    }
                    first.push(c as usize);
                }
            }
            _ => unreachable!(),
        }
        let last = total
            .checked_sub(first.iter().sum())
            .ok_or("active histogram exceeds total")?;
        if last == 0 {
            return Err("zero implied active count".into());
        }
        first.push(last);
        for (symbol, count) in active.into_iter().zip(first) {
            counts[symbol] = count;
        }
        return Ok(counts);
    }
    if matches!(mode, 2 | 3 | 5) {
        let values = super::m6_decode_uints(&blob[p..], 255, 1 << 16)?;
        let mut first = Vec::with_capacity(255);
        match mode {
            2 => first = values,
            3 => {
                let mut previous = 0i128;
                for v in values {
                    previous += unzig(v);
                    if previous < 0 {
                        return Err("negative dense histogram count".into());
                    }
                    first.push(previous as usize);
                }
            }
            5 => {
                let center = total / 256;
                for v in values {
                    let c = center as i128 + unzig(v);
                    if c < 0 {
                        return Err("negative centered histogram count".into());
                    }
                    first.push(c as usize);
                }
            }
            _ => unreachable!(),
        }
        let last = total
            .checked_sub(first.iter().sum())
            .ok_or("dense histogram exceeds total")?;
        first.push(last);
        return Ok(first);
    }
    Err(format!("unknown count-vector mode {mode}"))
}
pub fn decode_type_class(blob: &[u8], total: usize) -> Result<Vec<u8>, String> {
    let mut p = 0;
    let len = super::unvar(blob, &mut p)?;
    let end = p.checked_add(len).ok_or("histogram length overflow")?;
    if end > blob.len() {
        return Err("truncated CIX histogram".into());
    }
    let counts = read_counts(&blob[p..end], total)?;
    rank::decode_type_class_with_counts(&blob[end..], total, &counts)
}
