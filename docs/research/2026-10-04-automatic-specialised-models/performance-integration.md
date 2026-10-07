# Portfolio-26 integration performance audit

Read-only audit before the authorised Silesia pass. The historical additive chain retains generic candidates plus ELF joint-discount/section, chemical geometry/hydrogen, database, grid/volume, and PAQ candidates. `competitive_joint_discount_v26` has a fresh ELF path; its certificate/cache path is research-only and cannot enter production.

## Exact opportunities

1. **Share per-input validated recognizers.** `competitive_chemical.recognizes(data)` is called by the chemical candidate and again by `competitive_hydrogen.additions`, reparsing the same bounded SDF prefix. Database/grid wrapper layers similarly re-enter parent recognizers. An integrated runtime can evaluate each pure bounded recognizer once and pass a typed result to dependent candidates. It preserves candidates for arbitrary bytes when the result is held only for that encode, never keyed by path, filename, corpus, or hash.

2. **Use an incumbent prefix cap only for append-only frame writers.** Historical additions return materialized byte frames and compare `len(candidate) < len(frame)`. A specialist with an explicit self-contained append-only writer may stop once emitted bytes exceed the strict incumbent: it cannot win. Equality must complete to preserve ties, and an abort must be a distinct omission. This cannot be assumed for current PAQ subprocesses or transforms that materialize full payloads first.

## No safe candidate reduction

Chemical geometry/hydrogen variants, database modes 0..4, grid feedback/integer modes, and generic/native route/backend settings produce different complete frames. Dropping one based on typical results is a heuristic and is not acceptable. Current historical Python candidates have no existing incumbent limit or emitted-prefix signal. Resource admission must preflight source, transform, candidate output, decoder state, subprocess working set and temporary space; an infeasible candidate is a recorded omission and generic fallback remains eligible.

## Measurement-path reductions

`benchmarks/competitive_cli.py` currently calls `codec.decode(output)` after every encode before writing the archive, while reporting `seconds` captured before that verification. The authorised pass also requires an independently timed fresh-process archive-only decode. Using this CLI would therefore perform two full decodes and label only the first encode portion as encoding time. Historical Dickens PAQ `-9L` decode cost is about 2,970 seconds, making this a material throughput and accounting error.

Extract an encode-only runtime entry for the pass. Keep per-transform correctness checks and focused integration validation, then perform exactly one independently timed final archive-only decode for the selected complete stream. This removes duplicate full verification rather than verification itself.

The MR ledger establishes another narrow exact reduction: the 1,671,099-byte CIXI frame and portfolio26's 1,671,101-byte CIXV frame share the recorded 1,668,279-byte JXL payload and differ only by a two-byte envelope. Where identical input, backend, options, and payload identity are established in the current encode, compare the two complete envelopes without re-running JXL. Do not generalize this to merely similar images or unproven payload equality.

## Required integration checks

Freeze the ordered registry, recognizer graph, resource formulae and source/binary identities. Prove shared versus standalone recognizers agree on valid, malformed, renamed and extensionless fixtures; prove cache/certificate paths are unreachable; and prove capped versus uncapped selected archive/restoration equality for every append-only runner. Record candidate starts, completed frames, prefix/resource omissions, selected complete bytes, and independent restoration.

Recommendation: implement only shared per-input recognizers and explicit append-only incumbent caps. Retain all algorithms/settings until equivalence evidence exists.
