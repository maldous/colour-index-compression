# Record/stride parity fixtures

These byte-for-byte fixtures are deliberately kept inside the native crate so
that tests do not depend on the research tree being present in a source
snapshot or distribution build.

They were generated from the retained Python reference by
`docs/research/2026-10-04-native-rc/record-stride-completion/make_fixtures.py`.
The immutable research originals remain in
`docs/research/2026-10-04-native-rc/record-stride-completion/fixtures/`.
`manifest.json`, copied unchanged with this fixture set, records every input
and raw-frame SHA-256 digest and the reference generator provenance.

The fixtures are synthetic, small parity cases only; they are not corpus data
or compression-performance evidence.
