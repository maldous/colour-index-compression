# Native port map

`port-map.json` is the authoritative machine-readable inventory of every maintained
runtime production module. Every entry is **not_yet_qualified**. It assigns a
native owner and intended target area; it does not authorize an implementation
or imply byte compatibility.

Wire rule: `CIXB` denotes legacy/specialist binary envelopes whose exact subtype
is defined by the owning runtime module. `CIXG`, `CIXM`, `CIXF`, and `CIXZ` are
ASCII native container families and must not be relabelled as CIXB. Each port
must preserve exact encoder order, decoder inverse, backend arguments, resource
limits, and focused archive fixtures before it becomes qualified.

The canonical baseline is `rust/cix-native` at `97fea6189`, reconciled in
`canonical-baseline.json`. The current Python runtime is reference evidence,
not an allowed runtime dependency after the native/no-Python RC gate.
