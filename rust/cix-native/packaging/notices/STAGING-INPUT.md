# Selected runtime-provider notices

`provider-notices.json` is the deterministic input for the distribution exporter.
It binds every provider key and selected SHA-256 in the v4 engineering closure to
the verbatim notice files in `licenses/`. The exporter must verify each listed
notice digest, copy the listed texts without transformation, and fail if a
selected provider is absent from this manifest or differs from its bound hash.

This staging input does not add a provider, replace a provider, or establish a
licence conclusion. Its `unresolved` entries must remain visible in the release
closure and package review.
