use cix_native::oracle::{
    classify_selection, evaluate, CandidateKind, OracleConfig, SelectionOutcome,
};

fn small_config() -> OracleConfig {
    OracleConfig {
        max_input_bytes: 128,
        adaptive_orders: vec![0, 1],
        adaptive_bucket_bits: vec![4],
        ppm_orders: vec![0, 1, 2],
        fixedmix_eta_shifts: vec![5],
        lz_effort: 2,
        lz_model_limit: 256,
    }
}

fn deterministic_bytes(length: usize, seed: u32) -> Vec<u8> {
    let mut state = seed;
    (0..length)
        .map(|_| {
            // Fixed xorshift32: deterministic fixture generation with no
            // corpus or machine-dependent source.
            state ^= state << 13;
            state ^= state >> 17;
            state ^= state << 5;
            state as u8
        })
        .collect()
}

fn assert_every_declared_candidate_decodes(label: &str, input: &[u8]) {
    let report = evaluate(input, &small_config())
        .unwrap_or_else(|error| panic!("{label}: oracle evaluation failed: {error}"));
    // `evaluate` independently decodes before adding every candidate.  This
    // count ensures none of the declared route families was skipped.
    assert!(
        report.candidates.len() >= 35,
        "{label}: unexpectedly incomplete candidate universe"
    );
    assert!(report.contains(&CandidateKind::Raw), "{label}: raw missing");
    assert!(
        report.contains(&CandidateKind::Composition),
        "{label}: composition missing"
    );
    assert!(
        report.contains(&CandidateKind::CountRange),
        "{label}: count-range missing"
    );
    assert!(
        report
            .candidates
            .iter()
            .any(|candidate| matches!(candidate.kind, CandidateKind::PpmFixed { .. })),
        "{label}: fixed PPM missing"
    );
    assert!(
        report
            .candidates
            .iter()
            .any(|candidate| matches!(candidate.kind, CandidateKind::FixedMix { .. })),
        "{label}: fixed-mix missing"
    );
    assert!(
        report
            .candidates
            .iter()
            .any(|candidate| matches!(candidate.kind, CandidateKind::Lz { .. })),
        "{label}: LZ missing"
    );
}

#[test]
fn materializes_and_restores_every_declared_candidate() {
    let input = b"abcabcabcabc---abcabcabcabc---01234567890123456789";
    let report = evaluate(input, &small_config()).expect("synthetic oracle report");
    assert!(report.candidates.len() > 20);
    assert!(report.contains(&CandidateKind::Raw));
    assert!(report.contains(&CandidateKind::Composition));
    assert!(report.contains(&CandidateKind::CountRange));
    assert!(report.contains(&CandidateKind::Adaptive {
        order: 1,
        bucket_bits: 4
    }));
    assert!(report
        .candidates
        .iter()
        .any(|candidate| matches!(candidate.kind, CandidateKind::PpmSecondary { order: 2, .. })));
    assert!(report
        .candidates
        .iter()
        .any(|candidate| matches!(candidate.kind, CandidateKind::Lz { .. })));
    assert!(report.winning().payload.len() <= input.len());
}

#[test]
fn exact_decoding_covers_deterministic_synthetic_fixture_families() {
    let random = deterministic_bytes(96, 0x1357_9bdf);
    let repeated_seed = deterministic_bytes(48, 0x2468_ace1);
    let mut high_entropy_repeat = repeated_seed.clone();
    high_entropy_repeat.extend_from_slice(&repeated_seed);
    let mut mixed_region = vec![b'A'; 24];
    mixed_region.extend_from_slice(&deterministic_bytes(40, 0x9e37_79b9));
    mixed_region.extend((0..24).map(|index| (index % 5) as u8));
    mixed_region.extend_from_slice(b"record=0001\nrecord=0002\nrecord=0003\n");

    for (label, fixture) in [
        ("tiny", vec![0xa5]),
        ("deterministic-random", random),
        ("high-entropy-repeated-substring", high_entropy_repeat),
        ("repetitive", vec![b'Z'; 96]),
        ("mixed-region", mixed_region),
    ] {
        assert_every_declared_candidate_decodes(label, &fixture);
    }
}

#[test]
fn identifies_shortlist_miss_and_scoring_tie() {
    let input = b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
    let report = evaluate(input, &small_config()).expect("synthetic oracle report");
    let winner = report.winning().kind.clone();
    assert!(matches!(
        classify_selection(&report, &[CandidateKind::Raw], &CandidateKind::Raw),
        SelectionOutcome::ShortlistMiss { .. }
    ));
    assert_eq!(
        classify_selection(&report, &[winner.clone()], &winner),
        SelectionOutcome::Optimal
    );
    assert!(matches!(
        classify_selection(
            &report,
            &[winner],
            &CandidateKind::Lz {
                description: "not-in-report".into()
            }
        ),
        SelectionOutcome::DecodeFailure { .. }
    ));
}

#[test]
fn identifies_a_nonwinning_materialized_candidate_as_a_scorer_error() {
    let input = b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
    let report = evaluate(input, &small_config()).expect("synthetic oracle report");
    let winner = report.winning().kind.clone();
    let nonwinner = report
        .candidates
        .iter()
        .find(|candidate| candidate.payload.len() > report.winning().payload.len())
        .expect("fixture must contain a strictly larger decoded candidate")
        .kind
        .clone();
    assert!(matches!(
        classify_selection(&report, &[winner, nonwinner.clone()], &nonwinner),
        SelectionOutcome::ScorerError { .. }
    ));
}

#[test]
fn rejects_unbounded_input() {
    let config = small_config();
    let input = vec![7u8; config.max_input_bytes + 1];
    assert!(evaluate(&input, &config).is_err());
}

#[test]
fn rejects_malformed_or_unbounded_oracle_configuration() {
    let cases = [
        OracleConfig {
            lz_effort: 0,
            ..small_config()
        },
        OracleConfig {
            adaptive_orders: vec![17],
            ..small_config()
        },
        OracleConfig {
            adaptive_bucket_bits: vec![0],
            ..small_config()
        },
        OracleConfig {
            ppm_orders: vec![9],
            ..small_config()
        },
        OracleConfig {
            fixedmix_eta_shifts: vec![4],
            ..small_config()
        },
        OracleConfig {
            lz_model_limit: 0,
            ..small_config()
        },
    ];
    for config in cases {
        assert!(evaluate(b"config", &config).is_err());
    }
}

#[test]
fn handles_an_empty_synthetic_block() {
    let report = evaluate(&[], &small_config()).expect("empty oracle report");
    assert!(report.contains(&CandidateKind::Raw));
}
