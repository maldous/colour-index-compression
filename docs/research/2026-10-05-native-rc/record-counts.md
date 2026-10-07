# Remaining-count record route

The historical database remaining-count route has no separate raw magic: it is
`MYCS1` with dynamic remaining-count ordering, mode 3, carried by the existing
`CIXD\x01` frame and its selected backend. `record_ordering.rs` already held
the exact transform, inverse, and mode-3 reference fixture. The named native
entries bind that contract explicitly and use the existing bounded raw inverse;
the declared CIXD source length remains the reconstruction cap.

The frozen nontrivial reference vector is
`rust/cix-native/tests/fixtures/record_stride/record-mycs-mode3.raw`. It
contains a nonempty dynamic arithmetic ordering payload and is checked for raw
byte parity and exact bounded restoration. Frame-provider/catalog registration
remains outside this increment.
