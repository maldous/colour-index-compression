# CIX / Six complementary predictive information audit — model inventory

**Status:** code audit only; no experiment, codec change, production change, or
numeric structural-composition reopening.  This document is based on the
current native implementation, with the frozen production revision recorded by
the directive as `d3a2cd416`, and its retained Python reference/research code.
The CIXG selector's route names are explicitly not treated as a model inventory.

## Terms used here

* **Model / expert:** a mechanism which, before the next target is known,
  assigns it a distribution (or a sequence of conditional bit probabilities).
* **Coder:** turns already-provided intervals or frequencies into bits.  It is
  not an expert merely because it is called `range` or `arithmetic`.
* **Transform / representation:** reversibly changes bytes or emits auxiliary
  streams.  It is not an expert unless it exposes a causal distribution over
  the original next byte.
* **Route:** an archive candidate assembled from one or more of those pieces.
  CIXG's route table is at `rust/cix-native/src/selection.rs:10` and dispatch is
  at `rust/cix-native/src/main.rs:1087`.
* **Backend:** a substream coder selected independently of routes 2--7.  The
  implementation itself says these are not predictor-specific coders
  (`rust/cix-native/src/selection.rs:51`).

## Eligible causal probability sources

| Candidate | Observes and state | Unit and distribution | Adaptive / replay | Internal mixing | Audit status |
| --- | --- | --- | --- | --- | --- |
| Adaptive multinomial (CIXG substream; order 0, with a general hashed-context implementation) | Counts and Fenwick tree per order-0 or causal suffix-hash bucket; preceding bytes seed the tail. | **Byte.** Exact Laplace-smoothed integer interval: mass `2*count[x]+1`, total `2*seen+256`; normalized over 256 symbols. | Adaptive after each byte; the decoder constructs the same bucket and calls the same update. | No. | **Eligible.** Small, clean first trace expert.  The interval and update are `rust/cix-native/src/adaptive.rs:26`, `rust/cix-native/src/adaptive.rs:34`; causal encode order is `:147`. |
| PPM (CIXG route 8) | Bounded preceding-byte history; per-context symbol counts; exclusion set; optional SEE escape state. | **Sequential byte coding path, not yet a verified normalized byte distribution.** Its realised-symbol interval can be measured causally, but the fixed encoder always reserves escape mass (`rust/cix-native/src/ppm.rs:75`, `:441`); when a context contains every remaining byte, that escape branch has no decodable byte outcome (`:141`). | Adaptive, deterministically primed from prefix history and updated after the symbol. | PPM's back-off and exclusion are internal hierarchical composition, not a separately exposed cross-model mixture. | **Conditional / pending normalization audit.** Trace the full escape/hit/fallback path and its total reachable-byte mass at every position. It may enter the common log-loss comparison only if that audit establishes normalization (or if the interface explicitly admits an abort outcome and reports it separately). Do not silently renormalize realised-byte masses. The causal coding loop is `rust/cix-native/src/ppm.rs:417`; SEE variant begins `:473`. |
| FixedMix (CIXG route 9) | Thirteen bit-context pattern tables, six lag bytes (1,2,4,8,16,32), a four-byte match table, per-bit reliabilities, weights, bias, and bounded history. | **Bit.** Integer probability for each next bit, conditioned on preceding target-byte bits; next-byte probability is the product of eight conditional probabilities. | Fully adaptive and decoder-replayable through deterministic integer state/update. | **Yes.** It already combines its bit experts with a learned fixed-point context mixer. | **Eligible as one composite byte expert**, initially. It is also the best source for a later *internal* decomposition audit, but its component bit predictions must not be presented as independent byte experts without their shared conditional-bit semantics. The current CIXG route calls the non-recurrence encoder (`rust/cix-native/src/main.rs:1104`). Probability assembly `rust/cix-native/src/fixedmix.rs:277`; updates `:310`; causal byte loop `:412`. |
| Legacy context-expert route (CIXM6 mode 17) | Parallel count tables for byte-context orders (orders include 0); decayed cumulative log losses select one order using only prior symbols. | **Byte.** Each selected table gives additive-one normalized byte frequencies. | Adaptive and decoder-replayable; bounded contexts. | **Route-level causal selection, not a mixture.** All tables are updated, but the lowest prior decayed-loss expert alone assigns the code interval. | **Eligible only if the trace instrument supports the frozen CIXM6 mode independently.** It is valuable as a switching-expert comparator and for exposing its constituent order experts. Selection occurs before target coding at `rust/cix-native/src/expertmix.rs:155`; all-expert update follows at `:209`. |

### Recommended first extraction set

1. **Adaptive order-0** (and, separately, an explicitly configured order-1
   hashed-bucket instance if it is materialized by the intended research
   harness): exact byte probabilities are direct integer ratios.
2. **PPM fixed variant:** first expose the exact escape chain and calculate its
   reachable-byte mass at every position, then `observe(symbol)` mirrors
   `observe_from`.  It is not an eligible common-distribution expert unless
   this quantifies and resolves the impossible-escape mass without changing
   the model.
3. **FixedMix composite:** expose the eight causal bit probabilities and record
   their product for the realised byte.  Keep the internal component vector as
   diagnostics, not independent externally mixed experts in phase one.
4. **CIXM6 context-expert orders and its selected route:** include only when
   the CIXM6 decoder/encoder path is in the instrument build; trace each order
   plus the existing loss-selected choice.  This supplies the requested
   switching control without inventing a new selection scheme.

Adaptive, FixedMix, and context-expert can be queried before `observe`, have
normalized distributions, and have reconstructible state.  PPM must remain a
separately labelled causal coding-path trace until the stated normalization
audit passes.  Adaptive and FixedMix are sufficient for a minimal CIXG-focused
common-distribution audit; PPM can contribute a separate diagnostic in the
same run.  This is an extraction recommendation only, not a proposal to wire
a new archive route.

## Existing native mechanisms that are not eligible byte experts

| Mechanism | Classification and reason for exclusion from the common next-byte audit |
| --- | --- |
| Arithmetic/range coder (`rank::ArithmeticEncoder`) | **Coder.** It receives `(low, high, total)` from a model; it does not choose probabilities.  See `rust/cix-native/src/adaptive.rs:163` for the division of responsibility. |
| Count-range, Huffman, deflate, hybrid, and `cix` nested backends | **Backends/coders.** The route/backend matrix confirms that these can encode the same transformed substreams (`rust/cix-native/src/selection.rs:101`).  They do not expose a common causal forecast of the original next byte. |
| Composition/type-class rank coding | **Block/count model, unavailable for this audit.** It codes a sequence conditional on a whole-tile or whole-block count vector, which is known by the encoder from the target block and serialized/recovered before rank decoding.  That is valid coding with paid side information but not a `P(x_t | x_<t)` source.  The rank module identifies itself as type-class rank coding at `rust/cix-native/src/rank.rs:1`. |
| Runs / sparse runs | **Representation route.** It first discovers runs/positions and encodes values, lengths, and positions as substreams.  Future run extent and occurrence positions prevent a faithful original-next-byte distribution.  Native mode encoders are `rust/cix-native/src/sparse_runs.rs:595` and `:628`. |
| LZ / phrase | **Parser/representation route.** The CIXG parser emits four materialized streams after parsing a bounded block (`rust/cix-native/src/fast_lz.rs:98`).  Parser search and token choice are not an exposed normalized original-byte distribution; a match signal may later be a causal *feature* if separately specified. |
| Predictor residual, stride/periodic residual, record periodic | **Transform/feature-only.** These form residual bytes using prior positions, then hand residual streams to a backend (`rust/cix-native/src/main.rs:1099` and `:1101`).  Their residual coder has no existing mapping back to a probability over the original byte.  Period/mode search is route selection. |
| BWT | **Transform route, non-causal in original order.** BWT is computed over the block before the transformed stream is coded (`rust/cix-native/src/main.rs:1100`); BWT-domain contexts cannot be called a causal distribution for original `x_t`. |
| Transform chain, numeric, wavelet, bitplane | **Transforms/representations.** They model transformed values, planes, or description streams and may use adaptive/range components internally, but no code currently exposes an original-byte next-symbol distribution.  Chain explicitly documents itself as a transform-chain representation (`rust/cix-native/src/chain.rs:1`); numeric has local adaptive subcoding (`rust/cix-native/src/numeric.rs:133`) but is not a causal original-byte expert. |
| Histogram/count-vector metadata | **Model description / side information.** It describes global counts rather than predicting next bytes causally.  Native code calls it count-vector histogram type classes (`rust/cix-native/src/histogram.rs:1`). |
| Persistent zstd and direct external codecs | **Backend / opaque route.** CIXZ1 compares complete raw, persistent-zstd, and nested-CIXG candidates by region (`rust/cix-native/src/streaming_backend.rs:483`); it does not expose zstd's next-byte probabilities.  External ZPAQ/libbsc are likewise not an in-process common prediction interface. |
| Whole-input portfolio and per-region CIXZ1 selection | **Portfolio/local routing.** Finished candidate sizes choose a route after candidate construction, rather than combine same-symbol probabilities.  CIXZ1 describes its frame selection as complete candidate selection (`rust/cix-native/src/streaming_backend.rs:389`). |

## Retained Python code: audit boundary

The Python tree is retained reference/research implementation, not evidence
that its routes are present as current native predictive experts.  Its causal
counterparts corroborate the native classifications: adaptive (`cix/adaptive.py:36`),
PPM (`cix/ppm.py:677`), fixed bit mix (`cix/fixedmix.py:134`), and legacy
loss-selected context experts (`cix/expertmix.py:124`).  `cix/ctw.py` contains
a CTW probability implementation (`cix/ctw.py:74`), but no current native
CIX route dispatches CTW (`rust/cix-native/src/main.rs:1094`); classify it as
**historical/research-only, excluded from the first native inventory**.  The
same applies to Python-only mixer variants until a frozen, decoder-reproducible
native implementation is identified.

## Consequences for the trace design

The common interface can be exact without changing production behavior:

```
expert.predict(history, target_byte_prefix?) -> integer distribution or
                                              conditional bit probabilities
expert.observe(actual_byte)
```

For a normalized byte expert, log loss is `-log2(mass[actual] / total)`.  For
FixedMix, it is the sum of the eight `-log2(P(bit_k | history, preceding
bits))` terms.  PPM's arithmetic interval cost must be recorded separately
until its reachable-byte mass is exactly one; its unnormalised code-path cost
must never be compared as a common-distribution log loss.  The trace must
invoke prediction before each update, preserve the precise integer state where
available, and identify PPM's complete escape path.  It must not derive a byte
forecast from completed parse tokens, block counts, BWT order, an archive-size
probe, or a selected finished route.

The inventory also establishes a useful separation for the later report:

* FixedMix is **already an internally mixed predictor**.  The proposed audit
  tests whether it, PPM, adaptive, and (where supported) context-expert models
  have additional complementary *same-byte* information.
* CIXM6 context experts already implement **causal loss-selected routing**;
  their individual orders form a natural existing switching baseline.
* No existing route name alone licenses calling LZ, BWT, counts, transforms,
  range coding, or the portfolio an expert.

## Audit constraints preserved

This inventory does not reopen the closed numeric structural-composition
branch, alter production CIX, activate actions, obtain data, start Sites/Hutter,
or start broad benchmarking.  The next authorized work is an isolated trace
instrument and synthetic validation, followed by the existing
Canterbury/Calgary/Artificial qualification order.

## FixedMix recurrence variants: available, but not the current CIXG route

The native API also contains a recurrence-enabled FixedMix variant.  The
corrected v3 constructor uses `RecurrenceMode::CorrectV3` and
`Predictor::new_saturated` (`rust/cix-native/src/fixedmix.rs:611`, `:629`),
whereas `encode_with_legacy_recurrence_eta` retains the historical v2
lookup-after-observe behaviour (`:638`, `:657`).  The latter is a preserved
legacy bug: its feature lookup collapses to distance one, as the source itself
records (`:257`).  Neither recurrence variant is dispatched by the present
CIXG route 9, which invokes `encode_with_history_eta` (`rust/cix-native/src/main.rs:1104`).

Consequently, the corrected v3 recurrence signal is **implemented and
potentially audit-available**, but it must be called out as an untraced,
non-route configuration until the isolated instrument explicitly configures,
validates, and traces it.  It must not be reported as absent, nor merged with
the recurrence-disabled current-route FixedMix result.  V2 remains
historical-only and unsuitable as evidence for a prospective causal signal.
