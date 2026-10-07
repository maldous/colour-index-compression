# PRED-COST-1 native payload accounting

The predictive-mixture omission screen failed. This bounded follow-up does not
introduce a model, a mixer, a route, an archive frame, or a production change.
It measures existing native payloads for a single already frozen chunk of at
most 16 KiB: adaptive order 0, adaptive order 1, PPM fixed order 3 / escape 1
without update exclusion, fixedmix v1 eta 6, and corrected fixedmix v3 eta 6
with N1 `{4,1024}` and N2 `{6,16384}`.

`cost_trace.rs` calls the frozen native encoders and decoders, checks fresh
in-process restoration byte equality, and emits payload total bytes,
header/metadata bytes, arithmetic payload bytes, and a CRC32 over those exact
payload bytes. The CRC is an archive-only identifier, not a complete archive
checksum. No complete archive or compression-ratio claim follows.

The fixedmix v3 header is counted from the implementation: version byte, eta
ID, seven recurrence-configuration bytes, and the encoded arithmetic-bit
length varint. Adaptive and PPM headers likewise use their actual versioned
fields through the end of their bit-length varint. Termination cannot be
separated from finite-precision arithmetic payload bytes by these native APIs;
the result records it as combined and does not invent a split.

Ideal loss is not recomputed here. The existing trace analysis may join an
exact matching chunk's ideal losses by hash. Adaptive order-0/order-1 have no
new exact probability trace in this experiment, so their rows remain physical
only. Execution is scheduler-owned under `CIX_RELEASE_LEASE`; no run starts
from this plan.
