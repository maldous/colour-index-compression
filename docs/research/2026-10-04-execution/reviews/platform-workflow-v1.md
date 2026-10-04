# Platform workflow v1 review

This change prepares a manual-only, inventory-only workflow. It accepts an
exact lowercase 40-character reviewed source SHA and one allowlisted target:
Linux ARM64, Windows x64, macOS ARM64, or macOS x64. It reports observed OS,
architecture, CPU count, visible memory, and workspace disk facts in a capped
64 MB JSON receipt retained for three days. It refuses overwrite; a target/host
mismatch is recorded as an observation rather than a qualification result. Toolchain probes retain at most 4 KiB and stop on overflow or a five-second deadline; this bounds receipt data rather than claiming a process-write limit.

It does not expose native-contract, full-engine, archive exchange, packaging,
or signing stages. A receipt therefore is runner discovery evidence only, not
platform support or product qualification. The workflow stays unactivated until
root completes the coordinator’s historical-workflow and billing prerequisites.

`actions/checkout` is pinned to v5 commit
`fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09`; `actions/upload-artifact` is pinned
to current v4 commit `ea165f8d65b6e75b540449e92b4886f43607fa02`. On 2026-10-05,
read-only official GitHub API tag-ref calls resolved the v5 and v4 tags to these
commits. Official action
repositories document checkout’s ref behavior and artifact retention; GitHub’s
security guidance recommends immutable full-SHA action pins. The coordinator
report is the authority for fixed runners, resource ceilings, private-repo
status, and unresolved billing.

The Linux-local inventory contract completed under the root lease in
`jobs/platform-inventory-local-v1`: valid output, overwrite refusal, rejected
SHA/target inputs, output overflow and timeout behavior passed. Workflow and
tool hashes remained unchanged. PowerShell and hosted target execution were
not performed. The recipe's original aggregate temporary allowance was corrected
before its first dispatch to account for retained shared work.
