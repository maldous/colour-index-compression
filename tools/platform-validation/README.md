# Platform inventory tool

`inventory.py` creates a small JSON receipt from a requested reviewed commit SHA
and one fixed platform target. It validates the SHA shape, records host-reported
OS, architecture, CPU count, visible and cgroup memory/CPU limits, workspace disk facts, and bounded five-second toolchain probes, and
refuses to overwrite an existing receipt, caps the receipt at 64 MB, and records whether the requested target matches the observed host without treating a mismatch as qualification failure. Toolchain version probes use a five-second deadline and retain at most 4 KiB of combined output while the child process runs. Overflow causes termination; this bounds retained receipt data, not an assertion that a process never wrote more bytes. POSIX probes terminate an isolated process group; Windows probes terminate only the direct child. It neither builds CIX nor runs native or full-engine
contracts.

The workflow is deliberately `workflow_dispatch` only. It has one inventory job
per dispatch, an eight-minute timeout, `contents: read`, a three-day artifact,
and sparse checkout limited to this tool. GitHub concurrency permits one active
job per group plus at most one pending job; it is not a two-worker resource
claim. The coordinator’s two-worker ceiling remains a later admission policy.

The checkout and artifact actions are pinned to immutable upstream commits:
`actions/checkout` v5 is `fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09` and
`actions/upload-artifact` v4 is `ea165f8d65b6e75b540449e92b4886f43607fa02`. On
2026-10-05, the official GitHub API tag-ref endpoints resolved those tags to
those commits; the review JSON preserves that read-only receipt. The pins and
their intended use were checked against the official action repositories and
GitHub Actions documentation. No workflow enablement,
dispatch, toolchain installation, cache upload, dataset upload, or secret
collection is part of this tool.
