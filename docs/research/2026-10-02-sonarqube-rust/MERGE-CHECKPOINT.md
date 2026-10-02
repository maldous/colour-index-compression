# First reviewed Sonar refactor checkpoint

The first consolidated patch covers fourteen Rust source files. It was applied
before any throughput/deadline optimization, as directed by the user.

Base: 4fd93df3673608067595829e23bf69f0be3c6144 (Rust source unchanged through99f4).
Reviewed source diff SHA-256:
`bbc9269402c011ab8762057758efdee9e5015d7fd895bcd376954946fa21b634`.

The independent adversarial review found two regressions and required repair:

- BWT nonzero uint decoding now rejects values over254 before adding1. The
  direct255/usize::MAX and full-v3-frame regression passes.
- CIXZ1 releases a losing nested native archive before materializing the second
  synchronized Zstd payload, preserving the original buffer lifetime.

After repair, the adversary found no remaining merge-blocking semantic,
malformed-input or resource issue. Candidate order, strict size tie handling,
mathematical coding operations, framing, validation and CLI output precedence
remain unchanged. `git diff --check` and root `cargo check --locked` pass.

Completed focused worker evidence includes backend registry11/11, ZPAQ1/1,
selection6/6, transform2/2, BWT/LZ malformed/frozen fixtures7/7,
portfolio4/4, Huffman/coverage5/5, streaming unit6/6 and actual pipe7/7.
The new root malformed MAX regression passes separately. Full all-target tests
are still running in the isolated review checkout; no full-suite success is
claimed by this checkpoint.

This is a partial remediation checkpoint, not a zero-warning release. Initial
Sonar analysis reported75 cognitive-complexity findings; an intermediate scan
reported60. Unique compiler/Clippy diagnostics remain separately accounted for.
Additional workers are addressing remaining functions/warnings. Generated
Sonar reports containing local paths and scan credentials are excluded from
this source commit. A new scan and release qualification remain required.

The20-thread study was cancelled at the user's request after3 verified
Artificial checks, before any official-dataset result completed. The public
page uses46 previously verified Rust BEST results at d66739120, sorted by
percentage size difference against sourced references without external
pretraining/dictionaries. No incomplete archive is ranked. The next study is
four concurrent datasets with four threads per dataset, after code completion.
