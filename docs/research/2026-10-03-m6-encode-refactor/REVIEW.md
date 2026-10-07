# CIXM6 encoder mechanical-refactor review

## Scope and source identity

* Original source: `0b36c64dd` (`Simplify fixedmix table helpers without changing model state`).
* Immediate inherited partial-refactor baseline: `a5c491081`.
* Candidate: the uncommitted, scoped `rust/cix-native/src/main.rs` change in
  `/home/user/src/cix-sonar-main-encode-m6`.
* Scope is limited to `encode_m6`, its private M6 helpers, and this packet.
  No route, model, candidate order, tie rule, memory admission, deadline, or
  decode logic was changed.

`M6TrialContext` borrows the selection, source/history, effort, available
memory, and omission set. It lets the extracted candidate-family helpers retain
their original order without a high-arity helper interface.

Identity readbacks: original tree `523bf93f41e2992ebd647167310949cad3eda7ea`;
inherited-partial tree `34479d5298315dab4f513b019b0e6cff1f55cbab`;
candidate `main.rs` blob `259774660d41b78e149bc81ef79f961ccd521e91`.
The complete original-to-candidate scoped patch is exported at
`/tmp/cix-m6-net-0b36-relative.patch`.

### Rebuild assembly receipt

The candidate is assembled from the original `0b36c64dd` checkout plus the
source-only patch `/tmp/cix-m6-source-net-0b36.patch` (22,112 bytes; SHA-256
`6f28cdd2624d4a1d34f328793cfbfa6d3ed46c70b6931950836b57550f036cd3`).
The resulting uncommitted `main.rs` has SHA-256
`1e72ea5d69f09a16d92b7d8c76b1fdda33b5b48e8a69b5a6270861028bd50db8`.
The absolute toolchain reports `rustc 1.98.1 (48a229cea 2026-09-01)` and
`cargo 1.98.1 (797e8a9bc 2026-08-05)`.

## Builds and resource evidence

All final evidence used the stable toolchain by absolute path:

```
RUSTC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc
RUSTDOC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustdoc
/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo
```

The final original and candidate builds ran as system units with `User=user`,
`AllowedCPUs=12`, `MemoryMax=1G`, and `MemorySwapMax=0`. The readback inside
each actual build unit was:

```
cgroup=/system.slice/cix-m6-*-cpu12.service
memory.max=1073741824
memory.swap.max=0
cpuset.cpus.effective=12
```

`cargo build --release` completed for original and candidate. The candidate
also passed `cargo check --release --bin cix` and
`cargo test --release m6_rice_tests`. Existing warnings remain unsuppressed;
they are existing dead-code and vendored-C++ warnings, with no new warning
suppression in this change.

Earlier `a5c491081` supplemental checks used CPUs 1-2 before the CPU12
assignment was clarified. They establish only functional parity and are not
resource-policy-qualified. The final checks below are CPU12-qualified.
One later cache-warm build observation accidentally overlapped original and
candidate services on CPU12; it is excluded from the evidence. The sequential
CPU12 original/candidate builds and the CPU12 parity/test units are the receipts
reported here.

## CPU12 parity and reciprocal decoding

Original and candidate used identical commands: `--format cixm6`, the stated
block size, `--fast` / default / `--best`, and `-c`. For every row the archive
bytes and stderr output were identical; the candidate decoder restored
the original archive and the original decoder restored the candidate archive.

| fixture | bytes / block | FAST SHA-256 | default SHA-256 | BEST SHA-256 |
| --- | --- | --- | --- | --- |
| sparse | 512 / 512 | `8ecdabd7840448964e57cb1efbbe1e0343c142fb137ffbaa84c67676c4653871` | same | same |
| periodic ASCII | 512 / 512 | `b3f8be5bbfc57a1b416dc28b13636f0cffa75b14da78362fa71db76bdb991916` | `915cfbf574d0de8e7a7bc23b778a4c5c2b426b2d6dcda3c2e9f8df07119780f6` | `0e09a527e8d7a786cea7b32905776b929389215b184c2e7cfc74397e29c00d46` |
| numeric ASCII | 512 / 512 | `6205173b72b3df720afb4c1f52eaa9096248210b86ad84813721e76adbfc6226` | `65c96c7e12444b82f46d5f9973562688f217eb339f3f3c820b9fd5f74bac91f4` | same as default |
| periodic, four blocks | 1024 / 256 | `672ecb45b8034b019ce01af29b94ee38cc888602cfed66290cee589d2f54e5a3` | `1fd6c350b5147c592161dbbeeff264c59ee9eead89fe86059d0d205e1ea11865` | same as default |

The multi-block fixture exercises history, the recent-block queue, and
persistent-state observation across four frames. A truncated candidate archive
was rejected by the candidate decoder.

### Raw CPU12 runner receipt

The following is stdout from the receipt revalidation service, which hashed
and compared existing outputs and ran one truncated decode. The 12 encoder
pairs and reciprocal decodes ran earlier in
`cix-m6-final-parity-cpu12.service`, launched with CPU12, 1 GiB memory and
zero swap. Those direct native children inherit the generation service
constraints; neither binary independently recorded its own cgroup or affinity.
This packet does not claim independently sampled child resource enforcement.

```
Running as unit: cix-m6-receipt-parity-cpu12.service
cgroup=/system.slice/cix-m6-receipt-parity-cpu12.service
memory.max=1073741824
memory.swap.max=0
cpuset.cpus.effective=12
e9d7307344798a4a4f78a20e392968b18ec3f98cc9a3c7dd719f7569a9c37de3  original/cix
61369b6fd2c34c7b744fce49ba0d5b6c3eaf3e750a629ecf79405dd46f6e7768  original/uncix
92ff408f7d39eec5520d82b80fa1c459587018076435338f64fb4a7a79f8da4b  candidate/cix
1670a851152a8beac033bff192c702dd54a611cf8327300efb44d365f701a856  candidate/uncix
PASS sparse-512 fast/default/best
PASS periodic-512 fast/default/best
PASS numeric-512 fast/default/best
PASS multiblock-1024 fast/default/best
PASS truncated-rejected
Finished with result: success
Main processes terminated with: code=exited/status=0
Service runtime: 44ms
CPU time consumed: 40ms
Memory peak: 1.6M
Memory swap peak: 0B
```

The exact runner form for builds, checking, tests, and parity is
`sudo -n systemd-run --uid=user --property=CPUAccounting=yes
--property=AllowedCPUs=12 --property=MemoryAccounting=yes
--property=MemoryMax=1G --property=MemorySwapMax=0 --wait --pipe`, followed
by `/bin/bash -lc` with the absolute Rust paths above. The inner runner first
executes `awk -F: '$1==0 {print $3}' /proc/self/cgroup`, then reads
`memory.max`, `memory.swap.max`, and `cpuset.cpus.effective` below that cgroup.
It ran `cargo build --release --bin cix --bin uncix` against the original and
candidate target directories, `cargo check --release --bin cix`, and
`cargo test --release m6_rice_tests`; each completed successfully. Build
warnings were the pre-existing vendored C++ and dead-code warnings and were
not suppressed.

The raw focused-test receipt additionally recorded the following successful
test executions (the same runner readback was `memory.max=1073741824`,
`memory.swap.max=0`, `cpuset.cpus.effective=12`):

```
test cli::m6_rice_tests::rice_accepts_usize_max_and_rejects_high_quotient ... ok
test m6_rice_tests::rice_accepts_usize_max_and_rejects_high_quotient ... ok
test m6_rice_tests::rice_accepts_usize_max_and_rejects_high_quotient ... ok
test m6_rice_tests::rice_accepts_usize_max_and_rejects_high_quotient ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured
Finished with result: success
Main processes terminated with: code=exited/status=0
```

## Review handoff

Before root commit, export the scoped net patch against the original source:

```
git diff 0b36c64dd -- rust/cix-native/src/main.rs \
  docs/research/2026-10-03-m6-encode-refactor/
```

The working-tree candidate binary hash is intentionally distinct from the
original binary hash because Rust code layout changed. Archive bytes are the
semantic parity check.
