# Native whole-input selection

`full_engine::selection` is a bounded, content-only selector for inputs up to
128 MiB. It makes a complete archive available to the caller and records every
trial as selected, completed, failed, profile-omitted, or budget-omitted.

Priority is fixed before execution: raw, native, BEST-only generic PAQ v216
`-8`, v215 `-8`, v215 `-9L`, then catalogue specialists. Equal archive lengths
always retain that original order. FAST is raw plus native; DEFAULT excludes
PAQ-backed specialists but retains the filtered mode-0 Brotli candidate; BEST
includes all listed routes. Mixed-region selection is deliberately outside this
whole-input phase.

Reservations are declared admission arithmetic, not RSS measurements. Each
batch charges the retained source, one fixed output-cap reservation for the current incumbent archive, each candidate
model/buffer estimate, its CPU reservation, and `input_bytes + output_limit`
temporary capacity. A candidate that cannot fit is reported as budget-omitted;
the scheduler does not silently exceed a limit. The external supervisor still
owns hard process-RSS, temporary-filesystem and cancellation enforcement.

Provider paths are explicit installed paths. A JXL bridge is loaded per trial
from an optional absolute configured path, avoiding cross-thread sharing of its
library handle. PAQ calls stay inside the existing same-CIX worker bridge.
This document records a selector design and focused injected-executor tests; it
is not full-engine, codec, archive-parity, or release qualification evidence.
