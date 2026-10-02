# Corrected local scan: ba4e19921

The frozen source scan completed without a Clippy parse error. The quality
gate still fails: **30 native complexity findings and 62 imported Clippy
findings**, 92 open findings total. Complexity decreased from the earlier
39, but imported argument-count warnings increased. Both raw exports contain
14 argument-count diagnostics; the higher imported count is not evidence that
this refactor introduced six such warnings. Cleanup is unfinished.

The complete normalized ledger contains 187 diagnostics. Scanner-unsupported
rules, compiler-only diagnostics and alias/example locations remain in raw
evidence even when not represented in the Sonar issue inventory. The manifest
records exact diagnostic/rule counts, source tree and evidence hashes. Rust
and Clippy were invoked from the toolchain directly; scanner/server computation
remained local Docker. No GitHub Actions or source-rule suppression was used.

This scan does not include the unmerged numeric refactor, does not prove
runtime correctness, and does not qualify vendor C/C++ or dependencies.
