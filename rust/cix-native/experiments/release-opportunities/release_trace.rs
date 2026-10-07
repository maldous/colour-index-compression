//! RELEASE-PREDICTIVE-TRACE-1: bounded, diagnostic-only causal trace.
//!
//! Build with `CIX_RELEASE_SOURCE` set to a mechanically copied frozen source
//! directory. This file never writes CIX archives and does not alter CIX.

use std::{env, fs, io::Write};

const CAP: usize = 16 * 1024;
mod combinatorics { include!(concat!(env!("CIX_RELEASE_SOURCE"), "/combinatorics.rs")); }
mod rank { include!(concat!(env!("CIX_RELEASE_SOURCE"), "/rank.rs")); }
mod limits { include!(concat!(env!("CIX_RELEASE_SOURCE"), "/limits.rs")); }
mod zpaq_context { include!(concat!(env!("CIX_RELEASE_SOURCE"), "/zpaq_context.rs")); }

mod fixed {
    include!(concat!(env!("CIX_RELEASE_SOURCE"), "/fixedmix.rs"));
    use crate::zpaq_context::Config;
    #[derive(Clone, Copy)]
    pub enum Variant { V1, N1, N2 }
    pub struct Trace { state: State, table: &'static [i32; 4096] }
    impl Trace {
        pub fn new(variant: Variant) -> Result<Self, String> {
            let table = stretch_table();
            let state = match variant {
                Variant::V1 => State::new(6),
                Variant::N1 => State::with_recurrence(6, Config { bucket_bits: 4, max_distance: 1024 }, RecurrenceMode::CorrectV3)?,
                Variant::N2 => State::with_recurrence(6, Config { bucket_bits: 6, max_distance: 16384 }, RecurrenceMode::CorrectV3)?,
            };
            Ok(Self { state, table })
        }
        pub fn probability_then_observe(&mut self, byte: u8) -> f64 {
            let mut probability = 1.0; let mut prefix = 0u8;
            for bit in 0..8 {
                let actual = (byte >> (7 - bit)) & 1;
                let (p, stretches, keys, recurrence) = self.state.probabilities(bit, prefix, self.table);
                probability *= if actual == 1 { p as f64 / 4096.0 } else { (4096 - p) as f64 / 4096.0 };
                self.state.update(bit, actual, p, &stretches, &keys, recurrence);
                prefix = (prefix << 1) | actual;
            }
            self.state.finish_byte(byte); probability
        }
    }
}

mod ppm {
    include!(concat!(env!("CIX_RELEASE_SOURCE"), "/ppm.rs"));
    pub struct Trace { tables: Tables, history: Vec<u8> }
    impl Trace {
        pub fn new(block_length: usize) -> Result<Self, String> {
            let (tables, history) = prime(&[], block_length, 3, false)?; Ok(Self { tables, history })
        }
        fn probability(&self, symbol: u8) -> Result<f64, String> {
            let mut result = 1.0; let mut excluded = [false; 256];
            for order in (0..=3.min(self.history.len())).rev() {
                let Some(counts) = self.tables.get(context(&self.history, order)) else { continue; };
                let Some(symbols) = fixed_eligible(counts, &excluded, symbol) else { continue; };
                let escape = fixed_escape_mass(&symbols, 1)?; let total = (symbols.mass + escape) as f64;
                if let Some((_low, count)) = symbols.hit { return Ok(result * count as f64 / total); }
                result *= escape as f64 / total; exclude_eligible(counts, &mut excluded);
            }
            let (_rank, remaining) = fallback_rank(symbol, &excluded)?;
            Ok(result / remaining as f64)
        }
        pub fn probability_then_observe(&mut self, symbol: u8) -> Result<(f64, f64), String> {
            let actual = self.probability(symbol)?;
            let valid_mass = self.valid_mass()?;
            observe_from(&mut self.tables, &mut self.history, symbol, 3, 0);
            Ok((actual, valid_mass))
        }
        pub fn valid_mass(&self) -> Result<f64, String> {
            (0..=u8::MAX).try_fold(0.0, |sum, value| Ok::<_, String>(sum + self.probability(value)?))
        }
    }
}

fn fixed_distribution(variant: fixed::Variant, history: &[u8]) -> Result<[f64; 256], String> {
    let mut distribution = [0.0; 256];
    for candidate in 0..=u8::MAX {
        let mut replay = fixed::Trace::new(variant_for(variant))?;
        for &byte in history { replay.probability_then_observe(byte); }
        distribution[candidate as usize] = replay.probability_then_observe(candidate);
    }
    Ok(distribution)
}
fn variant_for(variant: fixed::Variant) -> fixed::Variant {
    match variant { fixed::Variant::V1 => fixed::Variant::V1, fixed::Variant::N1 => fixed::Variant::N1, fixed::Variant::N2 => fixed::Variant::N2 }
}
fn signature(history: &[u8]) -> Result<Vec<[f64; 3]>, String> {
    let mut v1 = fixed::Trace::new(fixed::Variant::V1)?; let mut n1 = fixed::Trace::new(fixed::Variant::N1)?; let mut n2 = fixed::Trace::new(fixed::Variant::N2)?;
    let mut out = Vec::new();
    for &byte in history { out.push([v1.probability_then_observe(byte), n1.probability_then_observe(byte), n2.probability_then_observe(byte)]); }
    Ok(out)
}
fn toy_controls() -> Result<(), String> {
    let a = [0.9f64, 0.9, 0.1, 0.1]; let b = [0.1f64, 0.1, 0.9, 0.9];
    let loss = |values: &[f64; 4]| values.iter().map(|p| -p.log2()).sum::<f64>();
    let best = loss(&a).min(loss(&b)); let oracle = a.iter().zip(b.iter()).map(|(x, y)| -x.max(*y).log2()).sum::<f64>();
    let static_equal = 4.0; // each mixture probability is (0.9 + 0.1)/2.
    let switch_raw = -4.0 * 0.9f64.log2();
    if !(oracle <= switch_raw && switch_raw < best && static_equal < best) { return Err("complementary toy static/switch loss invariant failed".into()); }
    let mut weights = [0.5f64, 0.5]; let mut online = 0.0;
    for index in 0..4 { let mixture = weights[0] * a[index] + weights[1] * b[index]; online -= mixture.log2(); let normalizer = mixture; weights[0] *= a[index] / normalizer; weights[1] *= b[index] / normalizer; }
    if !(online.is_finite() && online >= oracle) { return Err("complementary toy online loss invariant failed".into()); }
    Ok(())
}
fn selfcheck() -> Result<(), String> {
    for variant in [fixed::Variant::V1, fixed::Variant::N1, fixed::Variant::N2] {
        for history in [b"".as_slice(), b"aaaaaaaa".as_slice(), b"abcdabcd".as_slice()] {
            let distribution = fixed_distribution(variant_for(variant), history)?; let sum: f64 = distribution.iter().sum();
            if !(distribution.iter().all(|p| *p > 0.0) && (sum - 1.0).abs() < 2e-12) { return Err("fixedmix byte distribution is not positive and normalized".into()); }
        }
    }
    let prefix = b"causal release trace"; let mut extended = prefix.to_vec(); extended.extend_from_slice(b"unread suffix");
    if signature(prefix)? != signature(&extended)?[..prefix.len()] { return Err("fixedmix prefix causality failed".into()); }
    let mut ppm_trace = ppm::Trace::new(257)?; for byte in 0..=u8::MAX { ppm_trace.probability_then_observe(byte)?; }
    let mass = ppm_trace.valid_mass()?;
    if (mass - 0.5).abs() > 2e-12 { return Err(format!("PPM full-alphabet mass is not the expected native 0.5: {mass:.17e}")); }
    toy_controls()?;
    println!("{{\"release_predictive_trace\":\"selfcheck_passed\",\"ppm_full_alphabet_valid_mass\":\"{mass:.17e}\"}}"); Ok(())
}

fn main() -> Result<(), String> {
    let mut args = env::args().skip(1); let input = args.next().ok_or("usage: release_trace INPUT OUTPUT.tsv | release_trace selfcheck")?;
    if input == "selfcheck" && args.next().is_none() { return selfcheck(); }
    let output = args.next().ok_or("usage: release_trace INPUT OUTPUT.tsv | release_trace selfcheck")?;
    if args.next().is_some() { return Err("usage: release_trace INPUT OUTPUT.tsv".into()); }
    let data = fs::read(input).map_err(|error| format!("read input: {error}"))?;
    if data.len() > CAP { return Err(format!("input exceeds {CAP}-byte cap")); }
    let mut v1 = fixed::Trace::new(fixed::Variant::V1)?; let mut n1 = fixed::Trace::new(fixed::Variant::N1)?; let mut n2 = fixed::Trace::new(fixed::Variant::N2)?; let mut ppm = ppm::Trace::new(data.len())?;
    let mut out = fs::File::create(output).map_err(|error| format!("create trace: {error}"))?;
    writeln!(out, "position\tactual\tfixedmix_v1__p_actual\tfixedmix_v3_n1__p_actual\tfixedmix_v3_n2__p_actual\tppm_o3_e1_native_subprob__p_actual\tppm_o3_e1_native_subprob__valid_byte_mass\tppm_o3_e1_validmass_normalized_diagnostic__p_actual").map_err(|error| error.to_string())?;
    for (position, &byte) in data.iter().enumerate() {
        let p1 = v1.probability_then_observe(byte); let pn1 = n1.probability_then_observe(byte); let pn2 = n2.probability_then_observe(byte); let (pp, mass) = ppm.probability_then_observe(byte)?;
        writeln!(out, "{position}\t{byte}\t{p1:.17e}\t{pn1:.17e}\t{pn2:.17e}\t{pp:.17e}\t{mass:.17e}\t{:.17e}", pp / mass).map_err(|error| error.to_string())?;
    }
    Ok(())
}
