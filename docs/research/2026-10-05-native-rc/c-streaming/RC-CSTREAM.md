# Native C streaming ABI

The planned `cix_stream.h` ABI owns opaque encoder and decoder handles. Calls
are serialized per handle and use the native independent CIXG1 stream only.
Each process result reports consumed input, produced output, and whether the
caller must supply input, drain output, or has reached the checked terminator.

`flush` closes a partial encoder block; `finish` must be called until its
result is `FINISHED`; `reset` is the only recovery after a codec error. Input
and output ranges are required to be valid and disjoint. Handles are created
with a copied `cix_options_v1` snapshot and destroyed exactly once by their
owner. The ABI contains panics and serializes operations with a mutex.

This interface does not expose cancellation-handle ownership, retained model
history, CIXM6, or full-engine archives.
