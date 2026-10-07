# Final integrated hygiene scan preparation

These files are inputs to the root scheduler. Preparation is inert; the explicit
`schedule_scan.py` wrapper below acquires the shared lease before starting the scan.

After the root freezes the integrated source, run the following **under the root scheduler lease** and save every stdout/stderr stream as raw evidence. Replace angle-bracket paths only with scheduler-created paths under the final qualification evidence directory.

```bash
# Native source: first bind the fresh formatting and Clippy results.
cargo fmt --manifest-path /home/user/src/cix-0.1-distribution/Cargo.toml -- --check
cargo clippy --manifest-path /home/user/src/cix-0.1-distribution/Cargo.toml --all-targets --message-format=json -- -D warnings > <fresh-clippy-jsonl>

# Runtime source: static production-package receipt before its test stage.
python3 /home/user/src/colour-index-compression/runtime/tools/quality_check.py \
  --runtime /home/user/src/colour-index-compression/runtime/cix_runtime \
  --json <runtime-quality-receipt.json>
```

Use the established release Sonar harness as the implementation reference for the lease, cgroup, image-digest, token-lifecycle, and raw-report accounting. The root scheduler must adapt it to make three discrete projects from `final-scan-spec.json`:

- `cix-0.1-native-rust-final`: imports only the fresh Clippy JSON and scans Rust source/test paths. Vendor is excluded.
- `cix-0.1-runtime-python-final`: scans the complete retained runtime package, tools, and tests using Python 3.12. It cannot inherit the native Rust result.
- `cix-0.1-native-cpp-first-party-final`: scans only `src/zpaq_ffi.cpp` when the running Sonar server reports CFamily support and the same native build produces a compilation database/build-wrapper receipt. If unavailable, retain the C++ compiler diagnostic as a separate limitation; do not call the Rust result a C++ scan.

The locally available, pinned images at preparation time are listed in `final-scan-spec.json`. Verify the image IDs/digests again in the scheduler receipt and bind them to the frozen source manifest. The prior `sonar-release/run-v2` result belongs to source tree `bd28975a…`; it cannot qualify a later distribution tree or the Python runtime.

No Ruff, Black, Flake8, Pylint, Pyright, Clang-Tidy, or Cppcheck executable or cached wheel was found locally. Do not install/download any tool during final qualification without a new explicit scheduler decision.

## Root scheduler dispatch

The root scheduler invokes the one runnable wrapper. It uses `WaveScheduler` for the four physical-core leases and starts the scanner harness in a systemd slice that becomes Docker's cgroup parent. No inner wave lock is taken.

```bash
python3 docs/research/2026-10-04-automatic-specialised-models/hygiene/schedule_scan.py \
  --native-source /home/user/src/cix-0.1-distribution \
  --runtime-source /home/user/src/colour-index-compression/runtime \
  --clippy-json <fresh-clippy-jsonl> \
  --out <fresh-hygiene-evidence-directory> \
  [--compile-commands <fresh-native-compile-commands.json>]
```

The wrapper derives a new staged-source freeze manifest, takes the single global wave lock, leases the four physical cores, then creates a transient `.slice` with noninteractive `sudo -n`. It sets and reads back `MemoryMax=5 GiB`, `MemorySwapMax=0`, `AllowedCPUs=8,10,12,14`, and `CPUQuota=400%` on the slice itself before launching the harness as the workspace user with `sudo -n systemd-run --wait --pipe`. The harness requires that same `.slice` cgroup parent, uses local images only, gives its server 4 GiB and its one sequential scanner 1 GiB, and removes containers only after collecting scanner logs and task identifiers. Launch streams, slice receipt, compute-task, issue, and quality-gate evidence are retained on both success and failure.

C++ is scanned only when the server reports `cpp` support and the fresh compilation database is supplied; otherwise its non-scan reason is written to the manifest.

Final result: `run-5` reports zero Rust issues and zero Python issues. C++ was
not scanned because the local server lacks CFamily support. Earlier scan findings
and their remediation history are retained; no issue suppression was introduced.
