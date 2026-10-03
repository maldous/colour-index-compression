# Shared lane support boundary — checkpoint 427ac54aa

## Finding before dispatch

The completed NCSL v2 lane archive contains exactly one positional support per
archive: source length, stride, and residual mask are paid once in its 17-byte
header.  The ordered lane offsets and decoded lengths follow deterministically
from that support.  Each lane then carries an independently selected route,
its already framed coder payload length, and its opaque payload.

There is no support alphabet, support table, repeated support sequence, or
cross-archive state in the selected lane codec.  The encoder does not transmit
a discovered support blob which another representation could share.  A new
uniform support dictionary, trie, diagram, or template cache would introduce a
different model and would not be a same-discovered-support comparison.

The adjacent `shared_lane_supports.rs` is therefore a strict bounded NCSL v2
diagnostic, not a new archive codec.  It reports the one already-transmitted
support and the actual header, lane-metadata, and opaque-payload byte totals.
It does not search, recompress, decode entropy payloads, or claim a compressed
metadata or diagram result.

## Accounting consequence

The existing `route:u8, decoded_len:u32, payload_len:u32` lane records cost
9 bytes each.  `decoded_len` is derivable from the paid global support, but
removing it is a frame-format compaction.  It does not factor an existing
support model, and it would require a fresh NCSL format identity and matched
controls.  This checkpoint does not make that change or credit its possible
four-bytes-per-lane saving to shared support descriptions.

Likewise, applying a conventional compressor to the lane metadata creates a
new metadata codec and embeds its model/frame.  With one support and at most
eight lane records it is not a control for sharing a current support blob.
No imaginary compressed-metadata byte count is reported.

A restricted decision diagram has no nontrivial graph here: the sole support
is one header state followed by one deterministic ordered path.  Serializing
nodes and edges would be a new representation with no repeated branch or
subgraph to share.  It is explicitly not dispatched.

## Smallest diagnostic check

When root schedules the checkpoint, run only:

```text
shared_lane_supports inspect <already-verified NCSL-v2 archive>
```

The input is bounded to a regular file of at most 32768 bytes and declares at
most 4096 source bytes, stride 1 through 8, and at most eight lanes.  The
diagnostic rejects malformed headers, masks, route IDs, derived lane lengths,
payload ranges, and trailing bytes.  It writes no archive or output file.

No further support-sharing archive trial is justified from the present lane
format.  A future proposal must first identify a transmitted, repeated support
object and compare its fully paid model bytes against the existing NCSL frame
under a new experiment identity.
