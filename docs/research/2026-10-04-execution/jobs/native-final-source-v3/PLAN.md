# Native final source v3 plan

This is the smallest current-source native quality recipe after the CLI alias,
ZPAQ watchdog, header, and CMake changes. Root dispatches it only after the
checkout is stable and has written the required `cix-native-quality-scope-v1`
record. The record is a preflight receipt, outside this recipe's ownership: it
must say that the reusable cache was archived and verified, pruning completed,
and the shared decimal 4 GB work ceiling remains admitted. It must admit at
least 720,000,000 bytes of new work; the helper independently measures the
shared work allocation with `du` before creating its work child and rejects a
stale record or any allocation that would exceed 4 GB with that cap. The helper refuses
to start without it.

This continuation never materialises or reformats source. It reuses only the
immutable v2 exported `cix-0.1.0` workspace after verifying v2’s persisted
receipt records an all-workspace format pass, and verifying the v2 native,
workspace-lock, and normalized export-member hashes before work begins and
after it completes. It copies the retained qualified workspace `Cargo.lock` only after comparing
its complete TOML package array with the current native lock: the sole allowed
extra package is local `cix-portable`. It also records the current native and
portable workspace manifests. The helper runs later Cargo commands with
`--locked --offline`; it never regenerates or reselects dependencies. It hashes
every regular native snapshot file and the export tool’s normalized member-hash
manifest before the checks and again at the end. It records the selected-provider closure hash as an immutable input,
but these focused native tests do not claim to exercise provider runtime
selection.

The quality scope resumes after the recorded v2 `cargo fmt --all --check` pass: it runs all-target
Clippy with warnings denied, a current `release-lto` build of `cix`, `uncix`,
and `cixcat`, then serial `zpaq_backend`, the direct
`cli::tests::program_name_normalization_is_platform_specific` unit test,
`full_engine_constraints`, and `cli_smoke` tests. The ZPAQ target is the bounded libzpaq envelope test. The direct unit test
covers Windows decoder-program basename normalization; `full_engine_constraints`
covers numeric effort spellings including `-2`, `-6`, and `-8`; `cli_smoke`
covers ordinary pipe and option-terminator compatibility. This neither repeats the
large full-library suite nor runs the broad CLI archive oracle. The binary phase
uses the optimized `release-lto` profile. The focused `cargo test` phases
deliberately use Cargo's default test profile with debug information disabled;
they are behavioral regression checks, not optimized runtime measurements.

The retained `distribution-engineering-v4/target` remains immutable evidence.
The helper hashes it before and after, then copies it into its new work child
with `cp -a --reflink=auto` and rejects any hardlink overlap with the original.
Cargo uses only that copied target. The installed codec SDK library files
provided to the linker environment are individually hashed before and after. The helper samples all new job work every
0.2 seconds and terminates the phase process group above 720,000,000 bytes.
That cap includes the allowlisted snapshot, copied target, artifacts, and logs;
it is below 700 MiB. The root quality-scope admission must establish that the
existing shared work plus this 720 MB maximum is below the decimal 4 GB ceiling
before dispatch. Four compile jobs, serial tests, disabled incremental
compilation, and disabled disposable debug information bound the workload. The
declared peak is 12 GB RAM, four scheduled CPUs (8, 10, 12, 14), no swap, 4 GB
shared work, and 30 minutes wall time.

A passing receipt establishes only the named snapshot quality, binary-build,
and focused test evidence. It does not establish provider closure, distribution
packaging, Windows portability, or final RC acceptance.
