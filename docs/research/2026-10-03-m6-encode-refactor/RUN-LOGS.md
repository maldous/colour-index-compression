# CPU12 command receipts

These are text receipts only. Fixture input bytes, generated archives, and
binaries remain outside Git.

## Candidate check

Command executed without a shell pipeline around Cargo:

```sh
RUSTC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc \
RUSTDOC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustdoc \
/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo check \
  --release --bin cix --target-dir /tmp/cix-m6-final-target \
  >/tmp/cix-m6-final-check.stdout 2>/tmp/cix-m6-final-check.stderr
```

Raw runner output:

```text
Running as unit: cix-m6-final-check-unpiped-cpu12.service
cgroup=/system.slice/cix-m6-final-check-unpiped-cpu12.service
memory.max=1073741824
memory.swap.max=0
cpuset.cpus.effective=12
cargo-check-exit=0

warning: `cix-native` (bin "cix") generated 22 warnings
    Finished `release` profile [optimized] target(s) in 0.05s
Finished with result: success
Main processes terminated with: code=exited/status=0
Service runtime: 74ms
CPU time consumed: 44ms
Memory peak: 328.0K
Memory swap peak: 0B
```

## Candidate release build

Command executed without a shell pipeline around Cargo:

```sh
RUSTC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc \
RUSTDOC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustdoc \
/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo build \
  --release --bin cix --bin uncix --target-dir /tmp/cix-m6-final-target \
  >/tmp/cix-m6-final-build.stdout 2>/tmp/cix-m6-final-build.stderr
```

Raw runner output:

```text
Running as unit: cix-m6-final-build-unpiped-cpu12.service
cgroup=/system.slice/cix-m6-final-build-unpiped-cpu12.service
memory.max=1073741824
memory.swap.max=0
cpuset.cpus.effective=12
cargo-build-exit=0

warning: `cix-native` (bin "uncix") generated 22 warnings
warning: `cix-native` (bin "cix") generated 22 warnings (22 duplicates)
    Finished `release` profile [optimized] target(s) in 0.02s
Finished with result: success
Main processes terminated with: code=exited/status=0
Service runtime: 50ms
CPU time consumed: 45ms
Memory peak: 348.0K
Memory swap peak: 0B
```

## Focused M6 malformed-Rice test

The unpiped CPU12 runner `cix-m6-receipt-exact-test-cpu12.service` read
`memory.max=1073741824`, `memory.swap.max=0`, and
`cpuset.cpus.effective=12`. Cargo completed with exit status 0 and reported:

```text
test cli::m6_rice_tests::rice_accepts_usize_max_and_rejects_high_quotient ... ok
test m6_rice_tests::rice_accepts_usize_max_and_rejects_high_quotient ... ok
test m6_rice_tests::rice_accepts_usize_max_and_rejects_high_quotient ... ok
test m6_rice_tests::rice_accepts_usize_max_and_rejects_high_quotient ... ok
Finished with result: success
Main processes terminated with: code=exited/status=0
```
