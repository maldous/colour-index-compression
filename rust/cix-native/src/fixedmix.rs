//! Deterministic fixed-point three-family bit mixer for CIXG1 route 9.
use crate::rank::{ArithmeticDecoder, ArithmeticEncoder};
use std::collections::HashMap;

const SCALE: i64 = 4096;
const LOG_SCALE: i64 = 4096;
const WEIGHT_SCALE: i64 = 1024;
const CLIP_LOG: i64 = 12 * LOG_SCALE;
const COUNT_LIMIT: i32 = 2048;
const HISTORY_MAX: usize = 65536;
const ETA: [u8; 3] = [5, 6, 7];
const PATTERNS: &[&[usize]] = &[
    &[],
    &[1],
    &[1, 2],
    &[1, 2, 3],
    &[1, 2, 3, 4],
    &[1, 3],
    &[1, 4],
    &[1, 5],
    &[2, 3],
    &[2, 4],
    &[3, 6],
    &[4, 8],
    &[1, 4, 8],
];
const LAGS: &[usize] = &[1, 2, 4, 8, 16, 32];
const EXPERTS: usize = 20;

fn floor_div(a: i64, b: i64) -> i64 {
    let q = a / b;
    let r = a % b;
    if r != 0 && ((r < 0) != (b < 0)) {
        q - 1
    } else {
        q
    }
}
fn fixed_log2(value: u32) -> i32 {
    assert!(value > 0);
    let integer = 31 - value.leading_zeros();
    let one = 1u128 << 32;
    let mut y = ((value as u128) << 32) >> integer;
    let mut fraction = 0u32;
    for i in 0..12 {
        y = (y * y) >> 32;
        if y >= 2 * one {
            y >>= 1;
            fraction |= 1 << (11 - i);
        }
    }
    (integer * 4096 + fraction) as i32
}
fn stretch_table() -> Vec<i32> {
    let mut a = vec![0; 4096];
    for p in 1..4096 {
        a[p] = fixed_log2(p as u32) - fixed_log2((4096 - p) as u32);
    }
    a
}
fn squash(v: i64, t: &[i32]) -> i32 {
    if v <= t[1] as i64 {
        return 1;
    }
    if v >= t[4095] as i64 {
        return 4095;
    }
    let mut lo = 1usize;
    let mut hi = 4095;
    while lo < hi {
        let mid = (lo + hi) / 2;
        if t[mid] as i64 >= v {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    if (t[lo] as i64 - v).abs() < (v - t[lo - 1] as i64).abs() {
        lo as i32
    } else {
        (lo - 1) as i32
    }
}
type CtxKey = u64;
struct State {
    history: Vec<u8>,
    tables: Vec<HashMap<CtxKey, [i32; 2]>>,
    weights: Vec<[i32; EXPERTS]>,
    bias: [i32; 8],
    eta: u8,
    lag_rel: Vec<[[i32; 2]; 8]>,
    match_rel: [[i32; 2]; 8],
    matches: HashMap<[u8; 4], u8>,
}
impl State {
    fn new(eta: u8) -> Self {
        let initial = (WEIGHT_SCALE as i32 / EXPERTS as i32).max(1);
        Self {
            history: Vec::new(),
            tables: (0..PATTERNS.len()).map(|_| HashMap::new()).collect(),
            weights: vec![[initial; EXPERTS]; 8],
            bias: [0; 8],
            eta,
            lag_rel: vec![[[1, 1]; 8]; LAGS.len()],
            match_rel: [[1, 1]; 8],
            matches: HashMap::new(),
        }
    }
    fn context(&self, p: &[usize], bit: usize, prefix: u8) -> Option<CtxKey> {
        if p.iter().any(|&o| self.history.len() < o) {
            return None;
        }
        let mut key = 0u64;
        for &o in p {
            key = (key << 8) | self.history[self.history.len() - o] as u64;
        }
        key = (key << 16) | ((bit as u64) << 8) | prefix as u64;
        Some(key)
    }
    fn context_prob(counts: Option<&[i32; 2]>) -> i32 {
        if let Some(c) = counts {
            (((2 * c[1] + 1) * 4096) / (2 * (c[0] + c[1] + 1))).clamp(1, 4095)
        } else {
            2048
        }
    }
    fn rel_prob(pred: Option<u8>, rel: &[i32; 2], bit: usize) -> i32 {
        if let Some(p) = pred {
            let conf = (((2 * rel[0] + 1) * 4096) / (2 * (rel[0] + rel[1] + 1))).clamp(2048, 4095);
            if ((p >> (7 - bit)) & 1) != 0 {
                conf
            } else {
                4096 - conf
            }
        } else {
            2048
        }
    }
    fn predictions(&self) -> (Vec<Option<u8>>, Option<[u8; 4]>) {
        let lags = LAGS
            .iter()
            .map(|&n| {
                if self.history.len() >= n {
                    Some(self.history[self.history.len() - n])
                } else {
                    None
                }
            })
            .collect();
        let key = if self.history.len() >= 4 {
            Some(std::array::from_fn(|i| {
                self.history[self.history.len() - 4 + i]
            }))
        } else {
            None
        };
        (lags, key)
    }
    fn probabilities(
        &self,
        bit: usize,
        prefix: u8,
        t: &[i32],
    ) -> (i32, Vec<i32>, Vec<Option<CtxKey>>) {
        let mut ps = Vec::with_capacity(EXPERTS);
        let mut keys = Vec::with_capacity(PATTERNS.len());
        for (i, p) in PATTERNS.iter().enumerate() {
            let k = self.context(p, bit, prefix);
            let cnt = k.as_ref().and_then(|x| self.tables[i].get(x));
            ps.push(Self::context_prob(cnt));
            keys.push(k);
        }
        let (lags, match_key) = self.predictions();
        for (i, p) in lags.iter().enumerate() {
            ps.push(Self::rel_prob(*p, &self.lag_rel[i][bit], bit));
        }
        let mp = match_key.and_then(|k| self.matches.get(&k).copied());
        ps.push(Self::rel_prob(mp, &self.match_rel[bit], bit));
        let stretches: Vec<i32> = ps.iter().map(|&p| t[p as usize]).collect();
        let sum: i64 = self.weights[bit]
            .iter()
            .zip(&stretches)
            .map(|(&w, &s)| w as i64 * s as i64)
            .sum();
        let mixed = self.bias[bit] as i64 + floor_div(sum, WEIGHT_SCALE);
        (squash(mixed, t), stretches, keys)
    }
    fn update(
        &mut self,
        bit: usize,
        actual: u8,
        p: i32,
        stretches: &[i32],
        keys: &[Option<CtxKey>],
    ) {
        let error = if actual != 0 {
            SCALE - p as i64
        } else {
            -(p as i64)
        };
        let bd = floor_div(error * LOG_SCALE, SCALE * (1i64 << self.eta));
        self.bias[bit] = (self.bias[bit] as i64 + bd).clamp(-CLIP_LOG, CLIP_LOG) as i32;
        let denom = SCALE * LOG_SCALE * (1i64 << self.eta);
        for (i, &s) in stretches.iter().enumerate() {
            let d = floor_div(error * s as i64 * WEIGHT_SCALE, denom);
            self.weights[bit][i] =
                (self.weights[bit][i] as i64 + d).clamp(-4 * WEIGHT_SCALE, 4 * WEIGHT_SCALE) as i32;
        }
        for (i, key) in keys.iter().enumerate() {
            if let Some(k) = key {
                let c = self.tables[i].entry(*k).or_insert([0, 0]);
                c[actual as usize] += 1;
                if c[0] + c[1] > COUNT_LIMIT {
                    c[0] = (c[0] + 1) / 2;
                    c[1] = (c[1] + 1) / 2;
                }
            }
        }
        for (i, &lag) in LAGS.iter().enumerate() {
            if self.history.len() >= lag {
                let pred = (self.history[self.history.len() - lag] >> (7 - bit)) & 1;
                let r = &mut self.lag_rel[i][bit];
                r[if pred == actual { 0 } else { 1 }] += 1;
                if r[0] + r[1] > COUNT_LIMIT {
                    r[0] = (r[0] + 1) / 2;
                    r[1] = (r[1] + 1) / 2;
                }
            }
        }
        if self.history.len() >= 4 {
            let k: [u8; 4] = std::array::from_fn(|i| self.history[self.history.len() - 4 + i]);
            if let Some(&v) = self.matches.get(&k) {
                let pred = (v >> (7 - bit)) & 1;
                let r = &mut self.match_rel[bit];
                r[if pred == actual { 0 } else { 1 }] += 1;
                if r[0] + r[1] > COUNT_LIMIT {
                    r[0] = (r[0] + 1) / 2;
                    r[1] = (r[1] + 1) / 2;
                }
            }
        }
    }
    fn finish_byte(&mut self, b: u8) {
        if self.history.len() >= 4 {
            let k: [u8; 4] = std::array::from_fn(|i| self.history[self.history.len() - 4 + i]);
            self.matches.insert(k, b);
        }
        self.history.push(b);
        if self.history.len() > HISTORY_MAX {
            self.history.remove(0);
        }
    }
}
fn encode_eta(data: &[u8], eta: u8, t: &[i32]) -> (Vec<u8>, usize) {
    let mut state = State::new(eta);
    let mut coder = ArithmeticEncoder::new();
    for &b in data {
        let mut prefix = 0;
        for bit in 0..8 {
            let actual = (b >> (7 - bit)) & 1;
            let (p, s, k) = state.probabilities(bit, prefix, t);
            let zero = 4096 - p as usize;
            if actual == 1 {
                coder.encode(zero, 4096, 4096)
            } else {
                coder.encode(0, zero, 4096)
            }
            state.update(bit, actual, p, &s, &k);
            prefix = (prefix << 1) | actual;
        }
        state.finish_byte(b);
    }
    coder.finish()
}
fn put_v(mut x: usize, o: &mut Vec<u8>) {
    while x >= 128 {
        o.push((x as u8 & 127) | 128);
        x >>= 7;
    }
    o.push(x as u8);
}
fn get_v(b: &[u8], p: &mut usize) -> Result<usize, String> {
    let mut x = 0usize;
    for s in (0..usize::BITS as usize).step_by(7) {
        let v = *b.get(*p).ok_or("truncated fixed-mix length")?;
        *p += 1;
        x |= ((v & 127) as usize)
            .checked_shl(s as u32)
            .ok_or("fixed-mix length overflow")?;
        if v < 128 {
            return Ok(x);
        }
    }
    Err("oversized fixed-mix length".into())
}
pub fn encode(data: &[u8]) -> Vec<u8> {
    let t = stretch_table();
    let mut best = None;
    for (id, &eta) in ETA.iter().enumerate() {
        let (payload, bits) = encode_eta(data, eta, &t);
        let mut out = vec![1, id as u8];
        put_v(bits, &mut out);
        out.extend(payload);
        if best.as_ref().is_none_or(|x: &Vec<u8>| out.len() < x.len()) {
            best = Some(out)
        }
    }
    best.unwrap()
}
pub fn decode(blob: &[u8], n: usize) -> Result<Vec<u8>, String> {
    decode_with_history(blob, n, &[])
}
pub fn decode_with_history(
    blob: &[u8],
    n: usize,
    prefix_history: &[u8],
) -> Result<Vec<u8>, String> {
    if blob.len() < 3 || blob[0] != 1 || blob[1] > 2 {
        return Err("invalid fixed-mix version or learning rate".into());
    }
    let mut p = 2;
    let bits = get_v(blob, &mut p)?;
    if p.checked_add(bits.div_ceil(8)) != Some(blob.len()) {
        return Err("fixed-mix payload length mismatch".into());
    }
    let eta = ETA[blob[1] as usize];
    let t = stretch_table();
    let mut state = State::new(eta);
    let training = prefix_history
        .len()
        .min(HISTORY_MAX)
        .min(4096usize.max(n.saturating_mul(2)));
    for &byte in &prefix_history[prefix_history.len() - training..] {
        let mut prefix = 0u8;
        for bit in 0..8 {
            let (prob, s, k) = state.probabilities(bit, prefix, &t);
            let actual = ((byte >> (7 - bit)) & 1) as u8;
            state.update(bit, actual, prob, &s, &k);
            prefix = (prefix << 1) | actual;
        }
        state.finish_byte(byte);
    }
    let mut coder = ArithmeticDecoder::new(&blob[p..], bits);
    let mut out = Vec::with_capacity(n);
    for _ in 0..n {
        let mut byte = 0u8;
        let mut prefix = 0u8;
        for bit in 0..8 {
            let (prob, s, k) = state.probabilities(bit, prefix, &t);
            let zero = 4096 - prob as usize;
            let target = coder.target(4096);
            let actual = if target < zero {
                coder.update(0, zero, 4096);
                0
            } else {
                coder.update(zero, 4096, 4096);
                1
            };
            state.update(bit, actual as u8, prob, &s, &k);
            byte = (byte << 1) | actual as u8;
            prefix = (prefix << 1) | actual as u8;
        }
        out.push(byte);
        state.finish_byte(byte);
    }
    Ok(out)
}
