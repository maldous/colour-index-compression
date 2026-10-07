# Zero-regret longer-context mixer prerequisite trial

CIXR3 retains the CIXR2 raw/global/four-bank candidates and adds the qualified
five/six-byte context model with the same bank choices. Every block chooses by
complete nested frame size, and the outer header has the same size. The decoder
dispatches the distinct CIXQ2/CIXQ3 nested magic, so selectors remain explicit.
This is separate from the frozen CIXT1 Silesia trial.

Initial validation passed three round trips with physical nonregression against
CIXR2, an explicitly constructed valid Q3 branch, and rejection of six damaged
frames. The underlying extended model already passed 36 small and six larger
native/Python byte-equality and round-trip checks. A four-worker full 29-member
prerequisite run is now active with complete input/source/binary/output hashes.
No Silesia extension or new rank is inferred before the gate completes.

The separate CIXT1 rank checker passed its integrity test: incomplete cohorts,
altered artifact bytes and mixed policies are rejected. Its use remains gated
on all twelve Silesia results and complete decoding records.
