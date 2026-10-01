//! Decoder for the frozen CIX reversible transform representation (CIXM6 mode 5).

use crate::rank;
use std::collections::HashMap;

#[derive(Clone, Copy)]
enum Operation {
    ByteXor(usize),
    ByteDelta(usize),
    WordXor,
    WordDelta,
    WordDelta2,
    WordDelta2Zigzag,
    MatchXor,
}

#[derive(Clone, Copy)]
struct Spec {
    width: usize,
    big_endian: bool,
    shuffled: bool,
    operation: Operation,
}

fn spec(id: u8) -> Option<Spec> {
    let little = false;
    let big = true;
    let word = |width, big_endian, operation| Spec {
        width,
        big_endian,
        shuffled: true,
        operation,
    };
    let byte = |operation| Spec {
        width: 1,
        big_endian: little,
        shuffled: false,
        operation,
    };

    Some(match id {
        1 => byte(Operation::ByteXor(1)),
        2 => byte(Operation::ByteXor(2)),
        3 => byte(Operation::ByteXor(4)),
        4 => byte(Operation::ByteDelta(1)),
        5 => word(2, little, Operation::WordDelta),
        6 => word(4, little, Operation::WordDelta),
        7 => word(8, little, Operation::WordDelta),
        8 => word(2, big, Operation::WordDelta),
        9 => word(4, big, Operation::WordDelta),
        10 => word(8, big, Operation::WordDelta),
        11 => word(2, little, Operation::WordDelta2),
        12 => word(4, little, Operation::WordDelta2),
        13 => word(8, little, Operation::WordDelta2),
        14 => word(2, big, Operation::WordDelta2),
        15 => word(4, big, Operation::WordDelta2),
        16 => word(8, big, Operation::WordDelta2),
        17 => word(4, little, Operation::WordXor),
        18 => word(8, little, Operation::WordXor),
        19 => byte(Operation::ByteXor(8)),
        20 => byte(Operation::ByteXor(12)),
        21 => byte(Operation::ByteXor(16)),
        22 => byte(Operation::ByteXor(24)),
        23 => byte(Operation::ByteXor(32)),
        24 => byte(Operation::ByteXor(64)),
        25 => byte(Operation::ByteDelta(2)),
        26 => byte(Operation::ByteDelta(4)),
        27 => byte(Operation::ByteDelta(8)),
        28 => byte(Operation::ByteDelta(16)),
        29 => word(4, little, Operation::WordDelta2Zigzag),
        30 => word(8, little, Operation::WordDelta2Zigzag),
        31 => word(8, big, Operation::WordDelta2Zigzag),
        33 => byte(Operation::MatchXor),
        _ => return None,
    })
}

fn unshuffle(data: &[u8], width: usize) -> Vec<u8> {
    let usable = data.len() / width * width;
    let words = usable / width;
    let mut out = vec![0; data.len()];
    for lane in 0..width {
        for index in 0..words {
            out[index * width + lane] = data[lane * words + index];
        }
    }
    out[usable..].copy_from_slice(&data[usable..]);
    out
}

fn read_word(data: &[u8], big_endian: bool) -> u64 {
    if big_endian {
        data.iter()
            .fold(0, |value, &byte| (value << 8) | byte as u64)
    } else {
        data.iter().enumerate().fold(0, |value, (shift, &byte)| {
            value | ((byte as u64) << (shift * 8))
        })
    }
}

fn write_word(value: u64, width: usize, big_endian: bool, out: &mut Vec<u8>) {
    if big_endian {
        for shift in (0..width).rev() {
            out.push((value >> (shift * 8)) as u8);
        }
    } else {
        for shift in 0..width {
            out.push((value >> (shift * 8)) as u8);
        }
    }
}

fn word_mask(width: usize) -> u64 {
    if width == 8 {
        u64::MAX
    } else {
        (1u64 << (width * 8)) - 1
    }
}

fn unzigzag(value: u64) -> i128 {
    if value & 1 == 0 {
        (value >> 1) as i128
    } else {
        -((value >> 1) as i128) - 1
    }
}

fn signed_mod(value: i128, width: usize) -> i128 {
    let modulus = 1i128 << (width * 8);
    let unsigned = value.rem_euclid(modulus);
    let half = modulus >> 1;
    if unsigned < half {
        unsigned
    } else {
        unsigned - modulus
    }
}

fn add_signed(value: u64, delta: i128, width: usize) -> u64 {
    let modulus = 1i128 << (width * 8);
    ((value as i128 + delta).rem_euclid(modulus)) as u64
}

fn decode_matchxor(residual: &[u8]) -> Vec<u8> {
    const KEY_LEN: usize = 4;
    let mut table: HashMap<[u8; KEY_LEN], usize> = HashMap::new();
    let mut active = None;
    let mut out = Vec::with_capacity(residual.len());

    for (pos, &value) in residual.iter().enumerate() {
        let source = if active.is_some_and(|source| source < pos) {
            active
        } else if pos >= KEY_LEN {
            let key = [out[pos - 4], out[pos - 3], out[pos - 2], out[pos - 1]];
            table.get(&key).copied()
        } else {
            None
        };
        let prediction = source.map(|index| out[index]).unwrap_or(0);
        let byte = value ^ prediction;
        out.push(byte);

        if pos >= KEY_LEN {
            let key = [out[pos - 4], out[pos - 3], out[pos - 2], out[pos - 1]];
            table.insert(key, pos);
        }
        active = source
            .filter(|_| prediction == byte)
            .map(|source| source + 1);
    }
    out
}

fn invert(data: &[u8], spec: Spec) -> Vec<u8> {
    match spec.operation {
        Operation::MatchXor => return decode_matchxor(data),
        Operation::ByteXor(lag) => {
            let mut out = data.to_vec();
            for index in lag..out.len() {
                out[index] ^= out[index - lag];
            }
            return out;
        }
        Operation::ByteDelta(lag) => {
            let mut out = data.to_vec();
            for index in lag..out.len() {
                out[index] = out[index].wrapping_add(out[index - lag]);
            }
            return out;
        }
        _ => {}
    }

    let raw = if spec.shuffled {
        unshuffle(data, spec.width)
    } else {
        data.to_vec()
    };
    let usable = raw.len() / spec.width * spec.width;
    let mut values: Vec<u64> = raw[..usable]
        .chunks_exact(spec.width)
        .map(|word| read_word(word, spec.big_endian))
        .collect();
    if values.len() > 1 {
        let mask = word_mask(spec.width);
        match spec.operation {
            Operation::WordXor => {
                for index in 1..values.len() {
                    values[index] ^= values[index - 1];
                }
            }
            Operation::WordDelta => {
                for index in 1..values.len() {
                    values[index] = values[index - 1].wrapping_add(values[index]) & mask;
                }
            }
            Operation::WordDelta2 => {
                let mut previous_delta = values[1];
                values[1] = values[0].wrapping_add(previous_delta) & mask;
                for index in 2..values.len() {
                    previous_delta = previous_delta.wrapping_add(values[index]) & mask;
                    values[index] = values[index - 1].wrapping_add(previous_delta) & mask;
                }
            }
            Operation::WordDelta2Zigzag => {
                let mut previous_delta = unzigzag(values[1]);
                values[1] = add_signed(values[0], previous_delta, spec.width);
                for index in 2..values.len() {
                    previous_delta =
                        signed_mod(previous_delta + unzigzag(values[index]), spec.width);
                    values[index] = add_signed(values[index - 1], previous_delta, spec.width);
                }
            }
            Operation::ByteXor(_) | Operation::ByteDelta(_) | Operation::MatchXor => {
                unreachable!()
            }
        }
    }

    let mut out = Vec::with_capacity(raw.len());
    for value in values {
        write_word(value, spec.width, spec.big_endian, &mut out);
    }
    out.extend_from_slice(&raw[usable..]);
    out
}

/// Decode one complete mode-5 payload.
pub fn decode(data: &[u8], source_length: usize) -> Result<Vec<u8>, String> {
    if data.len() < 2 || data[0] != 1 {
        return Err("unknown transform block version".into());
    }
    let spec = spec(data[1]).ok_or("unknown transform ID")?;
    let mut pos = 2;
    let transformed = rank::decode_type_class(data, &mut pos, source_length)?;
    if pos != data.len() {
        return Err("unused transform block bytes".into());
    }
    let restored = invert(&transformed, spec);
    if restored.len() != source_length {
        return Err("transform source length mismatch".into());
    }
    Ok(restored)
}
