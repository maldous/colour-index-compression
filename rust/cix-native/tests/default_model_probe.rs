//! Native DEFAULT selector experiment `cixg1-ppm-predictability-v1`.
//!
//! These expectations intentionally describe the Rust selector after the
//! frozen Python parity checkpoint.  The promotion is generic: it uses only
//! the bounded two-byte prediction statistic from the current input block.

#[path = "../src/selection.rs"]
mod selection;

use selection::{generate_candidates, profile, shortlist, Features, LAGS, ROUTES};

#[test]
fn predictable_default_input_promotes_ppm_while_fast_stays_cheap() {
    let features = profile(b"abcdabcdabcdabcd", 16);
    let default = shortlist(&features, "balanced").expect("default shortlist");
    assert!(default.contains(&"ppm"));
    assert_eq!(default.len(), 7);

    let fast = shortlist(&features, "fast").expect("fast shortlist");
    assert!(!fast.contains(&"ppm"));
    assert_eq!(fast, ["runs", "deflate", "lz", "stride"]);

    let candidates =
        generate_candidates(&features, "balanced", None, None).expect("default candidates");
    assert!(candidates
        .iter()
        .any(|candidate| candidate.route == 8 && candidate.backend == "ppm"));
}

#[test]
fn high_entropy_repetition_keeps_lz_and_can_also_probe_ppm() {
    let features = Features {
        sample_bytes: 8192,
        entropy: 8.0,
        symbols: 256,
        run_fraction: 0.0,
        repeat_fraction: 0.25,
        lag_entropy: [8.0; LAGS.len()],
        predictability: 0.5,
        regional_entropy_range: 0.0,
    };
    let default = shortlist(&features, "balanced").expect("default shortlist");
    assert!(default.contains(&"lz"));
    assert!(default.contains(&"ppm"));
}

#[test]
fn best_remains_the_complete_native_route_set_and_overrides_constrain_normally() {
    let features = profile(b"abcdabcdabcdabcd", 16);
    assert_eq!(
        shortlist(&features, "maximum").expect("best shortlist"),
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
    assert_eq!(ROUTES.len(), 11);

    let predictor = generate_candidates(&features, "balanced", Some(4), Some("range"))
        .expect("predictor backend override");
    assert!(predictor
        .iter()
        .all(|candidate| candidate.route == 0
            || (candidate.route == 4 && candidate.backend == "range")));

    let ppm = generate_candidates(&features, "balanced", Some(8), Some("ppm"))
        .expect("PPM route override");
    assert!(ppm
        .iter()
        .any(|candidate| candidate.route == 8 && candidate.backend == "ppm"));
}
