# Matched BEST grammar v2 provenance erratum

Date: 2026-10-02

## Preserved records

This erratum leaves the frozen observations unchanged:

- `benchmark-work/rust-performance-audit/matched-best-grammar-v2/manifest.json`
- `benchmark-work/rust-performance-audit/matched-best-grammar-v2/results.json`
- `benchmark-work/rust-performance-audit/integrated-8865bfbcc/final/native-release.json`

The post-refactor release objects contain a stale inherited
`build_source_state` object naming revision `99f4f7319` and its dirty-state
hashes. That object matches the pre-refactor release and conflicts with the
post-refactor object's `source_revision`, `source_state` and artifact hashes.
It must not be used to identify the post-refactor build.

For the post-refactor release only, this erratum supersedes that legacy
`build_source_state` field with the following interpretation of the preserved
evidence:

- production revision:
  `8865bfbccba354b02920da86c7088c17e5f96aab`;
- clean Rust subtree object:
  `7360b401e85a3e9abf052e2d2bf14c7379fd79c7`, which independently equals
  `git rev-parse 8865bfbcc:rust/cix-native`;
- build profile: `release-lto`;
- stored build log:
  `benchmark-work/rust-performance-audit/integrated-colex-fixedmix-build.log`,
  SHA-256
  `d43f01d4a4d838ac0e12d14fcc6dece71fd7ef934d7e1d1ab4e6059336c556a0`;
- measured `cix` artifact SHA-256:
  `7ead367731b7a97035392473e54c59f55a937de7abc32b871c3028cec126a535`;
- measured `uncix` artifact SHA-256:
  `1a166665722c8f896e73ea0770b8ebd8a06d910f1501cad0474771debdd5e1f7`.

The artifact digests were independently read back from the stored binaries and
match both the release record and matched-probe manifest. The build log reaches
a successful `release-lto` completion. This is a reconstruction from the
preserved source guard, Git tree object, build log and artifact digests. It is
not a new observation of the original build and does not invent replacement
dirty-state hashes.

The pre-refactor artifact retains its originally recorded revision and dirty
source state without reinterpretation. All other frozen fields and result rows
retain their original meaning.

## Honest result scope

The probe contains three sequential, counterbalanced pairs on one 3,721-byte
Canterbury `grammar.lsp` input, pinned to CPU 8 with `--best --threads 1`.
Every run produced the same complete 1,096-byte archive. Both decoders restored
all six archives, for twelve fresh-process decodes, to the input SHA-256
`1b0805dfc0ae706b35aac2bb4e15f02485efd24dda5dbd29de7b2f84d1a88c15`.

Paired intervals below use a two-sided Student t interval with three pairs,
two degrees of freedom and `t = 4.30265`:

| Measure | Pre mean | Post mean | Mean reduction | Paired 95% CI for reduction |
| --- | ---: | ---: | ---: | ---: |
| Encode wall time | 44.977 s | 38.572 s | 6.405 s (14.2%) | -0.038 to 12.848 s |
| Encode CPU time | 44.937 s | 38.250 s | 6.687 s (14.9%) | 0.904 to 12.469 s |
| Peak RSS | 100,426.7 KiB | 100,082.7 KiB | 344.0 KiB (0.34%) | 136.5 to 551.5 KiB |

All three post-refactor observations were faster, but the absolute wall-time
interval narrowly includes zero because three pairs do not resolve the observed
run-to-run variance. The CPU interval supports a reduction on this focused
input. The RSS difference is small enough that it should be treated as an
observation rather than a practical memory improvement.

Decode CPU values round to 0.00 seconds and decode wall values range from 0.01
to 0.67 seconds. They establish exact compatibility, not a decode-throughput
comparison. The probe compares complete release artifacts and combines several
reviewed optimizations; it does not attribute the timing difference to any one
optimization and is not corpus-wide qualification.
