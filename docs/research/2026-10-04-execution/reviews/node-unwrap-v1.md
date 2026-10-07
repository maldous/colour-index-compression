# Node unwrap cleanup v1 — prepared patch and qualification

This prepared artifact addresses retained scan-v3 issue
`7588a833-bfb0-4fb8-b88d-fb00dfe99e16` (`cppcheck:knownConditionTrueFalse`)
at `rust/cix-native/bindings/node/src/cix_node.c:139`. It has **not** been
applied to the source tree, because the prepared adapter probe retains the
current 55-file source identity.

## Exact patch

Apply [`node-unwrap-v1.patch`](node-unwrap-v1.patch) only after that probe has
finished and its receipt is preserved. The artifact requires these exact
pre-patch identities. Its SHA-256 is
`9edd25e9ddfb98ed07c38c8a25daee59a9a6d2674404ab2c92c93f3431aa2192`:

| Path | Pre-patch SHA-256 | Expected post-patch SHA-256 |
|---|---|---|
| `rust/cix-native/bindings/node/src/cix_node.c` | `791a6274e418a8604fb663ca5a23e757370913039d289773dcdad5cc48156f14` | `2556b1c33b93ce7bc4d15ac95b1449c6e35dfae56158f909172af33d1adff35b` |
| `rust/cix-native/bindings/node/test/contract.js` | `a4cae30f1e6770b91f96c44bc8963614a181b09f38ae8c844ea9868b3843947a` | `8f6a1e8195e270c90c27335bc03e0333b5965ba0fb39b215d42ec6a0ab9d5366` |

The C change makes the post-unwrap null-handle branch explicit while retaining
the `invalid CIX object` N-API exception and integer failure result. The test
change pins exact lifecycle and bad-receiver error text without altering the
existing successful context encode/decode or fragmented encoder/decoder paths.

## Bounded qualification

`jobs/node-unwrap-v1/run.py` is deliberately a Node add-on rebuild only. It
links the retained installed `libcix_native.so`, does not run Cargo or rebuild
the native library, and uses the actual dependency-free Node contract. The
runner refuses to start unless both post-patch identities and the patch-artifact
identity match. It records and rechecks the Node CMake input, loaded contract,
installed CIX API headers, Node API headers, selected SDK library, and CMake,
C compiler, and Node executable identities. It configures a Release add-on and
caps each command log at 1 MiB. Its acceptance is:

1. The add-on configures and builds against the retained SDK and `/usr/include/node`.
2. The existing successful context encode/decode and fragmented encoder/decoder
   calls pass.
3. A disposed context and disposed encoder throw `invalid CIX object`.
4. Cross-type and plain-object receiver calls throw `invalid CIX receiver type`.
5. Cancellation, reset, output limit, and decoder-flush rejection continue to pass.

This is an adapter-only check. It neither qualifies a new CIX archive route nor
rebuilds the CIX native library.
