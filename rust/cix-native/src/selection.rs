//! Frozen CIXG1 byte profiler and bounded route shortlist.
//!
//! This module mirrors `cix.pipeline` at reference commit
//! `80b95427725ecf59d626b2982d50f6349abd56e1`. Probe adjacency is local to
//! each sampled region, while repeat and context state are shared between
//! regions, matching the Python implementation.

use std::collections::{HashMap, HashSet};

pub const ROUTES: [&str; 11] = [
    "raw",
    "runs",
    "composition",
    "lz",
    "predictor",
    "bwt",
    "stride",
    "phrases",
    "ppm",
    "mixture",
    "deflate",
];

pub const LAGS: [usize; 7] = [1, 2, 4, 8, 16, 32, 64];

/// One materializable CIXG1 encoding candidate. The representation and
/// backend are independent dimensions; future route parameters and packaging
/// can extend this spec without changing the CLI effort names.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Candidate {
    pub route: u8,
    pub backend: String,
    /// Route-specific, self-describing parameter carried inside the payload.
    /// PPM order is stored in its payload header; candidates remain limited
    /// to orders accepted by the frozen Python reference decoder.
    pub parameter: Option<u8>,
}

fn baseline_backend(route: u8) -> &'static str {
    match route {
        2 => "cix",
        8 => "ppm",
        10 => "deflate",
        _ => "hybrid",
    }
}

fn nested_backends(route: u8, effort_name: &str) -> &'static [&'static str] {
    if !(2..=7).contains(&route) || effort_name == "fast" {
        &[]
    } else if effort_name == "balanced" {
        &["hybrid", "cix", "deflate"]
    } else {
        &["cix", "deflate", "hybrid", "range", "count-range"]
    }
}

/// Generate an ordered, finite CIXG1 candidate set. Python-reference route
/// order comes first; extension backends follow so strict-size ties preserve
/// the reference winner. `forced_route` and `forced_backend` constrain only
/// their named dimensions.
pub fn generate_candidates(
    features: &Features,
    effort_name: &str,
    forced_route: Option<u8>,
    forced_backend: Option<&str>,
) -> Result<Vec<Candidate>, String> {
    let mut routes = if let Some(route) = forced_route {
        vec![route]
    } else {
        shortlist(features, effort_name)?
            .iter()
            .map(|name| {
                ROUTES
                    .iter()
                    .position(|candidate| candidate == name)
                    .map(|id| id as u8)
                    .ok_or_else(|| format!("unknown route {name}"))
            })
            .collect::<Result<Vec<_>, _>>()?
    };
    if forced_route == Some(8) && forced_backend.is_some_and(|backend| backend != "ppm") {
        return Err("the PPM route does not support a nested backend override".into());
    }
    // A global nested-backend override excludes representations whose coder
    // is intrinsic (PPM); never mislabel their payload as the requested coder.
    if forced_backend.is_some_and(|backend| backend != "ppm") {
        routes.retain(|&route| route != 8);
    }
    let mut candidates = vec![Candidate {
        route: 0,
        backend: "raw".into(),
        parameter: None,
    }];
    let mut base = Vec::new();
    for &route in &routes {
        let backend = if route == 8 {
            "ppm"
        } else {
            forced_backend.unwrap_or_else(|| baseline_backend(route))
        };
        base.push(Candidate {
            route,
            backend: backend.into(),
            parameter: (route == 8).then_some(3),
        });
    }
    candidates.extend(base);
    if forced_backend.is_none() {
        for &route in &routes {
            for &backend in nested_backends(route, effort_name) {
                let candidate = Candidate {
                    route,
                    backend: backend.into(),
                    parameter: None,
                };
                if !candidates.contains(&candidate) {
                    candidates.push(candidate);
                }
            }
        }
    }
    // PPM's order is independently serialized in its payload. The frozen
    // Python decoder accepts orders 0..=3; the baseline stays first for stable
    // ties and effort widens only within that compatibility range.
    let ppm_orders: &[u8] = match effort_name {
        "fast" => &[2],
        "balanced" => &[1, 2],
        "maximum" => &[1, 2],
        _ => return Err(format!("unknown CIXG1 effort profile: {effort_name}")),
    };
    for &route in &routes {
        if route != 8 {
            continue;
        }
        for &order in ppm_orders {
            candidates.push(Candidate {
                route,
                backend: "ppm".into(),
                parameter: Some(order),
            });
        }
    }
    Ok(candidates)
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Effort {
    pub block_bytes: usize,
    pub sample_bytes: usize,
    pub candidate_limit: usize,
    pub search_seconds: f64,
    pub trial_seconds: f64,
    pub worker_memory_mib: usize,
}

pub const FAST: Effort = Effort {
    block_bytes: 32_768,
    sample_bytes: 2_048,
    candidate_limit: 4,
    search_seconds: 0.75,
    trial_seconds: 0.30,
    worker_memory_mib: 256,
};

pub const BALANCED: Effort = Effort {
    block_bytes: 32_768,
    sample_bytes: 4_096,
    candidate_limit: 7,
    search_seconds: 3.0,
    trial_seconds: 1.0,
    worker_memory_mib: 384,
};

pub const MAXIMUM: Effort = Effort {
    block_bytes: 65_536,
    sample_bytes: 8_192,
    candidate_limit: 10,
    search_seconds: 12.0,
    trial_seconds: 4.0,
    worker_memory_mib: 512,
};

pub const EFFORTS: [(&str, Effort); 3] =
    [("fast", FAST), ("balanced", BALANCED), ("maximum", MAXIMUM)];

pub fn effort(name: &str) -> Option<Effort> {
    EFFORTS
        .iter()
        .find_map(|(candidate, config)| (*candidate == name).then_some(*config))
}

#[derive(Clone, Debug, PartialEq)]
pub struct Features {
    pub sample_bytes: usize,
    pub entropy: f64,
    pub symbols: usize,
    pub run_fraction: f64,
    pub repeat_fraction: f64,
    /// Entropies correspond positionally to [`LAGS`].
    pub lag_entropy: [f64; LAGS.len()],
    pub predictability: f64,
    pub regional_entropy_range: f64,
}

struct Histogram {
    counts: [usize; 256],
    first_seen: Vec<u8>,
    len: usize,
}

impl Default for Histogram {
    fn default() -> Self {
        Self {
            counts: [0; 256],
            first_seen: Vec::new(),
            len: 0,
        }
    }
}

impl Histogram {
    fn observe(&mut self, value: u8) {
        let count = &mut self.counts[usize::from(value)];
        if *count == 0 {
            self.first_seen.push(value);
        }
        *count += 1;
        self.len += 1;
    }

    fn entropy(&self) -> f64 {
        if self.len == 0 {
            return 0.0;
        }
        let n = self.len as f64;
        let weighted_log_sum = self.first_seen.iter().fold(0.0, |sum, &value| {
            let count = self.counts[usize::from(value)] as f64;
            sum + count * count.log2()
        });
        n.log2() - weighted_log_sum / n
    }
}

fn entropy(data: &[u8]) -> f64 {
    let mut histogram = Histogram::default();
    for &value in data {
        histogram.observe(value);
    }
    histogram.entropy()
}

/// Profile bounded, spread samples of one input block.
///
/// `cap` is the frozen total sample budget. As in Python, each of up to four
/// regions has width `max(1, cap / 4)`, and overlapping regions are not merged.
pub fn profile(data: &[u8], cap: usize) -> Features {
    let width = (cap / 4).max(1);
    let two_thirds = (data.len() / 3) * 2 + ((data.len() % 3) * 2) / 3;
    let mut starts = vec![
        0,
        data.len() / 3,
        two_thirds,
        data.len().saturating_sub(width),
    ];
    starts.sort_unstable();
    starts.dedup();

    let parts: Vec<&[u8]> = starts
        .into_iter()
        .map(|start| &data[start..start.saturating_add(width).min(data.len())])
        .collect();

    let mut sample = Histogram::default();
    let mut run_equal = 0usize;
    for part in &parts {
        for &value in *part {
            sample.observe(value);
        }
        run_equal += part.windows(2).filter(|pair| pair[0] == pair[1]).count();
    }

    let mut seen = HashSet::<[u8; 4]>::new();
    let mut repeats = 0usize;
    let mut keys = 0usize;
    for part in &parts {
        for key in part.windows(4) {
            let key = [key[0], key[1], key[2], key[3]];
            repeats += usize::from(!seen.insert(key));
            keys += 1;
        }
    }

    let lag_entropy = LAGS.map(|lag| {
        let mut residuals = Histogram::default();
        for part in &parts {
            for index in lag..part.len() {
                residuals.observe(part[index] ^ part[index - lag]);
            }
        }
        residuals.entropy()
    });

    let mut contexts = HashMap::<[u8; 2], u8>::new();
    let mut hits = 0usize;
    let mut opportunities = 0usize;
    for part in &parts {
        for index in 2..part.len() {
            let key = [part[index - 2], part[index - 1]];
            if let Some(&prediction) = contexts.get(&key) {
                opportunities += 1;
                hits += usize::from(prediction == part[index]);
            }
            contexts.insert(key, part[index]);
        }
    }

    let first_regional_entropy = entropy(parts[0]);
    let (minimum_regional_entropy, maximum_regional_entropy) = parts[1..].iter().fold(
        (first_regional_entropy, first_regional_entropy),
        |(minimum, maximum), part| {
            let value = entropy(part);
            (minimum.min(value), maximum.max(value))
        },
    );

    Features {
        sample_bytes: sample.len,
        entropy: sample.entropy(),
        symbols: sample.first_seen.len(),
        run_fraction: run_equal as f64 / sample.len.saturating_sub(parts.len()).max(1) as f64,
        repeat_fraction: repeats as f64 / keys.max(1) as f64,
        lag_entropy,
        predictability: hits as f64 / opportunities.max(1) as f64,
        regional_entropy_range: maximum_regional_entropy - minimum_regional_entropy,
    }
}

/// Return the frozen, ordered candidate route names for an effort profile.
pub fn shortlist(features: &Features, effort_name: &str) -> Result<Vec<&'static str>, String> {
    let config = effort(effort_name)
        .ok_or_else(|| format!("unknown CIXG1 effort profile: {effort_name}"))?;

    let mut routes = vec!["runs", "deflate"];
    let mut priorities = Vec::with_capacity(12);
    if features.repeat_fraction > 0.01 {
        priorities.push("lz");
    }

    // Python's min() compares in insertion order. Spell this out so even a
    // caller-provided NaN has the same behavior as the frozen implementation.
    let mut minimum_lag_entropy = features.lag_entropy[0];
    for &value in &features.lag_entropy[1..] {
        if value < minimum_lag_entropy {
            minimum_lag_entropy = value;
        }
    }
    if minimum_lag_entropy < features.entropy - 0.20 {
        priorities.push("stride");
    }
    if features.predictability > 0.1 {
        priorities.push("predictor");
    }
    if features.symbols < 96 || features.entropy < 5.5 {
        priorities.push("composition");
    }
    priorities.extend([
        "lz",
        "bwt",
        "stride",
        "predictor",
        "phrases",
        "composition",
        "ppm",
        "mixture",
    ]);

    for route in priorities {
        if !routes.contains(&route) {
            routes.push(route);
        }
    }
    routes.truncate(config.candidate_limit);
    Ok(routes)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn assert_near(actual: f64, expected: f64) {
        assert!(
            (actual - expected).abs() < 1e-12,
            "expected {expected}, got {actual}"
        );
    }

    #[test]
    fn empty_profile_matches_frozen_python() {
        let features = profile(&[], 0);
        assert_eq!(features.sample_bytes, 0);
        assert_eq!(features.symbols, 0);
        assert_eq!(features.entropy, 0.0);
        assert_eq!(features.run_fraction, 0.0);
        assert_eq!(features.repeat_fraction, 0.0);
        assert_eq!(features.lag_entropy, [0.0; LAGS.len()]);
        assert_eq!(features.predictability, 0.0);
        assert_eq!(features.regional_entropy_range, 0.0);
    }

    #[test]
    fn spread_profile_matches_frozen_python_vector() {
        let features = profile(b"abcdabcdabcdabcd", 16);
        assert_eq!(features.sample_bytes, 16);
        assert_eq!(features.symbols, 4);
        assert_near(features.entropy, 2.0);
        assert_near(features.run_fraction, 0.0);
        assert_near(features.repeat_fraction, 0.25);
        assert_near(features.lag_entropy[0], 1.959_147_917_027_244_8);
        assert_near(features.lag_entropy[1], 1.0);
        assert_eq!(&features.lag_entropy[2..], &[0.0; 5]);
        assert_near(features.predictability, 1.0);
        assert_near(features.regional_entropy_range, 0.0);
    }

    #[test]
    fn shortlist_preserves_priority_and_effort_order() {
        let features = profile(b"abcdabcdabcdabcd", 16);
        assert_eq!(
            shortlist(&features, "fast").unwrap(),
            ["runs", "deflate", "lz", "stride"]
        );
        assert_eq!(
            shortlist(&features, "maximum").unwrap(),
            [
                "runs",
                "deflate",
                "lz",
                "stride",
                "predictor",
                "composition",
                "bwt",
                "phrases",
                "ppm",
                "mixture",
            ]
        );
    }

    #[test]
    fn shortlist_fallback_order_and_limits_match_frozen_python() {
        let features = Features {
            sample_bytes: 256,
            entropy: 8.0,
            symbols: 256,
            run_fraction: 0.0,
            repeat_fraction: 0.0,
            lag_entropy: [8.0; LAGS.len()],
            predictability: 0.0,
            regional_entropy_range: 0.0,
        };
        assert_eq!(
            shortlist(&features, "balanced").unwrap(),
            [
                "runs",
                "deflate",
                "lz",
                "bwt",
                "stride",
                "predictor",
                "phrases",
            ]
        );
        assert!(shortlist(&features, "unknown").is_err());
    }

    #[test]
    fn candidate_generation_keeps_dimensions_independent() {
        let features = profile(b"abcdabcdabcdabcd", 16);
        let best = generate_candidates(&features, "maximum", None, None).unwrap();
        assert_eq!(best.first().unwrap().route, 0);
        assert!(best.iter().any(|item| item.route == 8));
        assert!(best
            .iter()
            .any(|item| item.route == 4 && item.backend == "count-range"));
        let ppm_orders: Vec<_> = best
            .iter()
            .filter(|item| item.route == 8)
            .filter_map(|item| item.parameter)
            .collect();
        assert_eq!(ppm_orders, [3, 1, 2]);

        let route_locked = generate_candidates(&features, "maximum", Some(4), None).unwrap();
        assert!(route_locked
            .iter()
            .all(|item| item.route == 4 || item.route == 0));
        assert!(route_locked
            .iter()
            .any(|item| item.backend == "count-range"));

        let backend_locked =
            generate_candidates(&features, "maximum", None, Some("range")).unwrap();
        assert!(backend_locked
            .iter()
            .filter(|item| item.route != 0)
            .all(|item| item.backend == "range"));
        assert!(!backend_locked.iter().any(|item| item.route == 8));
        assert!(generate_candidates(&features, "maximum", Some(8), Some("range")).is_err());

        let fast = generate_candidates(&features, "fast", Some(8), None).unwrap();
        assert!(fast.iter().all(|item| item.backend != "count-range"));
        assert!(fast.len() < best.len());
        assert_eq!(
            fast.iter()
                .filter(|item| item.route == 8)
                .filter_map(|item| item.parameter)
                .collect::<Vec<_>>(),
            [3, 2]
        );
    }
}
