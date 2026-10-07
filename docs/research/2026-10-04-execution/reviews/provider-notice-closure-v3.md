# Provider notice and provenance closure v3

`rust/cix-native/packaging/notices/provider-provenance-v3.json` is the
deterministic input for the fourteen providers selected by
`distribution-engineering-v4`. It preserves the v2 notice map and adds the
evidence that ties every selected library hash to its recorded artifact receipt
or selected closure.

The JXL family is bound to the `v0.12.0` checkout at
`a7a9c787341cf703dede03c2009fa460cae5e5df`, its recorded Google submodule
commits, and `jxl-bridge-v3/installed.json`. CharLS and OpenJPEG are bound to
the exact Ubuntu package names, versions, filenames, archive hashes, and the
SDK provision/install receipts. PAQ keeps the existing four source receipts,
local roots, and README identities. The spatial bridge has its selected binary
hash and package inputs, but no dedicated source-to-binary receipt; that is
recorded as unresolved rather than implied.

The staged input instructs the exporter to copy each listed exact notice text
with a hash check. It records source availability separately and makes no claim
that source redistribution follows from a particular binary package or from a
permissive licence text. The unresolved list remains part of final package
review: PAQ upstream identities, spatial bridge build provenance, and the
missing package repository/source-package URLs.
