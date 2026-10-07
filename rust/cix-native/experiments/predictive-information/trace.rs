//! PREDICTIVE-INFORMATION-TRACE-1: isolated causal-probability audit.
//!
//! Build this file against a source snapshot made from production revision
//! d3a2cd416.  It deliberately includes that snapshot rather than linking the
//! working tree, and emits ideal-probability diagnostics only; it is not an
//! archive format or a production route.

use std::{
    env,
    fs,
    io::Write,
    time::{Instant},
};

const MAX_INPUT: usize = 16 * 1024;
const EXPERT_MIX_ORDERS: [u8; 4] = [0, 1, 2, 4];
const FIXED_COMPONENTS: usize = 20;
const EXPERT_NAMES: [&str; 28] = [
    "adaptive_o0", "adaptive_o1",
    "context_o0", "context_o1", "context_o2", "context_o4", "context_selected",
    "fixed_pattern_empty", "fixed_pattern_1", "fixed_pattern_1_2", "fixed_pattern_1_2_3",
    "fixed_pattern_1_2_3_4", "fixed_pattern_1_3", "fixed_pattern_1_4", "fixed_pattern_1_5",
    "fixed_pattern_2_3", "fixed_pattern_2_4", "fixed_pattern_3_6", "fixed_pattern_4_8",
    "fixed_pattern_1_4_8", "fixed_lag_1", "fixed_lag_2", "fixed_lag_4", "fixed_lag_8",
    "fixed_lag_16", "fixed_lag_32", "fixed_match4", "fixed_mixer_eta6",
];

// `CIX_TRACE_SOURCE` must point to the immutable copy produced from
// d3a2cd416. `include!` makes all wrappers below inspect the exact native
// implementation while keeping wrapper-only visibility inside this file.
mod combinatorics { include!(concat!(env!("CIX_TRACE_SOURCE"), "/combinatorics.rs")); }
mod rank { include!(concat!(env!("CIX_TRACE_SOURCE"), "/rank.rs")); }
mod limits { include!(concat!(env!("CIX_TRACE_SOURCE"), "/limits.rs")); }
mod zpaq_context { include!(concat!(env!("CIX_TRACE_SOURCE"), "/zpaq_context.rs")); }
// Included for source binding and the documented exclusion below. Its native
// fixed-escape path can retain an escape mass after every byte is excluded,
// so it is intentionally not coerced into the normalized-expert table.
mod ppm_native {
    include!(concat!(env!("CIX_TRACE_SOURCE"), "/ppm.rs"));
    pub fn full_alphabet_direct_byte_mass() -> Result<f64, String> {
        let mut tables = Tables::new(); let mut history = Vec::new();
        for symbol in 0..=u8::MAX { observe(&mut tables, &mut history, symbol, 0); }
        let excluded = [false; 256];
        let counts = tables.get(&Vec::new()).ok_or("missing PPM order-0 table")?;
        let eligible = fixed_eligible(counts, &excluded, 0).ok_or("missing PPM eligible symbols")?;
        let escape = fixed_escape_mass(&eligible, 1)?;
        Ok(eligible.mass as f64 / (eligible.mass + escape) as f64)
    }
}

mod adaptive_native {
    include!(concat!(env!("CIX_TRACE_SOURCE"), "/adaptive.rs"));
    use std::collections::HashMap;

    pub struct Trace {
        order: usize,
        tail: Vec<u8>,
        models: HashMap<usize, Model>,
    }
    impl Trace {
        pub fn new(order: usize) -> Self { Self { order, tail: Vec::new(), models: HashMap::new() } }
        fn current(&self) -> Option<&Model> {
            let bucket = bucket(&self.tail, self.order, 8);
            self.models.get(&bucket)
        }
        pub fn distribution(&self) -> [f64; 256] {
            let mut out = [0.0; 256];
            if let Some(model) = self.current() {
                for (symbol, slot) in out.iter_mut().enumerate() {
                    let (low, high, total) = model.interval(symbol);
                    *slot = (high - low) as f64 / total as f64;
                }
            } else { out.fill(1.0 / 256.0); }
            out
        }
        pub fn actual_interval_probability(&self, byte: u8) -> f64 {
            let model = self.current();
            model.map_or(1.0 / 256.0, |model| { let (low, high, total) = model.interval(byte as usize); (high - low) as f64 / total as f64 })
        }
        pub fn observe(&mut self, byte: u8) {
            let bucket_id = bucket(&self.tail, self.order, 8);
            self.models.entry(bucket_id).or_insert_with(Model::new).add(byte as usize);
            extend_tail(&mut self.tail, byte, self.order);
        }
        pub fn state_bytes(&self) -> usize { self.models.len() * (256 * 4 + 257 * 4) + self.tail.capacity() }
    }
}

mod expertmix_native {
    include!(concat!(env!("CIX_TRACE_SOURCE"), "/expertmix.rs"));

    pub struct Trace {
        orders: Vec<u8>, history: Vec<u8>, tables: Vec<Table>, losses: Vec<f64>, contexts: Vec<Vec<u8>>,
        context_count: usize,
    }
    impl Trace {
        pub fn new() -> Self {
            let orders = super::EXPERT_MIX_ORDERS.to_vec();
            Self { tables: (0..orders.len()).map(|_| HashMap::new()).collect(), losses: vec![0.0; orders.len()],
                   history: Vec::new(), contexts: Vec::new(), context_count: 0, orders }
        }
        fn contexts(&mut self) { populate_contexts(&mut self.contexts, &self.history, &self.orders); }
        pub fn selected_order(&mut self) -> u8 { self.contexts(); self.orders[best_expert(&self.losses)] }
        pub fn distributions(&mut self) -> [[f64; 256]; 5] {
            self.contexts();
            let selected = best_expert(&self.losses);
            let mut out = [[0.0; 256]; 5];
            for symbol in 0..256 {
                for expert in 0..self.orders.len() {
                    let (low, high, total) = interval(self.tables[expert].get(&self.contexts[expert]), symbol as u8);
                    out[expert][symbol] = (high - low) as f64 / total as f64;
                }
                out[4][symbol] = out[selected][symbol];
            }
            out
        }
        pub fn selected_interval_probability(&mut self, byte: u8) -> f64 {
            self.contexts(); let selected = best_expert(&self.losses);
            let (low, high, total) = interval(self.tables[selected].get(&self.contexts[selected]), byte);
            (high - low) as f64 / total as f64
        }
        pub fn observe(&mut self, byte: u8) {
            self.contexts();
            update_experts(&mut self.tables, &mut self.losses, &self.contexts, byte, &mut self.context_count, usize::MAX)
                .expect("unbounded trace context update");
            push_history(&mut self.history, byte, *self.orders.last().unwrap() as usize);
        }
        pub fn state_bytes(&self) -> usize { self.context_count * 96 + self.history.capacity() + self.losses.len() * 8 }
    }
}

mod fixedmix_native {
    include!(concat!(env!("CIX_TRACE_SOURCE"), "/fixedmix.rs"));

    pub struct Trace { state: State, table: &'static [i32; 4096] }
    impl Trace {
        pub fn new(block_length: usize) -> Self {
            let table = stretch_table();
            Self { state: prime_unchecked(&[], block_length, 6, table), table }
        }
        fn component_probs(&self, bit: usize, prefix: u8) -> [i32; EXPERTS] {
            let mut probabilities = [0; EXPERTS];
            for (index, pattern) in PATTERNS.iter().enumerate() {
                let key = self.state.context(pattern, bit, prefix);
                probabilities[index] = State::context_prob(key.as_ref().and_then(|value| self.state.tables[index].get(value)));
            }
            let (lags, match_key) = self.state.predictions();
            for (index, prediction) in lags.iter().enumerate() {
                probabilities[PATTERN_EXPERTS + index] = State::rel_prob(*prediction, &self.state.lag_rel[index][bit], bit);
            }
            let match_prediction = match_key.and_then(|key| self.state.matches.get(&key).copied());
            probabilities[EXPERTS - 1] = State::rel_prob(match_prediction, &self.state.match_rel[bit], bit);
            probabilities
        }
        // Enumerate the 255 non-root prefix-tree nodes once. Bit-specific
        // state is only updated after the byte, matching the native encoder.
        pub fn distributions(&self) -> [[f64; 256]; super::FIXED_COMPONENTS + 1] {
            let mut out = [[0.0; 256]; super::FIXED_COMPONENTS + 1];
            let mut nodes: Vec<(u8, [f64; super::FIXED_COMPONENTS + 1])> = vec![(0, [1.0; super::FIXED_COMPONENTS + 1])];
            for bit in 0..8 {
                let mut next = Vec::with_capacity(nodes.len() * 2);
                for (prefix, prior) in nodes {
                    let components = self.component_probs(bit, prefix);
                    let (mixed, _, _, _) = self.state.probabilities(bit, prefix, self.table);
                    for actual in 0..=1u8 {
                        let mut probability = prior;
                        for index in 0..super::FIXED_COMPONENTS {
                            let one = components[index] as f64 / 4096.0;
                            probability[index] *= if actual == 1 { one } else { 1.0 - one };
                        }
                        let one = mixed as f64 / 4096.0;
                        probability[super::FIXED_COMPONENTS] *= if actual == 1 { one } else { 1.0 - one };
                        next.push(((prefix << 1) | actual, probability));
                    }
                }
                nodes = next;
            }
            for (byte, probability) in nodes { for index in 0..=super::FIXED_COMPONENTS { out[index][byte as usize] = probability[index]; } }
            out
        }
        pub fn match_available(&self) -> bool {
            self.state.history.len() >= 4 && self.state.matches.contains_key(&std::array::from_fn(|index| self.state.history.get(self.state.history.len() - 4 + index)))
        }
        pub fn observe(&mut self, byte: u8) { observe_byte(&mut self.state, byte, self.table); }
        pub fn sequential_actual_probability(&mut self, byte: u8) -> f64 {
            let mut probability = 1.0; let mut prefix = 0;
            for bit in 0..8 {
                let actual = (byte >> (7 - bit)) & 1;
                let (p, stretches, keys, recurrence) = self.state.probabilities(bit, prefix, self.table);
                probability *= if actual == 1 { p as f64 / 4096.0 } else { (4096 - p) as f64 / 4096.0 };
                self.state.update(bit, actual, p, &stretches, &keys, recurrence); prefix = (prefix << 1) | actual;
            }
            probability
        }
        pub fn state_bytes(&self) -> usize { self.state.history.bytes.capacity() + self.state.tables.iter().map(|table| table.len() * 48).sum::<usize>() + self.state.matches.len() * 24 }
    }
}

#[derive(Clone, Copy)]
struct Metrics { p_actual: f64, entropy: f64, maximum: f64, top: usize }
fn metrics(distribution: &[f64; 256], actual: u8) -> Result<Metrics, String> {
    let sum: f64 = distribution.iter().sum();
    if !(sum.is_finite() && (sum - 1.0).abs() < 2e-12) { return Err(format!("non-normalized distribution: {sum:.17}")); }
    let mut entropy = 0.0; let mut maximum = -1.0; let mut top = 0;
    for (symbol, &probability) in distribution.iter().enumerate() {
        if probability <= 0.0 || !probability.is_finite() { return Err("zero or non-finite byte probability".into()); }
        entropy -= probability * probability.log2();
        if probability > maximum { maximum = probability; top = symbol; }
    }
    Ok(Metrics { p_actual: distribution[actual as usize], entropy, maximum, top })
}
fn header() -> String {
    let mut fields = vec!["position".to_owned(), "actual".to_owned(), "run_length".to_owned(), "match_available".to_owned(), "context_selected_order".to_owned()];
    for name in EXPERT_NAMES {
        fields.extend([format!("{name}__p_actual"), format!("{name}__entropy_bits"), format!("{name}__max_probability"), format!("{name}__top_symbol")]);
        for replicate in 0..4 { fields.push(format!("{name}__noise{replicate}")); }
    }
    fields.join("\t")
}
fn noise_sign(position: usize, expert: usize, replicate: usize, symbol: usize) -> f64 {
    let mut value = (position as u64).wrapping_mul(0x9e37_79b9_7f4a_7c15)
        ^ (expert as u64).wrapping_mul(0xbf58_476d_1ce4_e5b9)
        ^ (replicate as u64 + 20_261_004).wrapping_mul(0x94d0_49bb_1331_11eb)
        ^ symbol as u64;
    value ^= value >> 30; value = value.wrapping_mul(0xbf58_476d_1ce4_e5b9);
    value ^= value >> 27; value = value.wrapping_mul(0x94d0_49bb_1331_11eb);
    value ^= value >> 31;
    if value & 1 == 0 { -1.0 } else { 1.0 }
}
fn noisy_actual(distribution: &[f64; 256], position: usize, expert: usize, replicate: usize, actual: u8) -> f64 {
    const EPSILON: f64 = 0.25;
    let mut normalizer = 0.0;
    for (symbol, &probability) in distribution.iter().enumerate() { normalizer += probability * (EPSILON * noise_sign(position, expert, replicate, symbol)).exp(); }
    distribution[actual as usize] * (EPSILON * noise_sign(position, expert, replicate, actual as usize)).exp() / normalizer
}
fn line(position: usize, actual: u8, run: usize, matching: bool, selected: u8, values: &[Metrics; 28], noisy: &[[f64; 4]; 28]) -> String {
    let mut fields = vec![position.to_string(), actual.to_string(), run.to_string(), u8::from(matching).to_string(), selected.to_string()];
    for (index, metric) in values.iter().enumerate() {
        fields.extend([format!("{:.17e}", metric.p_actual), format!("{:.17e}", metric.entropy), format!("{:.17e}", metric.maximum), metric.top.to_string()]);
        fields.extend(noisy[index].iter().map(|value| format!("{value:.17e}")));
    }
    fields.join("\t")
}
fn causal_signature(data: &[u8]) -> Result<Vec<[f64; 28]>, String> {
    let mut adaptive0 = adaptive_native::Trace::new(0); let mut adaptive1 = adaptive_native::Trace::new(1);
    let mut context = expertmix_native::Trace::new(); let mut fixed = fixedmix_native::Trace::new(data.len());
    let mut result = Vec::with_capacity(data.len());
    for &actual in data {
        let adaptive0_distribution = adaptive0.distribution(); let adaptive1_distribution = adaptive1.distribution();
        let context_distributions = context.distributions(); let fixed_distributions = fixed.distributions();
        let distributions: [&[f64; 256]; 28] = [
            &adaptive0_distribution, &adaptive1_distribution, &context_distributions[0], &context_distributions[1], &context_distributions[2], &context_distributions[3], &context_distributions[4],
            &fixed_distributions[0], &fixed_distributions[1], &fixed_distributions[2], &fixed_distributions[3], &fixed_distributions[4], &fixed_distributions[5], &fixed_distributions[6], &fixed_distributions[7], &fixed_distributions[8], &fixed_distributions[9], &fixed_distributions[10], &fixed_distributions[11], &fixed_distributions[12], &fixed_distributions[13], &fixed_distributions[14], &fixed_distributions[15], &fixed_distributions[16], &fixed_distributions[17], &fixed_distributions[18], &fixed_distributions[19], &fixed_distributions[20],
        ];
        let mut row = [0.0; 28];
        for index in 0..28 { row[index] = metrics(distributions[index], actual)?.p_actual; }
        result.push(row);
        adaptive0.observe(actual); adaptive1.observe(actual); context.observe(actual); fixed.observe(actual);
    }
    Ok(result)
}
fn fixed_distribution_fidelity(history: &[u8]) -> Result<(), String> {
    let mut traced = fixedmix_native::Trace::new(history.len() + 256);
    for &byte in history { traced.observe(byte); }
    let distribution = traced.distributions();
    for candidate in 0..=u8::MAX {
        let mut sequential = fixedmix_native::Trace::new(history.len() + 256);
        for &byte in history { sequential.observe(byte); }
        let native = sequential.sequential_actual_probability(candidate);
        if (native - distribution[FIXED_COMPONENTS][candidate as usize]).abs() > 2e-15 {
            return Err(format!("fixed mixer prefix-tree probability differs from sequential native interval for {candidate}"));
        }
    }
    Ok(())
}
fn interval_fidelity(history: &[u8]) -> Result<(), String> {
    let mut adaptive = adaptive_native::Trace::new(1); let mut context = expertmix_native::Trace::new();
    for &byte in history { adaptive.observe(byte); context.observe(byte); }
    let adaptive_distribution = adaptive.distribution(); let context_distribution = context.distributions();
    for candidate in 0..=u8::MAX {
        if (adaptive.actual_interval_probability(candidate) - adaptive_distribution[candidate as usize]).abs() > 2e-15 { return Err("adaptive interval extraction differs from byte distribution".into()); }
        if (context.selected_interval_probability(candidate) - context_distribution[4][candidate as usize]).abs() > 2e-15 { return Err("selected context interval differs from byte distribution".into()); }
    }
    Ok(())
}
fn selfcheck() -> Result<(), String> {
    let prefix = b"causal prediction audit\x00\xff\x00\xff";
    let mut extended = prefix.to_vec(); extended.extend_from_slice(b"future bytes must not alter a prefix");
    let prefix_signature = causal_signature(prefix)?; let extended_signature = causal_signature(&extended)?;
    if prefix_signature != extended_signature[..prefix.len()] { return Err("causal suffix invariance failed".into()); }
    let source = b"fixed frozen codec fidelity fixture: \x00\x01\x02 repeated repeated";
    for history in [b"".as_slice(), b"aaaaaaaaaaaa".as_slice(), b"abcdabcdabcdabcd".as_slice(), source.as_slice()] {
        fixed_distribution_fidelity(history)?; interval_fidelity(history)?;
    }
    let ppm_mass = ppm_native::full_alphabet_direct_byte_mass()?;
    if (ppm_mass - 0.5).abs() > 2e-15 { return Err(format!("unexpected PPM full-alphabet direct byte mass {ppm_mass:.17e}")); }
    let adaptive = adaptive_native::encode_general(source, 0, 8, &[], 1)?;
    if adaptive_native::decode(&adaptive, source.len())? != source { return Err("adaptive frozen codec roundtrip failed".into()); }
    let context = expertmix_native::encode(source, &EXPERT_MIX_ORDERS)?;
    if expertmix_native::decode(&context, source.len())? != source { return Err("context-expert frozen codec roundtrip failed".into()); }
    let fixed = fixedmix_native::encode(source);
    if fixedmix_native::decode(&fixed, source.len())? != source { return Err("fixed mixer frozen codec roundtrip failed".into()); }
    println!("{{\"trace\":\"PREDICTIVE-INFORMATION-TRACE-1\",\"selfcheck\":\"passed\",\"ppm_direct_byte_mass\":\"{ppm_mass:.17e}\",\"ppm\":\"unavailable_non_normalized_escape\"}}");
    Ok(())
}
fn usage() -> &'static str { "usage: trace INPUT OUTPUT.tsv | trace selfcheck" }
fn main() -> Result<(), String> {
    let mut args = env::args().skip(1);
    let input = args.next().ok_or_else(|| usage().to_owned())?;
    if input == "selfcheck" && args.next().is_none() { return selfcheck(); }
    let output = args.next().ok_or_else(|| usage().to_owned())?;
    if args.next().is_some() { return Err(usage().into()); }
    let data = fs::read(&input).map_err(|error| format!("read input: {error}"))?;
    if data.len() > MAX_INPUT { return Err(format!("input exceeds {MAX_INPUT}-byte trace cap")); }
    let started = Instant::now();
    let mut adaptive0 = adaptive_native::Trace::new(0);
    let mut adaptive1 = adaptive_native::Trace::new(1);
    let mut context = expertmix_native::Trace::new();
    let mut fixed = fixedmix_native::Trace::new(data.len());
    let mut rows = fs::File::create(&output).map_err(|error| format!("create trace: {error}"))?;
    writeln!(rows, "{}", header()).map_err(|error| error.to_string())?;
    let mut predict_nanos = [0u128; 4]; let mut observe_nanos = [0u128; 4];
    let mut run = 0usize; let mut previous = None;
    for (position, &actual) in data.iter().enumerate() {
        let pretarget_run = run;
        let prediction_started = Instant::now(); let adaptive0_distribution = adaptive0.distribution(); predict_nanos[0] += prediction_started.elapsed().as_nanos();
        let prediction_started = Instant::now(); let adaptive1_distribution = adaptive1.distribution(); predict_nanos[1] += prediction_started.elapsed().as_nanos();
        let prediction_started = Instant::now(); let selected_order = context.selected_order(); let context_distributions = context.distributions(); predict_nanos[2] += prediction_started.elapsed().as_nanos();
        let prediction_started = Instant::now(); let matching = fixed.match_available(); let fixed_distributions = fixed.distributions(); predict_nanos[3] += prediction_started.elapsed().as_nanos();
        let mut values = [Metrics { p_actual: 0.0, entropy: 0.0, maximum: 0.0, top: 0 }; 28];
        values[0] = metrics(&adaptive0_distribution, actual)?; values[1] = metrics(&adaptive1_distribution, actual)?;
        for index in 0..5 { values[2 + index] = metrics(&context_distributions[index], actual)?; }
        for index in 0..=FIXED_COMPONENTS { values[7 + index] = metrics(&fixed_distributions[index], actual)?; }
        let mut noisy = [[0.0; 4]; 28];
        let distributions: [&[f64; 256]; 28] = [
            &adaptive0_distribution, &adaptive1_distribution,
            &context_distributions[0], &context_distributions[1], &context_distributions[2], &context_distributions[3], &context_distributions[4],
            &fixed_distributions[0], &fixed_distributions[1], &fixed_distributions[2], &fixed_distributions[3], &fixed_distributions[4], &fixed_distributions[5], &fixed_distributions[6], &fixed_distributions[7], &fixed_distributions[8], &fixed_distributions[9], &fixed_distributions[10], &fixed_distributions[11], &fixed_distributions[12], &fixed_distributions[13], &fixed_distributions[14], &fixed_distributions[15], &fixed_distributions[16], &fixed_distributions[17], &fixed_distributions[18], &fixed_distributions[19], &fixed_distributions[20],
        ];
        for expert in 0..28 { for replicate in 0..4 { noisy[expert][replicate] = noisy_actual(distributions[expert], position, expert, replicate, actual); } }
        writeln!(rows, "{}", line(position, actual, pretarget_run, matching, selected_order, &values, &noisy)).map_err(|error| error.to_string())?;
        let update_started = Instant::now(); adaptive0.observe(actual); observe_nanos[0] += update_started.elapsed().as_nanos();
        let update_started = Instant::now(); adaptive1.observe(actual); observe_nanos[1] += update_started.elapsed().as_nanos();
        let update_started = Instant::now(); context.observe(actual); observe_nanos[2] += update_started.elapsed().as_nanos();
        let update_started = Instant::now(); fixed.observe(actual); observe_nanos[3] += update_started.elapsed().as_nanos();
        run = if previous == Some(actual) { run + 1 } else { 1 }; previous = Some(actual);
    }
    let summary_path = format!("{output}.summary.tsv"); let mut summary = fs::File::create(&summary_path).map_err(|error| format!("create summary: {error}"))?;
    writeln!(summary, "expert\teligible_normalized_byte_distribution\tpredict_group_nanos\tobserve_group_nanos\testimated_group_state_bytes\tnote").map_err(|error| error.to_string())?;
    let state = [adaptive0.state_bytes(), adaptive1.state_bytes(), context.state_bytes(), fixed.state_bytes()];
    for (index, name) in EXPERT_NAMES.iter().enumerate() {
        let (group, note) = if index == 0 { (0, "dedicated adaptive_o0 family measurement") }
            else if index == 1 { (1, "dedicated adaptive_o1 family measurement") }
            else if index < 7 { (2, "shared context family measurement; repeated per expert, not additive") }
            else { (3, "shared fixedmix family measurement; repeated per expert, not additive") };
        writeln!(summary, "{name}\tyes\t{}\t{}\t{}\t{note}", predict_nanos[group], observe_nanos[group], state[group]).map_err(|error| error.to_string())?;
    }
    writeln!(summary, "ppm_fixed_o4_escape1\tno\t0\t0\t0\tnative escape remains allocated after all 256 byte symbols are excluded; not normalized over bytes").map_err(|error| error.to_string())?;
    writeln!(summary, "trace_total_nanos\t\t{}", started.elapsed().as_nanos()).map_err(|error| error.to_string())?;
    Ok(())
}
