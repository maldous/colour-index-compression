# Native integration design — read-only assessment

## Finding

The restored 0.1 distribution already has two safe archive families for an
automatic candidate to return: a normal native CIX archive (`CIXG1`, `CIXG2`,
`CIXM6`, or `CIXF1`) and a complete direct-backend envelope (`CIXB1`). A new
outer wrapper is neither needed nor desirable. The decoder dispatches these
magics before route decoding and checks exact consumption, declared lengths,
memory admission and integrity checks appropriate to each family.

A specialised candidate must therefore be an *encoder-side candidate adapter*
that returns one complete archive in an existing family, with its own declared
decoder. It must not return raw model bytes labelled by a heuristic, and the
runtime selector must not use a filename, corpus name, hash, or saved stream.
The safe generic policy is: cheaply inspect only the supplied bytes; admit a
candidate by bounded structural evidence and effort/memory policy; materialise
only admitted candidates; select the smallest complete archive; otherwise
retain the always available CIXG raw/native path.

## Existing routing

| Facility | Current role | Integration consequence |
| --- | --- | --- |
| CIXG1/CIXG2 | framed native block stream; route/substream IDs live inside frames | Add a new native route only with a versioned route ID and decoder implementation. Do not overload an existing ID. |
| CIXM6/CIXF1 | native whole/persistent container plus optional filename footer | Existing decoder dispatch is safe, but these are not a generic place to place arbitrary external payloads. |
| CIXB1 | complete direct-backend archive: backend/profile IDs, source length, payload length and SHA-256 | Preferred family for a specialised one-shot backend already able to decode itself under stated bounds. Extend its descriptor/decoder pair only. |
| `portfolio_auto` | BEST-only whole-input selector across a complete CIXG2 archive and configured CIXB1 candidates | Natural location for bounded specialised whole-input admission, subject to the same named-file, memory and effort gates. |
| CIXG streaming selection | block-local native routes and raw fallback | Keep this path for stdin, streaming, large input, history, and constrained memory. A whole-input specialisation must not silently consume it. |

The decoder currently recognises `CIXM6`/`CIXM5`, `CIXB1`, and CIXG1/CIXG2
headers in distinct paths. Direct magic dispatch is sufficient only after the
encoder emits a complete family-valid archive. It cannot safely dispatch an
unframed specialised payload because there is no decoder identity, length
contract, or resource admission for it.

## Candidate catalog and budgets

The restored `external::best_candidates()` is a source-defined catalog of 14
configured CIXB1 descriptors. `portfolio_auto::eligible` admits whole-archive
BEST only for a readable named regular file, level at least 9, no streaming,
no history, no explicit portfolio/external override, CIXG1/CIXG2 format choice,
input at most `external::MAX_INPUT`, and memory sufficient for source, two
archive capacities and the native minimum. Its effort budget is 60/300/600/900
seconds by level plus a bounded size allowance; the incumbent maximum is a
complete archive, never a predictive estimate.

The new adapter should expose the same information as a CIXB1 descriptor:
stable candidate ID, profile/effort eligibility, encoder and decoder memory
estimates, input cap, complete-archive encoder, and decode admission. An
unsupported dependency, time expiry, or memory failure is an observed
omission recorded by `--explain`; it must not make the encode fail when the
generic fallback succeeds.

## T1 and prefix pruning

`portfolio_auto` preserves a competitive prefix guard through `CappedWriter`.
It snapshots the current complete incumbent size and stops a monotonically
growing candidate only once its serialized prefix exceeds that size; equality
is materialised and compared. The reason string is
`whole-archive candidate prefix cannot improve the incumbent`. This is a safe
T1 pruning rule because it uses a completed incumbent and an irreversible
output lower bound. Preserve it for any candidate that writes a single
monotone complete archive. Do not apply it to candidates that can buffer,
rewrite headers, or emit a non-monotone transformed representation without a
proved lower bound.

## Practical implementation sequence after approval

1. Restore each historical winner as a concrete bounded candidate with a
   generic byte-derived admission predicate; document candidates that cannot
   meet this condition as unavailable rather than guessing a detector.
2. Choose an existing container: CIXB1 for a complete self-decoding backend,
   CIXG2 only for a native route with a new versioned route decoder.
3. Add decoder admission and malformed/trailing-byte rejection before adding
   the encoder candidate to automatic selection.
4. Register candidates in an effort-specific catalog. Preserve CIXG streaming
   and current portfolio26 candidates, T1 prefix pruning, complete-size tie
   policy and omission reporting.
5. Freeze route catalog, source/dependency hashes, resource estimates and
   selected effort profile before the authorised Silesia pass. Measure complete
   archives and independent archive-only restore; report gaps rather than
   substituting historical outputs.

No implementation or benchmark run is authorised by this assessment.
