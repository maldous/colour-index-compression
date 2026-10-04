# Release-contract assertion audit v1

**Scope.** Read-only review of CIX-owned C and C++ host-contract, installed-consumer,
and example test sources under `rust/cix-native`. Vendored source and generated `target/`
outputs are excluded. The review asks whether a check that performs work can disappear
when `NDEBUG` (or GLib's `G_DISABLE_ASSERT`) is defined.

## Result

There are no remaining first-party calls to standard `assert(...)` in the reviewed
source. The just-qualified RocksDB contract is the only prior candidate found by that
scan; it now uses its always-on `require` helper and its separate NDEBUG qualification
is outside this review's evidence.

No other CIX-owned host contract needs an assertion-independence repair. The two
assertion-like systems found below are not controlled by `NDEBUG`, and their operations
remain evaluated.

| Source / contract family | Mechanism | Release-elision result | Evidence of actual flags |
| --- | --- | --- | --- |
| `adapters/gio/contract.c` | `g_assert_true`, `g_assert_false`, `g_assert_cmp*`, `g_assert_no_error`, `g_assert_nonnull`, `g_assert_error` | **Always-on.** The installed GLib `gtestutils.h` implements these macros directly; `G_DISABLE_ASSERT` only disables the bare `g_assert(expr)` macro. This file has no bare `g_assert`. | `host-adapters-v1` through `v4` generated contract flags are `-pthread`, with neither `-DNDEBUG` nor `-DG_DISABLE_ASSERT`; their CMake build type is empty. |
| `adapters/hdf5/tests/filter_contract.c` | CIX `CHECK(condition)` | **Always-on.** It evaluates the condition, prints function/line/expression, and goes to cleanup. It does not expand to standard `assert`. | Passing `host-adapters-v5` and `v6` generated contract flags are `-std=gnu99` plus CIX filter definitions, without `-DNDEBUG`; their CMake build type is empty. |
| `adapters/blosc2/tests/blosc2_cix_contract.c`, `adapters/gstreamer/tests/contract.c`, `adapters/sevenzip/cix_7zip_contract.cpp`, `adapters/wiredtiger/tests/wiredtiger_contract.c` | Direct status/value branches and return codes | **Always-on.** No assertion macro appears in the CIX test sources. | Captured contract flags contain no `-DNDEBUG` for the Blosc2, GStreamer, 7-Zip, and WiredTiger CMake contract targets examined. |
| `adapters/squashfs/profile/tests/profile_contract.c`, `adapters/squashfs/userspace/tests/squashfuse_*_contract.c`, `packaging/sdk/tests/*consumer*`, `packaging/squash/contract.c`, `tests/c_api_consumer.c` | Direct status/value branches and return codes | **Always-on.** No assertion macro appears in the CIX test sources. | SquashFS profile qualifications deliberately used `-O3 -DNDEBUG`; their contract source uses direct branches, so that release evidence remains valid on this question. |

## Historical evidence interpretation

An empty CMake build type is material: CMake's cached `CMAKE_C_FLAGS_RELEASE` or
`CMAKE_CXX_FLAGS_RELEASE` text may contain `-DNDEBUG`, but it is not selected unless
`CMAKE_BUILD_TYPE=Release` (or equivalent flags) is actually used. The generated
`flags.make` records above are the authoritative final target flags, not the cache's
unused defaults.

The following existing pass evidence is therefore not compromised by assertion elision:

- GIO host-adapter passes (`host-adapters-v1`–`v4`): no standard assert and no
  `G_DISABLE_ASSERT`.
- HDF5 host-adapter passes (`host-adapters-v5` and `v6`): CIX `CHECK` remains active.
- Blosc2, GStreamer, 7-Zip, and WiredTiger host contracts: direct checks, with no
  standard assertion call found.
- SquashFS profile Release passes: direct checks retained under actual `-DNDEBUG`.

## Required changes

None outside the already completed RocksDB repair. For future C/C++ host-contract
recipes, record the target's generated compile flags or `compile_commands.json` and
reject a bare standard `assert` that encloses an operation. For GLib tests, prohibit
bare `g_assert(expr)` around an operation; the `g_assert_true`/comparison/error macros
used by the current GIO contract are appropriate.
