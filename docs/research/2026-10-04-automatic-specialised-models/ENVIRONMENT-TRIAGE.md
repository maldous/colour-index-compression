# Frozen executable-backend environment triage

Classification: **the sanitization is ineffective in general; it has no effect
on this frozen run given the observed environment and admitted caller paths.**
This was a read-only review. No artifact, model, policy or timing cell changed.
The maintained, staged and source-snapshot executable adapters have identical
SHA-256 values in [environment-triage.json](environment-triage.json).

`legacy/executable.py:26` drops `CIX_*` from the environment it returns, but
`_run_paq` at line 65 starts with a fresh environment copy and updates it. Omitted
keys therefore survive. The coordinating review correctly identified this
general sanitization gap.

The actual whole-input and nested catalog admits joint-discount **mode 2**.
The encoder explicitly supplies `CIX_JOINT_DISCOUNT=2`, and the decoder supplies
the mode recorded in the archive. The inherited value cannot override that
explicit setting. Compatible modes 0–3 are likewise explicit; mode 4 uses stock
v215. The stock v215/v216 and store-state sources contain no `CIX_*` environment
consumer. Filtered modes use those stock/store-state backends.

The joint-discount source has one additional control:
`CIX_REGISTER_BASE_TRACE`. It opens a diagnostic output file and can cause I/O
or a failure when set; it does not provide predictive input. Read-only inspection
of the running controller, phase processes, PAQ child and system-manager CIX
variable names found neither this trace flag nor an inherited model flag. The
observed inherited CIX keys concern backend location, CLI identity, candidate
diagnostics and the scheduler lease; the PAQ sources do not consume them.

There is no demonstrated validity defect requiring interruption or a repeat.
Keep the frozen pass running. Before public distribution, make the child
environment replacement semantics explicit and isolate the optional research
trace control, with focused environment-contract verification. That later change
must carry a new source identity; it is not applied to this qualification build.
