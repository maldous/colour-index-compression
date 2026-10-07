# External BEST trial helper refactor

Source revision: `40d3520db63a7d54526cb22430b769e77cf601c9`.

## Change

`portfolio_auto::run_external_trials` was the remaining native Sonar
cognitive-complexity finding in this module. The change divides its work into
three helpers without changing the candidate registry, selection policy,
dependencies, or external-backend policy:

- `run_external_trial` retains the existing interruption check, aggregate
  source/incumbent memory calculation, admission rejection handling, one-shot
  encoding result classification, and evaluated-counter timing.
- `report_external_archive` retains the explain/verbose backend-version line.
- `validate_and_consider_external` retains decoder admission before complete
  archive validation and the strict-smaller incumbent replacement rule.

The disabled path still records exactly one incompatible-constraint omission
and does not inspect a backend. The enabled path still visits candidates in
`external::best_candidates()` registry order. Resource omissions and BSC/ZPAQ
candidate rejections remain omissions; interruption and other errors still
terminate selection.

## Qualification

Both commands used the direct stable Rust toolchain in a transient user
systemd scope with `CPUAffinity=18`, `MemoryMax=1G`, and `MemorySwapMax=0`.

| check | result | evidence |
| --- | --- | --- |
| `cargo check --lib --all-features` | pass, exit 0 | `cargo-check.raw` |
| `cargo test --test auto_best_portfolio named_best_compares_complete_archives_and_fresh_cli_decodes -- --exact` | pass, exit 0 | `auto-best-roundtrip.raw` |
| `cargo test --test backend_registry -- --test-threads=1` | 11 pass, exit 0 | `backend-registry.raw` |

The integration test uses a regular named source with `--best`, requires each
registered external candidate to be either reported as a complete candidate or
as an explicit omission, compares a selected CIXB1 archive to a direct
materialisation when an external candidate wins, and restores the selected
archive through a fresh `uncix` process. It passed in 76.02 seconds after the
test build. The scope reported no swap use and a 1.0 GiB peak during the
complete test process.

The registry test exercises every direct CIXB1 configuration, complete
encode/decode, corruption and truncation rejection, admission accounting, and
the explicit malformed-gzip expansion limit. It passed all 11 cases with no
swap use.

The raw command transcripts include pre-existing vendored C/C++ warnings; no
new Rust warning or error was emitted by this helper change.

## Parent/candidate parity

`parity/` compares the unmodified `40d3520db` parent binary with the helper
candidate built from the same revision plus this patch. Both independent builds
used the direct stable toolchain, CPU 18, `MemoryMax=1G`, and
`MemorySwapMax=0`. The raw logs record the actual native child cgroup and
`Cpus_allowed_list: 18`; the completed services report zero swap peak.

The deterministic generic record fixture is 8,161 bytes with SHA-256
`0c7bf4fe6d235ba41d6af67a6492d749592c3fb432e2e4122bf554522a44b5bc`.
Both invocations used:

```text
cix --best --threads 1 --memory 512MiB --verbose -k -f -o ARCHIVE INPUT
```

Both selected `cixm6:native-auto:block=16384` at 256 bytes. Their complete
archives compare byte-for-byte and share SHA-256
`997a2b69b49eef2d43b834e9047cefbf31613de8b242119ad0f86f9f678483f2`.
The parent `uncix` decoded the candidate archive and candidate `uncix` decoded
the parent archive; both restored the fixture byte-for-byte. Binary and dynamic
library hashes are recorded separately because the two Rust binaries are
expected to differ after the source refactor while their loaded external DSOs
are identical.

The BEST traces show successful complete CIXB1 candidates for gzip, bzip2, XZ,
Zstandard, Brotli, and BSC, with the high-memory XZ/Zstandard/ZPAQ profiles
explicitly omitted at the declared aggregate budget. A second 512-byte
deterministic high-entropy fixture records an external-candidate trace where
CIXM6 still wins at 532 bytes; the parent and candidate report identical
external candidate sizes and identical omission reasons. This establishes that
the enabled external loop still reaches backend materialisation and complete
candidate validation before the native incumbent remains selected.

| artifact | SHA-256 |
| --- | --- |
| `auto-best-roundtrip.raw` | `254c6acfd75e89d0171706452e2606cb6af6878ecbbe345629cc405b655b90c4` |
| `backend-registry.raw` | `0348ce63a632fd84b0f4725614fe3b6e767427fe9d581896f628b0c1e5a5df74` |
| `cargo-check.raw` | `32045ef6a4ea767664d7aea2546981181a838e985430cf29419e9b32a87353dc` |

The parity artifact hashes are listed in `parity/` and are intentionally kept
as raw receipts rather than reduced to a hand-transcribed summary.
