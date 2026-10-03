# Release 0.1 predictive opportunity closure

This is a new diagnostic only. CPI1, its source snapshot, traces, receipts,
and conclusions remain immutable. No route, selector, archive format, or
production source is changed by this work.

## Question

Does the corrected, already implemented fixed-mixer recurrence state expose
causal byte-level information missing from CPI1's version-1 fixed mixer, and
does native PPM's paid escape interval leave a measurable opportunity after
all costs are represented honestly?

## Frozen candidates

The trace binds only to a fresh immutable source copy using
`CIX_RELEASE_SOURCE`.

| Label | Native implementation | Configuration | Status in probability pool |
| --- | --- | --- | --- |
| `fixedmix_v1` | `fixedmix::State::new` | eta 6, no recurrence | incumbent diagnostic comparator |
| `fixedmix_v3_n1` | `fixedmix::State::with_recurrence` | saturated recurrence `{ bucket_bits: 4, max_distance: 1024 }`, eta 6 | candidate expert |
| `fixedmix_v3_n2` | same | saturated recurrence `{ bucket_bits: 6, max_distance: 16384 }`, eta 6 | candidate expert |
| `ppm_o3_e1_native_subprob` | `ppm::encode_fixed` semantics | order 3, escape method 1, `update_exclusion=false` | native interval diagnostic only |
| `ppm_o3_e1_validmass_normalized_diagnostic` | explicit new analysis model | native hit paths divided by their reachable final-byte mass | not native PPM and never a production claim |
| `ppm_o3_see` | `ppm::encode_secondary` semantics | order 3, `update_exclusion=false` | included only after exact event-times-symbol extraction and byte-mass proof |

`fixedmix_v3_n1` and `fixedmix_v3_n2` are existing corrected production code
paths. The trace only makes their causal byte probability observable. Each
byte distribution is the product of its eight conditional bit probabilities.
For v3, each realised byte is scored by the native eight-bit sequence, updating
state between its bits. The self-check reconstructs each of the 256 candidate
paths from the same small history and verifies positivity and byte-mass one.
This is deliberately a bounded replay diagnostic, not a claim that bit state
can be treated as independently updated.

Native fixed PPM has a sequence of probability events, including escapes and a
fallback rank. A direct hit-only byte view is generally subnormal. The trace
records its exact native path probability and `native_valid_byte_mass`; it
does not mix that quantity with normal byte experts. The separately named
valid-mass normalization is a diagnostic new model, used only to ask whether
the paid escape mass is the limiting cost. It must report the normalizer and
is excluded from native-PPM comparisons.

### SEE inspection boundary

The inspected `encode_secondary` path first codes a hit/escape event from the
adaptive SEE state, then codes a hit symbol from the eligible-count mass. On
an escape it excludes the eligible symbols and continues, finally using the
fallback rank. That makes an exact native realised-path probability available
in principle, but does not by itself create a normalized next-byte
distribution: an escape event can retain mass after all final byte symbols are
already direct hits, while the ultimate fallback alphabet is empty. Replacing
that event mass with a byte distribution would define a new model. Therefore
SEE is excluded from the comparable pool unless a future trace first reports
the native final-byte mass and proves it is one on every evaluated state. If
it is not one, SEE may only appear as an explicitly labelled subprobability
diagnostic under the same rule as fixed PPM.

## Instrument and outputs

`rust/cix-native/experiments/release-opportunities/release_trace.rs` accepts
`release_trace INPUT OUTPUT.tsv`, caps input at 16 KiB, and writes scientific
notation. Each row contains position, actual byte, realised-byte probability
for v1, N1 and N2, then native PPM path probability, native valid final-byte
mass, and normalized-diagnostic probability. Entropy, top-byte, run,
recurrence-feature, timing and state-size diagnostics are not emitted by this
first bounded instrument and must not be implied by its evidence.

Before any real trace the implemented self-check must pass:

1. distributions sum to one for all fixed-mixer candidates;
2. for several histories and every candidate byte, independently replayed
   v1/N1/N2 native eight-bit paths are positive and sum to one;
3. changing a suffix cannot alter a prefix trace;
4. PPM's full-alphabet native final-byte mass is the known 0.5 defect; and
5. a small complementary-expert fixture preserves the expected ordering of
   oracle, switching, static, and online losses.

Codec round trips, arithmetic interval-versus-ideal accounting, per-expert
timing/state, forced-escape PPM cases, and exact Bayesian/switching formula
equalities are follow-up validation work. They are not evidence supplied by
this version of the trace.

## Qualification and decision

Root freezes fresh, unread local real regions after source and this plan are
frozen. Work follows Canterbury, Calgary, then Artificial gates; no Silesia,
Hutter, acquisition, or broad benchmark work begins here. Development chooses
only whether SEE has met its exact-extraction gate. Held-out analysis freezes
the expert set and all online/static settings before reading the data.

Report ideal log loss separately from integer interval loss, arithmetic output,
metadata and complete archive bytes. A physical research route is considered
only if a causal v3 addition improves held-out loss by more than 0.05 bits per
input byte over CPI1's incumbent v1 and the frozen static/online pool, then
retains the gain after finite-precision and framing costs. Otherwise close the
opportunity. The trace is bounded to 16 KiB and a five-minute run ceiling; the
existing WaveScheduler owns execution.
