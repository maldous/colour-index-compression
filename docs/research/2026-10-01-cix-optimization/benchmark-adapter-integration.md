# Rust CIX benchmark-adapter integration

## Ordinary profiles

[`benchmarks/silesia_rust_client.py`](../../../benchmarks/silesia_rust_client.py) is the benchmark adapter for snapshotted `dist/cix` and `dist/uncix` binaries. It copies each executable into the cell work directory, verifies the copied SHA-256, and records the requested profile, normalized profile, expert overrides, exact command, and both binary stamps.

The normal commands intentionally measure CIX's own automatic choices:

| Requested profile | Normalized profile | Encode effort argument | Imposed route/container/resource settings |
|---|---|---|---|
| `fast` | `fast` | `--fast` | none |
| `default` | `default` | none | none |
| `best` | `best` | `--best` | none |

`current` is a legacy input label normalized to `default`; `size` is normalized to `best`. They exist only to read historical recipes. The adapter's option tests prove that normal DEFAULT has no implicit route, backend, format, block, memory, thread, or stream argument, and that explicit expert arguments are forwarded without hidden settings.

This means a new ordinary-profile study measures the binary defaults plus its automatic selector. It must not label the result as a fixed-format or fixed-resource comparison.

## Historical fixed recipes

Old matrix receipts are immutable evidence. Their profile labels and metadata describe the settings frozen at the time; changing the client does not modify those receipts or reinterpret their result rows.

The tracked legacy generator [`benchmarks/silesia_rust_native_matrix.py`](../../../benchmarks/silesia_rust_native_matrix.py) now forwards its own declared fixed expert controls on encode: format, one thread, block size, and memory. This preserves the intent of a newly generated instance of that historical fixed-settings matrix after the client stopped silently imposing those values. It is separate from an ordinary automatic-profile study. The untracked v3 generator and already frozen manifests are not changed by this integration note.

When preparing a new study, choose exactly one form:

1. **Actual auto profile:** use the adapter with only `--profile fast`, `--profile default`, or `--profile best`.
2. **Fixed mechanism/resource control:** declare every expert override in manifest configuration and adapter command, including format, route/backend where relevant, block size, memory, and thread count.

Do not create a hybrid record that calls an ordinary profile while metadata claims fixed values which the command did not pass.

## Evidence boundary

The ordinary-profile qualification records real default commands in [`profile evidence`](adversarial-parallel-evidence/cix-profile-qualification/profile-summary.json), and [`tests/test_rust_client_options.py`](../../../tests/test_rust_client_options.py) covers command construction. The adapter does not make a profile result a general Silesia result, select a package externally, or repair a frozen manifest. New measurements require a new experiment identity and the standard bounded scheduler declaration.

Decode discovers its container from archive bytes; the adapter omits encoding-only format, block, route, backend and worker controls when decoding. This keeps historical CIXM6 recipes compatible with the native auto decoder. Memory and streaming controls remain available for decoding.


## 2026-10-02 FAST release promotion

The normal `dist/` CLI and shared library now come from source release
`d66739120c40fc409f2bf011b165389fc1062c2b`. All four artifacts are byte-identical
to the frozen `d5e7d4ba` candidate used in the matched 33-pair CCA gate and the
MR measurements. The source revision and full hashes are in
`dist/native-release.json`; the earlier immutable `938e8805` baseline stays in
`benchmark-work/cix-qualified-release/final` for explicit controls.

`benchmarks/silesia_rust_client.py` already snapshots `dist/cix` and
`dist/uncix`, so subsequent newly frozen benchmark cells use the promoted
release without extra strategy flags. `cix_fast_opportunity.py` now also
uses `dist/` by default; use `--artifacts` to declare a historical control.
Existing receipts and source snapshots retain their original paths/identities.

The FAST update is not a size win: complete MR archives increase 3.45% while
local encode/decode wall time improves ~35×/~17×. Native BEST restores the
historical Python maximum MR result exactly, including archive bytes. The
[new ledger](../2026-10-02-fast-opportunity/README.md) separates codec-reference,
selector, source and complete-framing evidence. No benchmark workflow ran on
GitHub Actions.
