# Full-engine jobs

`full_engine::job_protocol` is the RC23 same-executable job library. It has a
versioned length-prefixed binary control wire (`CJB1`, version 1) and keeps
binary input, archive, and restored data on caller-provided `Read`/`Write`
streams. It never accepts a path, starts a command, or invokes another runtime.

The protocol supports whole-input selection and bounded full-engine archive
decode. A request declares input, archive, output, memory, intermediate,
temporary, worker, and optional deadline limits. Control records reject unknown
versions, oversized records, truncated records, and invalid UTF-8. Selection
results retain the full outer trial report, native and mixed nested diagnostics,
mixed omitted/provider-omission counts, and separate recognizer discovery
outcomes.

Progress is stage-only: accepted, input read, selection/decode start and finish,
and output written. It deliberately does not report fabricated byte progress.
Cancellation uses one caller-owned token per request and is checked at those
boundaries and by the selected engine paths. It cannot force-preempt an
in-process codec call.

`job_cli` is the implemented same-executable command-mode adapter. Its only
forms are:

```
cix --cix-job-capabilities-v1
cix --cix-job-v1 --input ABS --output ABS \
  --private-library-dir ABS --temporary-root ABS
```

The interface is present for RC23 qualification; passing its scheduled native
provider and end-to-end qualification remains separate from this contract.

The first writes one capability control record to stdout. The second reads one
request control record from stdin, followed optionally by one matching cancel
record; stdout contains only progress and one result or error record. Input
and output bytes never travel over standard I/O. The input must already be an
absolute regular file. The output must be an absolute nonexistent file; the
adapter writes a private sibling temporary and atomically claims the final name
before its final result record. It never overwrites an existing output. The
filesystem and stdout are independent channels: if that final stdout write
fails, the process returns nonzero and the committed output may still exist.
Terminal diagnostic text is truncated on a UTF-8 boundary to the control-wire
text limit, so unusually long native messages still yield a parseable error.

The private-library and temporary directories must be explicit absolute
directories. Provider discovery uses those supplied locations; it does not use
`PATH`. Decode constructs only the raw backend provider, so a raw archive does
not require image bridge libraries to be present. Direct JPEG XL and spatial
frames load only their required configured bridge; a CIXH1 envelope defers a
missing optional bridge until a nested frame actually needs it.

The sibling staged output is reserved against `temporary_bytes` before it is
created. Selection reserves the smaller of archive and output caps, then passes
only the remaining temporary budget to its workers. Decode reserves its output
cap; non-native decode frames additionally reserve a conservative PAQ-worker
input and output allowance. That allowance uses the larger of archive and
intermediate caps for worker input, plus the larger of restored-output and
intermediate caps for worker output, because nested frames can transform either
side before PAQ runs. Native frames without a worker may use the entire
declared temporary budget for their staged output.

The command mode makes no process-RSS guarantee. Its whole-input selection
capability is deliberately limited to 128 MiB by the caller-facing job policy;
the request's declared resource limits remain the admission controls passed to
the selector and decoder. Native cancellation remains cooperative, so callers
that require a hard stop must terminate the job process. The optional cancel
record is considered only before the synchronized filesystem-commit cutoff;
EOF without one is not cancellation. A cancel parsed after that cutoff is
ignored because publication has already begun.
The adapter has a deterministic control-plane cutoff test; timing-independent
coverage of cancellation inside a native codec call remains unavailable because
those calls are deliberately cooperative rather than preemptible.
