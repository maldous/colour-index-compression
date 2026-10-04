# Final Rust and optional-Python Sonar runner

`run.py prepare` derives its selection exclusively from a materialised public
CIX export's `EXPORT-MANIFEST.json`. It selects every CIX-owned `.rs` and
`.py` member: native Rust, portable Rust, bindings, and exported adapter/host
Python integrations. It writes a file-level exclusion ledger for preserved
vendor source and never selects the retired private `runtime/cix_runtime` tree.

`run.py run` reuses the authenticated stop, idle, WaveScheduler lock, physical
core lease, and verified no-swap slice checks from `tools/sonar-cxx/repair.py`.
It starts one language-enabled, pinned local server and serially scans native
Rust, portable Rust, and exported Python. It records active languages, indexed
files, issues, completed tasks, and quality gates. Both server and scanner use
read-only roots, bounded tmpfs, no Docker log driver, and bounded retained log
receipts. It refuses an empty index or a changed export-manifest identity.

The root scheduler must first generate fresh native and portable Clippy JSON
for the same exported workspace; this tool imports them but never runs Cargo.
No command in this directory is run by this preparation change.
