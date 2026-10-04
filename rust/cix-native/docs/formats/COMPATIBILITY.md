# Container compatibility

CIX identifies archives by a five-byte ASCII magic. The 0.1 command-line
decoder recognizes the following containers:

| Magic | Role | Encoder status in 0.1 |
| --- | --- | --- |
| `CIXG1` | generic framed CIX stream | supported |
| `CIXG2` | versioned generic framed CIX stream | supported |
| `CIXM5` | legacy CIXM stream | decode compatibility |
| `CIXM6` | legacy CIXM stream revision | supported |
| `CIXF1` | validated filename wrapper around a CIXM stream | supported |
| `CIXB1` | bounded native-backend envelope | supported; see [FORMAT-CIXB1.md](FORMAT-CIXB1.md) |
| `CIXZ1` | bounded mixed streaming container | supported; see [FORMAT-CIXZ1.md](FORMAT-CIXZ1.md) |

The generic containers use independently validated frames and terminal
integrity data. CIXM6 retains its historical persistent-state and history
semantics; CIXF1 adds validated UTF-8 filename metadata to a CIXM stream.

The magic alone does not establish that an older encoder’s full option set is
available in this release. Decode compatibility is maintained only for
container variants accepted by the 0.1 decoder. Unknown container revisions,
unknown route identifiers, trailing bytes, malformed lengths, and failed
integrity checks are rejected.

Format documents are protocol references, not performance claims. Consumers
should test archives with `uncix -t` when restoration is not required and use
the same release line for any newly created archive that must be decoded in a
controlled environment.
