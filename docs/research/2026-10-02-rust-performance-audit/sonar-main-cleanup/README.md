# Main CLI cleanup

## Scope

This bounded cleanup starts from `9214e2f8b80a16009986af56dd3de242fd26651e`.
It changes only `rust/cix-native/src/main.rs` and this evidence directory.

The high-complexity command parser is split into default construction, program
mode detection, option classification, value assignment, flag assignment, and
help/version handling. `run` now invokes small validation groups in the same
existing order before it selects the output path or encoder. The encoder,
decoder, route selection, frame ordering, atomic output path, and cancellation
paths were not changed.

## Validation

The final source compiled with the exact stable-toolchain binaries at
`/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/`.
The build and all CLI checks ran in separate user systemd services with
`MemoryMax=1G`, `MemorySwapMax=0`, and `CPUAffinity=14`; each service read back
its own cgroup limits. The build service captured Cargo and Rustc descendants
on CPU 14 in that cgroup, reached a 684.9 MiB service memory peak, and had a
zero-byte swap peak.

A 1,048,620-byte fixture was encoded with the unmodified `9214e2f8` binary and
decoded by the final binary; the final binary's archive was decoded by the
unmodified binary. Both archives were byte-identical, and both restored files
matched the fixture SHA-256. The focused CLI matrix returned exit 2 without a
named output for invalid decoder threads, decoder route, incompatible profile
and level, missing option value, and unsupported option.

The local scanner was unable to query its configured localhost server, which
returned HTTP 404. It therefore provides no final server-side issue count.

See `results.json` for hashes and exact command outcomes.
