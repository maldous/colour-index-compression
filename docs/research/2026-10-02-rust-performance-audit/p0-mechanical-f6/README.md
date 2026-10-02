# P0 mechanical Rust cleanup — f6aa99c38

## Scope

This is an isolated, behaviour-preserving cleanup patch based on
`f6aa99c38344bb49dc575f166b25170e3063c540`
(`80550d4b4685ff9268277a4f54051ff13ff0a80d` tree).  The reviewed source
identity is that base plus the accompanying mechanical patch; it is not the
current canonical tree.  It changes only:

- `adaptive.rs`: elided needless named lifetime; idiomatic Fenwick low-bit and
  overflow-safe upper-midpoint expressions.
- `stateful.rs`: the matching Fenwick and midpoint expressions, plus a new
  two-block persistent-model encoder/independent-decoder restoration test.
- `huffman.rs`: fixed-size metadata chunking with an explicit malformed odd
  remainder error; idiomatic bit divisibility predicate.
- `record_periodic.rs`: idiomatic exact-divisibility predicate.
- `expertmix.rs`: overflow-safe ceiling halving using `u32::div_ceil`.
- `oracle.rs`: inclusive fixed-mix eta range pattern.

The compiler in this environment is stable Rust 1.98.1.  `cargo check`
confirmed that `isolate_lowest_one`, `is_multiple_of`, `div_ceil`, and
`as_chunks` are all available in the pinned toolchain.  The old midpoint
domains are `0..=255`; the new `lo + (hi - lo).div_ceil(2)` form retains the
same upper midpoint while avoiding intermediate addition.  The old expert-mix
addition could overflow at `u32::MAX`; `div_ceil(2)` gives the intended ceiling
halving without that intermediate overflow.

## Local validation and retained provenance

The launch recipe specified direct stable-toolchain paths, CPU 18,
`MemoryMax=1G`, and `MemorySwapMax=0` through user systemd units.  The raw
completed-pass logs retain the unit names and results, but their transient
unit property readbacks were not captured before systemd collected those
units.  Therefore CPU affinity, cgroup settings, and direct-toolchain use for
the successful check, focused tests, stateful test, and Clippy run are
**declared launch settings, not independently retained readbacks**.

The failed full-library unit remains queryable.  Its retained `systemctl show`
receipt in `raw/lib-1g-systemd-show.txt` proves its exact command, CPU 18,
1 GiB memory maximum, zero swap maximum, 1 GiB peak, and OOM result.  It is
the only run in this packet for which those resource properties are verified
after completion.

| Check | Result | Receipt |
| --- | --- | --- |
| `cargo check --lib --all-features` | pass | `raw/check.raw` |
| `cargo test --test codec_limits --test huffman --test oracle -- --test-threads=1` | pass: 17 tests | `raw/targeted.raw` |
| `cargo test --lib stateful::integer_overflow_tests -- --test-threads=1` | pass: 2 tests | `raw/stateful.raw` |
| `cargo clippy --lib --all-features --message-format=short` | pass; none from the six owned modules | `raw/clippy.raw` |

The targeted tests cover adaptive bounded-context round trip and cancellation,
Huffman round trip plus malformed/trailing/padding cases, and Oracle candidate
materialisation/restoration plus invalid eta.  The stateful test separately
models encoder and fresh decoder state, commits the first reconstructed block
to both, then verifies exact restoration of a second block using accumulated
history.  It also retains the existing maximum-varint malformed-input test.

The full `cargo test --lib -- --test-threads=1` run was allowed to continue
under the requested 1 GiB cgroup.  It passed the early chain fixture and later
tests through `streaming_backend::persistent_backend_rejects_corrupt_frame`,
then systemd ended it with `oom-kill` after 9m34s (1.0 GiB peak, no swap).
That is a resource-limited, incomplete result, not a test pass.  Its raw log
is retained as `raw/lib-1g.raw`; the focused successful tests above cover the
changed paths.

SHA-256 of the completed raw logs:

```text
9f7240cf3dd1d9420c71b516e29aaa0eab535a5902330035d2b76ff123a7729a  check.raw
60bab716390d4652acd08b3f45699e52c8716409ba3c30027881d481b7be15b7  targeted.raw
72293783fe364940ecfdb3063d9fcb4a81e9ea541f0c3ec36805b899713204c0  stateful.raw
d8673adf22ce6be7c9a27bc234c5ff1042be4c631eb0343a0f55a75a3962ec11  clippy.raw
62f5b9341c71e3f89eb632dd28b0f30e432302060a457195b2a7ce58a25920f0  lib-1g.raw
f348222f1ee71f10b0b54b7ac0197078f97ca881c21e40017bb9ae8dab13814c  lib-1g-systemd-show.txt
421dd228b6bec88a1e07bb35159c146a38437600b95942f7f407689e0d33c2b5  base-commit.txt
f4a919c7d1afb5803db12122d5623df2b2926dfbe7386baafe05709e82176c06  base-tree.txt
```

Vendor C/C++ warnings in the raw compiler logs are retained for provenance;
this patch does not modify vendored code.  The Clippy log still reports
unrelated first-party findings owned by other remediation batches, and two
existing duplicate-module architecture warnings for `adaptive.rs` and
`huffman.rs`; it contains no warning at a changed location in this patch.
