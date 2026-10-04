# Compiler-metadata refresh proposal v1

## Scope and decision

This is a source-only design note for `tools/sonar-cxx/repair.py`.  It does not
change the tool or rerun a compiler.

The existing `CMAKE_RECEIPTS` table points at older `flags.make` material.  It
cannot describe the current completed qualifications below.  Their saved
`compile_commands.json` files contain the actual CMake compiler argument
vectors, so a new fail-closed reader should use those files directly rather
than reconstructing flags from CMake text or `flags.make`.

The direct spatial contract compiler invocation is also present verbatim in
the successful receipt.  It should be represented as a compilation-database
row with its exact arguments, after replacing only the frozen test source path
with its current equivalent.  It must not be changed into a synthetic `-c`
invocation.

## Evidence checked now

Both completed jobs have a zero command result and a retained source copy.  At
the time of this review, each current product file below has the same SHA-256
as that copy.

| Qualification | Current translation units | Current local headers and build file | Retained command source |
| --- | --- | --- | --- |
| `rocksdb-contract-ndebug-v1` | `adapters/rocksdb/cix_compression_manager.cc`, `adapters/rocksdb/contract_test.cc` | `cix_compression_manager.h`, `CMakeLists.txt` | `jobs/rocksdb-contract-ndebug-v1/compile_commands.json` |
| `spatial-stride-contract-v1` | `codecs/spatial/cix_spatial_bridge.cpp`, `codecs/spatial/tests/spatial_stride_contract.cpp` | `cix_spatial_bridge.h`, `CMakeLists.txt`; installed copy `prefix/include/cix/cix_spatial_bridge.h` | `jobs/spatial-stride-contract-v1/compile_commands.json` and its successful `compile-contract` receipt row |
| `jxl-drain-contract-v1` | `codecs/jxl/cix_jxl_bridge.cpp`, `codecs/jxl/tests/jxl_drain_contract.cpp` | `cix_jxl_bridge.h`, `CMakeLists.txt`, `README.md`; installed copy `prefix/include/cix/cix_jxl_bridge.h` | `jobs/jxl-drain-contract-v1/compile_commands.json` and its successful `compile-contract` receipt row |

The checked local-header digests are:

* RocksDB `cix_compression_manager.h`:
  `17856bcd05e18cd2bf75683c2b634b66b9a1f8181126ca6aeaa6a2d306655b80`.
* Spatial `cix_spatial_bridge.h`, including the installed test header:
  `049b7ec3e64b162b5a27d3e440ae90658c51696bdea572ad8c71f6899b39d07e`.

The CMake databases already retain their actual build directories and include
operands.  In particular, the RocksDB database records `-O3 -DNDEBUG`,
`-std=gnu++20`, and `-fno-rtti`; the spatial bridge database records its
CharLS/OpenJPEG include roots and strict floating-point flags.  The refresh
must preserve these vectors byte-for-byte except for an approved frozen-source
prefix substitution.

The spatial contract's successful direct argv is:

```text
c++ -std=c++17 -Wall -Wextra -Werror
  <frozen>/tests/spatial_stride_contract.cpp
  -I <qualified-prefix>/include/cix
  -L <qualified-prefix>/lib
  -Wl,-rpath,<qualified-prefix>/lib
  -lcix_spatial_bridge
  -o <qualified-work>/spatial_stride_contract
```

It uses absolute semantic paths.  `run.py` did not record a `cwd` for this
`subprocess.run` call, unlike other direct-capture receipts.  The refresh must
therefore set the compilation-database `directory` to the normalized current
spatial source root and record `directory_origin:
"normalised-no-recorded-cwd-all-semantic-operands-absolute"`.  This is a
metadata directory for tools that require one; it is not evidence of the
original process working directory.  A future qualification should record the
actual `cwd`, which then replaces this narrow exception.

## Proposed helper

Add a small, separately tested helper beside the existing completed-receipt
readers.  The constants below intentionally name only these two receipts.
They should not be folded into the older `CMAKE_RECEIPTS`/`flags.make` path.

```python
@dataclass(frozen=True)
class QualifiedCxxReceipt:
    name: str
    receipt: Path
    database: Path
    snapshot_root: Path
    current_root: Path
    units: tuple[str, ...]
    local_files: tuple[str, ...]       # sources, owned headers, CMake input


def _same_file(snapshot: Path, current: Path) -> str | None:
    if not snapshot.is_file() or not current.is_file():
        return "missing"
    return None if digest(snapshot) == digest(current) else "sha256 mismatch"


def _normalise_receipt_row(row: dict, snapshot_root: Path,
                           current_root: Path) -> dict:
    arguments = row.get("arguments") or shlex.split(row["command"])
    frozen_file = Path(row["file"]).resolve()
    if not frozen_file.is_relative_to(snapshot_root):
        raise RuntimeError("receipt translation unit escapes its frozen root")
    relative = frozen_file.relative_to(snapshot_root)
    current_file = (current_root / relative).resolve()
    if not current_file.is_relative_to(current_root) or not current_file.is_file():
        raise RuntimeError("mapped current translation unit is absent or escapes root")
    # Replace paths as path-prefixes, including attached -I<path> operands,
    # never by an unrestricted textual replacement.
    def map_operand(value: str) -> str:
        prefix = str(snapshot_root)
        if value == prefix or value.startswith(prefix + os.sep):
            return str(current_root) + value[len(prefix):]
        for flag in ("-I", "-isystem"):
            if value.startswith(flag + prefix + os.sep):
                return flag + str(current_root) + value[len(flag + prefix):]
        return value
    if arguments.count(str(frozen_file)) != 1 or "-c" not in arguments:
        raise RuntimeError("CMake row is not one exact compile invocation")
    mapped = [map_operand(value) for value in arguments]
    if mapped.count(str(current_file)) != 1:
        raise RuntimeError("source operand was not mapped exactly once")
    return {"file": str(current_file), "directory": row["directory"],
            "arguments": mapped}


def _qualified_cmake_database(spec: QualifiedCxxReceipt) -> tuple[list[dict], dict]:
    receipt = json.loads(spec.receipt.read_text())
    if any(command.get("returncode") != 0 for command in receipt.get("commands", ())):
        return [], {"status": "failed_receipt"}
    if not spec.database.is_file():
        return [], {"status": "missing_database"}
    mismatches = {
        relative: reason
        for relative in spec.local_files
        if (reason := _same_file(spec.snapshot_root / relative,
                                 spec.current_root / relative))
    }
    if mismatches:
        return [], {"status": "stale_source_or_header", "mismatches": mismatches}
    rows = [_normalise_receipt_row(row, spec.snapshot_root, spec.current_root)
            for row in json.loads(spec.database.read_text())]
    wanted = {str((spec.current_root / relative).resolve()) for relative in spec.units}
    selected = [row for row in rows if row["file"] in wanted]
    if {row["file"] for row in selected} != wanted or len(selected) != len(wanted):
        return [], {"status": "incomplete_or_duplicate_database_units"}
    return selected, {"status": "qualified_cmake_database_reused",
                      "database_sha256": digest(spec.database),
                      "source_header_hashes": {
                          relative: digest(spec.current_root / relative)
                          for relative in spec.local_files}}
```

The production helper should use the exact receipt paths and roots:

```python
QualifiedCxxReceipt(
    "rocksdb-contract-ndebug-v1",
    ROOT / "docs/research/2026-10-04-execution/jobs/rocksdb-contract-ndebug-v1/receipt.json",
    ROOT / "docs/research/2026-10-04-execution/jobs/rocksdb-contract-ndebug-v1/compile_commands.json",
    ROOT / "benchmark-work/native-rc-check-v1/rocksdb-contract-ndebug-v1/source",
    source / "rust/cix-native/adapters/rocksdb",
    ("cix_compression_manager.cc", "contract_test.cc"),
    ("CMakeLists.txt", "cix_compression_manager.cc", "cix_compression_manager.h", "contract_test.cc"),
)
QualifiedCxxReceipt(
    "spatial-stride-contract-v1-bridge",
    ROOT / "docs/research/2026-10-04-execution/jobs/spatial-stride-contract-v1/receipt.json",
    ROOT / "docs/research/2026-10-04-execution/jobs/spatial-stride-contract-v1/compile_commands.json",
    ROOT / "benchmark-work/native-rc-check-v1/spatial-stride-contract-v1/source",
    source / "rust/cix-native/codecs/spatial",
    ("cix_spatial_bridge.cpp",),
    ("CMakeLists.txt", "cix_spatial_bridge.cpp", "cix_spatial_bridge.h"),
)
```

For the spatial direct test, extract only the `compile-contract` row from the
same passing receipt.  Require it to be the sole matching successful row,
require its argv to contain the frozen test path exactly once, and require all
of these equalities before emitting a row:

```python
snapshot / "tests/spatial_stride_contract.cpp" == current / "tests/spatial_stride_contract.cpp"
snapshot / "cix_spatial_bridge.h" == current / "cix_spatial_bridge.h"
snapshot / "cix_spatial_bridge.h" == qualified_prefix / "include/cix/cix_spatial_bridge.h"
```

The emitted row keeps the full recorded argument vector, maps only the test
source operand to current source, sets `file` to that current test, and uses
the normalized-directory provenance stated above.  The header equality binds
both the frozen and installed contract header to the current header before the
direct test row can be reused.

## Header and input closure

The helper should save a `header_bindings` provenance object for every emitted
unit.  It must include every CIX-owned header in the retained dependency file
(`*.o.d`) that lies below the snapshot root, with its frozen path, current
path, and both digests.  It must reject an unreadable dependency file, a local
header without a current counterpart, or any digest difference.  This is
stronger than checking only the translation unit.

Headers outside the CIX snapshot do not have a product-source counterpart.
For those, record the exact dependency paths and their current digests as
`external_header_inputs`; do not pretend a current product source hash proves
their historical identity.  The retained receipt already pins selected SDK
libraries and RocksDB headers, but it does not pin every transitive system or
SDK header.  The refresh can use those paths for analysis only after recording
them; it cannot upgrade the older qualification into a full external-header
reproducibility claim.

The same provenance must retain the CMake database digest, receipt digest,
actual CMake `directory`, the frozen source path, the normalized current source
path, and the direct-row directory-origin marker.  This makes a subsequent
source or header edit fail closed instead of silently reusing an old command.

## Minimal tests for `tools/sonar-cxx/test_repair.py`

Use a temporary fixture with a frozen root, a current root, one `.cpp`, one
local `.h`, a dependency file, a CMake database row, and a direct spatial-style
receipt row.  The test should prove all of the following:

1. A matching fixture produces the CMake bridge, RocksDB contract, and direct
   spatial-test rows.  The CMake `directory` and every non-source compiler
   operand are unchanged; only the frozen source operand is re-rooted.
2. The direct row retains `-Wall -Wextra -Werror`, linker operands, and its
   full argv.  Its output records the explicit normalized-directory provenance.
3. Changing either current `.cpp` or current `.h` rejects all rows using that
   snapshot.  Changing the installed spatial header rejects the direct row.
4. A missing, duplicate, escaping, or non-`-c` CMake database translation unit
   is rejected.  The direct test is the intentional exception: it is accepted
   only through the direct-receipt path and never converted to `-c`.
5. A changed database, receipt, dependency file, or external-header input
   digest is visible in provenance and prevents reuse where it changes the
   local identity contract.

The JXL qualification records the direct compiler working directory, so its
direct row retains that exact directory instead of using the spatial
normalization exception. Its retained Ninja build lacks `.o.d` files; reuse
therefore verifies the receipt's complete source manifest, installed header,
and every path/hash in the receipt-pinned JXL dependency-prefix manifest. It
records that manifest method explicitly rather than inventing a dependency-file
claim. A later retained `ninja -t deps` capture can strengthen this closure.

This adds four actual current translation units to the compiler closure
(RocksDB bridge, RocksDB contract, spatial bridge, JXL bridge) plus the
current spatial and JXL contract sources represented by their direct compiler
invocations. It does not claim that unrelated unconfigured C/C++ translation
units are covered.
