# One native Rust enwik9 full measurement

This protocol is one user-authorized local attempt on the retained canonical
1,000,000,000-byte `enwik9` input. Its SHA-256 is
`159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc`.
It is separate from the catalog study and preserves earlier cancelled work.

The controller first waits for the catalog run state to become `COMPLETE`. It
then obtains the same global WaveScheduler lock and CPU-16 physical-core lease
for a clean detached `d66739120c40fc409f2bf011b165389fc1062c2b` source build.
Each `cix` and `uncix` binary is built independently with Cargo offline,
locked, one job, `release-lto`, and `-C target-feature=+crt-static`. Dynamic
linkage, a failed build, or a failed package smoke test is terminal; there is
no dynamic fallback.

The smoke gate creates the static package, runs no-argument `comp9a` and then
`decomp9` on a small generated input, hides that input from the decoder, and
checks exact bytes. Only then is the immutable full manifest created. The
full job copies the source once in 1 MiB chunks into the neutral `enwik9`
filename while hashing it, and executes the package's actual compiled commands:

```text
comp9a  -> cix --best --threads 1 --verbose -o archive9.bhm enwik9
decomp9 -> cix -d -o data9 archive9.bhm
```

These commands use CIX's native 512 MiB default working-memory policy. There
are no route, backend, framing, block, history, memory, external-codec or
option-byte overrides. The fresh decoder receives the archive only; both the
retained source and its local copy are inaccessible. Exact full-size SHA-256
restoration is required.

The job uses CPU 16, a decimal 9 GB RSS cgroup cap, a 4 GB temporary-space cap,
no swap, and a 48-hour combined encode/decode ceiling. Build and smoke phases
are capped at 1,200 and 300 seconds. Progress records are written every 30
seconds. The final package is built only after exact reconstruction and counts
`S = 2 * length(cix9) + length(archive9.bhm)` with zero external option bytes.

Run only from the root-owned controller:

```bash
python3 benchmarks/hutter_rust_qualification.py --id rust-enwik9-v1 --prepare
python3 benchmarks/hutter_rust_qualification.py --id rust-enwik9-v1 --queue \
  --catalog-area docs/research/2026-10-02-rust-full-catalog/native-catalog-d667-v3
```

`--queue` persists while the catalog wave runs and then performs build, package,
smoke, manifest freeze, and the one full cell automatically. Results are always
labelled `LOCAL_FULL_MEASUREMENT_PENDING_ELIGIBILITY`. This is not an official
Hutter Prize score or submission: Geekbench 5 normalization, release/package
eligibility review, an OSI public source release, and submission authorization
remain absent. No Actions, publication, email, or site update is performed.
