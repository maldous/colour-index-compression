//! Bounded exact oracle for the public native library candidate space.
//!
//! This is deliberately a *payload* oracle.  It materializes and decodes each
//! candidate below, then compares payload lengths exactly.  It does not claim
//! to search the complete CLI/container space: CIXG1/CIXG2 framing, CIXM6
//! modes, transforms (BWT, stride, phrases, predictor), block segmentation,
//! history sharing, external codecs, and the private CLI route encoder live in
//! `main.rs` and are therefore excluded.  Callers must add their framing cost
//! before using a payload winner as an archive winner.
//!
//! The candidate universe is intentionally finite and documented in
//! [`OracleConfig`].  For a supplied config, [`evaluate`] materializes every
//! candidate in that universe; it never estimates a candidate's size.

use crate::{adaptive, fixedmix, legacy_lz, ppm, rank};

/// Default upper limit for one oracle block.  The oracle is for diagnosis on
/// small blocks, not an alternative production selector.
pub const DEFAULT_MAX_INPUT_BYTES: usize = 4096;

/// Explicit finite public-library candidate universe.
///
/// It includes raw; exact composition and count-range coders; every declared
/// adaptive `(order, bucket_bits)` pair; every PPM order/escape/update/SEE
/// variant; each fixed-mix learning rate; and the complete bounded LZ
/// `encode_candidates` portfolio at `lz_effort`.  PPM's fixed and secondary
/// encoders are materialized separately so parameter ties are observable.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OracleConfig {
    pub max_input_bytes: usize,
    pub adaptive_orders: Vec<usize>,
    pub adaptive_bucket_bits: Vec<usize>,
    pub ppm_orders: Vec<usize>,
    pub fixedmix_eta_shifts: Vec<u8>,
    pub lz_effort: u8,
    pub lz_model_limit: usize,
}

impl Default for OracleConfig {
    fn default() -> Self {
        Self {
            max_input_bytes: DEFAULT_MAX_INPUT_BYTES,
            // These are the context candidates currently exposed to the
            // native selector.  Broader parameter grids must be stated by a
            // caller; this prevents an unbounded oracle by accident.
            adaptive_orders: vec![0, 1, 2],
            adaptive_bucket_bits: vec![4, 8, 10],
            ppm_orders: (0..=8).collect(),
            fixedmix_eta_shifts: vec![5, 6, 7],
            lz_effort: 9,
            lz_model_limit: 1 << 12,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum CandidateKind {
    Raw,
    Composition,
    CountRange,
    Adaptive {
        order: usize,
        bucket_bits: usize,
    },
    PpmFixed {
        order: usize,
        escape_method: u8,
        update_exclusion: bool,
    },
    PpmSecondary {
        order: usize,
        update_exclusion: bool,
    },
    FixedMix {
        eta_shift: u8,
    },
    Lz {
        description: String,
    },
}

impl CandidateKind {
    pub fn name(&self) -> String {
        match self {
            Self::Raw => "raw".into(),
            Self::Composition => "composition".into(),
            Self::CountRange => "count-range".into(),
            Self::Adaptive { order, bucket_bits } => {
                format!("context-range-o{order}-b{bucket_bits}")
            }
            Self::PpmFixed {
                order,
                escape_method,
                update_exclusion,
            } => format!(
                "ppm-o{order}-escape{escape_method}-update{}",
                u8::from(*update_exclusion)
            ),
            Self::PpmSecondary {
                order,
                update_exclusion,
            } => format!(
                "ppm-o{order}-secondary-update{}",
                u8::from(*update_exclusion)
            ),
            Self::FixedMix { eta_shift } => format!("fixedmix-eta{eta_shift}"),
            Self::Lz { description } => description.clone(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CandidateResult {
    pub kind: CandidateKind,
    pub payload: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OracleReport {
    pub candidates: Vec<CandidateResult>,
    /// Stable first-minimum winner.  Candidate generation order is part of
    /// the report so a tie can be distinguished from a scoring error.
    pub winner: usize,
}

impl OracleReport {
    pub fn winning(&self) -> &CandidateResult {
        &self.candidates[self.winner]
    }

    pub fn contains(&self, kind: &CandidateKind) -> bool {
        self.candidates
            .iter()
            .any(|candidate| &candidate.kind == kind)
    }
}

/// Why a production shortlist/score differs from a fully materialized oracle.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum SelectionOutcome {
    Optimal,
    /// The oracle winner was never presented to the production scorer.
    ShortlistMiss {
        oracle_winner: CandidateKind,
    },
    /// The scorer selected a materialized candidate with a larger payload.
    ScorerError {
        oracle_winner: CandidateKind,
        selected: CandidateKind,
    },
    /// The scorer selected a non-first candidate with the same exact payload
    /// length as the oracle winner.
    Tie {
        oracle_winner: CandidateKind,
        selected: CandidateKind,
    },
    /// A caller attempted to evaluate a candidate that was not verified by
    /// this oracle, or a candidate failed decode during evaluation.
    DecodeFailure {
        candidate: CandidateKind,
        message: String,
    },
}

fn validate(config: &OracleConfig, input_len: usize) -> Result<(), String> {
    if input_len > config.max_input_bytes {
        return Err(format!(
            "oracle input is {input_len} bytes; configured maximum is {}",
            config.max_input_bytes
        ));
    }
    if !(1..=9).contains(&config.lz_effort) {
        return Err("oracle LZ effort must be between 1 and 9".into());
    }
    if config.lz_model_limit == 0 {
        return Err("oracle LZ model limit must be nonzero".into());
    }
    for &order in &config.adaptive_orders {
        if order > 16 {
            return Err("oracle adaptive order exceeds 16".into());
        }
    }
    for &bits in &config.adaptive_bucket_bits {
        if !(1..=16).contains(&bits) {
            return Err("oracle adaptive bucket bits must be 1 through 16".into());
        }
    }
    for &order in &config.ppm_orders {
        if order > 8 {
            return Err("oracle PPM order exceeds 8".into());
        }
    }
    for &eta in &config.fixedmix_eta_shifts {
        if !matches!(eta, 5 | 6 | 7) {
            return Err("oracle fixed-mix eta must be 5, 6, or 7".into());
        }
    }
    Ok(())
}

fn verified(
    input: &[u8],
    kind: CandidateKind,
    payload: Vec<u8>,
    decode: impl FnOnce(&[u8]) -> Result<Vec<u8>, String>,
) -> Result<CandidateResult, SelectionOutcome> {
    match decode(&payload) {
        Ok(restored) if restored == input => Ok(CandidateResult { kind, payload }),
        Ok(_) => Err(SelectionOutcome::DecodeFailure {
            candidate: kind,
            message: "candidate decoder restored different bytes".into(),
        }),
        Err(message) => Err(SelectionOutcome::DecodeFailure {
            candidate: kind,
            message,
        }),
    }
}

/// Materialize and fresh-decode every candidate in `config`'s declared finite
/// universe.  The returned winner minimizes payload bytes exactly.
pub fn evaluate(input: &[u8], config: &OracleConfig) -> Result<OracleReport, String> {
    validate(config, input.len())?;
    let mut candidates = Vec::new();
    candidates.push(CandidateResult {
        kind: CandidateKind::Raw,
        payload: input.to_vec(),
    });

    let composition = rank::encode_composition_tiles(input)?;
    candidates.push(
        verified(input, CandidateKind::Composition, composition, |blob| {
            rank::decode_composition_tiles(blob, input.len())
        })
        .map_err(format_outcome)?,
    );
    let count_range = rank::encode_count_range(input)?;
    candidates.push(
        verified(input, CandidateKind::CountRange, count_range, |blob| {
            rank::decode_composition_tiles(blob, input.len())
        })
        .map_err(format_outcome)?,
    );

    for &order in &config.adaptive_orders {
        for &bucket_bits in &config.adaptive_bucket_bits {
            let model_limit = 1usize.checked_shl(bucket_bits as u32).unwrap_or(usize::MAX);
            let payload = adaptive::encode_general(input, order, bucket_bits, &[], model_limit)?;
            candidates.push(
                verified(
                    input,
                    CandidateKind::Adaptive { order, bucket_bits },
                    payload,
                    |blob| adaptive::decode_general(blob, input.len(), &[], model_limit),
                )
                .map_err(format_outcome)?,
            );
        }
    }
    for &order in &config.ppm_orders {
        for update_exclusion in [false, true] {
            for escape_method in 0..=3 {
                let payload =
                    ppm::encode_fixed(input, order, &[], escape_method, update_exclusion)?;
                candidates.push(
                    verified(
                        input,
                        CandidateKind::PpmFixed {
                            order,
                            escape_method,
                            update_exclusion,
                        },
                        payload,
                        |blob| ppm::decode(blob, input.len()),
                    )
                    .map_err(format_outcome)?,
                );
            }
            let payload = ppm::encode_secondary(input, order, &[], update_exclusion)?;
            candidates.push(
                verified(
                    input,
                    CandidateKind::PpmSecondary {
                        order,
                        update_exclusion,
                    },
                    payload,
                    |blob| ppm::decode(blob, input.len()),
                )
                .map_err(format_outcome)?,
            );
        }
    }
    for &eta_shift in &config.fixedmix_eta_shifts {
        let payload = fixedmix::encode_with_history_eta(input, &[], eta_shift)?;
        candidates.push(
            verified(
                input,
                CandidateKind::FixedMix { eta_shift },
                payload,
                |blob| fixedmix::decode(blob, input.len()),
            )
            .map_err(format_outcome)?,
        );
    }
    for encoded in legacy_lz::encode_candidates(input, &[], config.lz_effort)? {
        let kind = CandidateKind::Lz {
            description: encoded.description,
        };
        candidates.push(
            verified(input, kind, encoded.payload, |blob| {
                legacy_lz::decode(blob, input.len(), &[], config.lz_model_limit)
            })
            .map_err(format_outcome)?,
        );
    }
    let winner = candidates
        .iter()
        .enumerate()
        .min_by_key(|(_, candidate)| candidate.payload.len())
        .map(|(index, _)| index)
        .ok_or("oracle generated no candidates")?;
    Ok(OracleReport { candidates, winner })
}

fn format_outcome(outcome: SelectionOutcome) -> String {
    match outcome {
        SelectionOutcome::DecodeFailure { candidate, message } => {
            format!("oracle decode failure for {}: {message}", candidate.name())
        }
        _ => "invalid oracle outcome while evaluating candidate".into(),
    }
}

/// Compare a production shortlist and its chosen candidate against `report`.
/// `selected` must use the exact payload identity generated by this oracle.
pub fn classify_selection(
    report: &OracleReport,
    shortlist: &[CandidateKind],
    selected: &CandidateKind,
) -> SelectionOutcome {
    let winner = report.winning();
    if !shortlist.iter().any(|candidate| candidate == &winner.kind) {
        return SelectionOutcome::ShortlistMiss {
            oracle_winner: winner.kind.clone(),
        };
    }
    let Some(actual) = report
        .candidates
        .iter()
        .find(|candidate| candidate.kind == *selected)
    else {
        return SelectionOutcome::DecodeFailure {
            candidate: selected.clone(),
            message: "selected candidate is outside this verified oracle report".into(),
        };
    };
    if actual.payload.len() == winner.payload.len() {
        if actual.kind == winner.kind {
            SelectionOutcome::Optimal
        } else {
            SelectionOutcome::Tie {
                oracle_winner: winner.kind.clone(),
                selected: actual.kind.clone(),
            }
        }
    } else {
        SelectionOutcome::ScorerError {
            oracle_winner: winner.kind.clone(),
            selected: actual.kind.clone(),
        }
    }
}
