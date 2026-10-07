# COND-CONTEXT-1 source and cost audit

`rank::encode_composition_tiles` is the global matched control. It writes
1024-byte independent type-class tiles. `rank::encode_context_type_classes`
writes its own `order`, `bucket_bits`, active context count, optional active-ID
colex rank, optional lane-length composition rank, then one complete
type-class payload per causal lane. `rank::decode_context_type_classes` uses
only stored parameters and restored earlier bytes, checks lane consumption and
rejects trailing payload bytes.

The experiment's CIXCTX1 frame has a 26-byte header and a four-byte CRC32 over
the full header and payload. Its mode is explicit: global composition,
order-1/4-bit context, order-2/8-bit context, or raw. Raw is always a finite
fallback candidate. `best` preserves the declared candidate order for ties.

The driver charges the outer header/CRC and every emitted payload byte. For a
context payload it independently rebuilds the same causal lane assignment from
the source only for encode-time accounting, then checks that its calculated
parameters, active-ID rank width, lane-length rank width and emitted lane
payload sizes sum exactly to the stored payload length. Decode does not use
that accounting reconstruction.

The driver bounds input archives to 1 MiB through `File::take(max+1)`, checks
regular-file metadata, verifies outer CRC before parsing dependent fields,
checks exact payload length, and writes output only after rank decoding and
output-length validation. `reject` accepts only inputs that fail archive
parsing. These are experiment-frame checks; they do not change native CIX
decoding.
