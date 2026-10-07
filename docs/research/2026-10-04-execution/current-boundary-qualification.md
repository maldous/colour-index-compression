# Current boundary qualification continuation

Benchmark HOLD and RC51 remain open. These are focused correctness and analysis
receipts; none is a new corpus result, platform-support claim, or complete RC.

The common PAQ loader now uses the installed-provider filename rule and the
existing explicit-path loader. The immutable allowlisted source in
`jobs/paq-loader-freeze-v1/receipt.json` passed formatting, all-target Clippy with
warnings denied, eight worker tests, and the real installed-provider archive
fixture using a freshly built CIX executable. All four retained PAQ library
identities and the JXL bridge were bound before and after the check. See
`jobs/paq-loader-slice1-v1/receipt.json`. This was a development-profile check,
not a final optimized build or non-Linux qualification.

The Node null-wrapper check is now an explicit conditional. The optimized
addon built in v2; its original test expected the wrong lifecycle error. V3
reused exactly that binary and corrected the expectations to `context is
disposed` and `stream is disposed`; the contract passed. Bad receivers still
reject without promising a particular engine message. These tests do not
explicitly reach the internal null-wrapper branch. V1 failed on an invalid
lease-marker override before compilation; both failed attempts remain.

The SquashFS profile alignment calculation now uses a named private structure
with the same member types and order. V2 produced byte-identical optimized
objects, identical disassembly after only the object-path preamble was
normalized, a passing C contract and 1,545 exact-choice differential cases.
V1 stopped before compilation because the scheduler raw-output directory
collided with the helper's new-work directory. Its failure is retained.

Provider metadata now records the canonical PAQ upstream revisions and the
existing CIX fork derivations. The real export sanitizer preserved the public
provenance and passed its private-path checks. This does not close remaining
source-package or selected-provider dependency obligations.

The earlier native v3 target was fully archived, content/link/mode verified and
reclaimed. Its three optimized binaries remain separately available with their
original hashes. Archive SHA-256:
`61fe285506e9670240d9999329fda0633e0a60e7e8ab65b2083f1a6f48d07867`.

Adapter probe v2 indexed 55/55 sources but retained 759 findings, 26 parser
recoveries and two Cppcheck configuration errors. An empty quality-gate result
is not a clean scan. The next probe binds the current profile/Node fixes and
three additional compiler projections. Its focused repair tests passed; the
new scan is pending resource admission.

The private platform-inventory workflow is prepared only. Its local writer
checks passed, including invalid inputs, refusal to overwrite, output overflow
and timeout handling. This is Linux-local evidence, not Windows/macOS/ARM
execution or PowerShell qualification. Actions remain disabled; account usage
limits and the old-workflow isolation procedure must be resolved before any
bounded private dispatch.
