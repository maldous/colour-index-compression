Integrated CLI proof checkpoint (private; not a release)

This checkpoint preserves five accepted canonical changes and twelve completed
qualification/preservation jobs since fa52832119928ac69c49f9d9205e1e274df5a35f.
The CLI now admits the existing relocated-pointer CIXB binary signature; its
focused prefix regression includes truncated, unknown and overlong inputs.
Build/install documentation and Debian/RPM/Homebrew prerequisites include LZ4
and Snappy development dependencies. No coding algorithm or wire format changed.

Accepted evidence: full default release library and three CLI builds, base CLI
and standard LZ4/Snappy round trips, relocated-pointer Brotli restoration,
corrected historical nested PAQ restoration, checksum/raw-frame rejection with
no final output, and one exact prefix library regression. Quinn source verdict
9af1ccc4; V4 scoped verdict 871c0bad; remaining-v2 verdict 078a5127. The optimized
library test binary contains 308 tests: only prefixes_are_exact has run in this
qualification; the other 307 were filtered out. No broad suite claim follows.

Preserved negative results include runtime-v1 scratch-budget termination,
runtime-v2 missing LZ4/Snappy development linker aliases, runtime-v3 missing CLI
signature admission, runtime-v4 incorrectly framed PAQ fixture, and remaining-v1
PAQ temporary-root ownership rejection. The verified namespace preflight and
remaining-v2 runtime use explicit readonly roots with trusted namespace-local
ancestors and unchanged production guards. The earlier failure did not record
its exact offending ancestor. Memory samples are lower bounds, not true peaks;
the 64 KiB namespace metadata allowance is not measured inode/dentry usage.

Historical PAQ evidence correction (independent classification 982ca8f7): the
relocated-pointer physical harness used the real PAQ bridge but embedded raw
paq8px bytes in its outer frame, bypassing the required CIXP nested wrapper.
It proved transform/payload/outer-envelope behavior, not complete historical
nested-frame compatibility. Preserve its bytes and this negative. Remaining-v2
replaced only that six-byte inner signature, retained length/CRC/other bytes,
and the ordinary full CLI restored all 10240 original bytes exactly. The old
raw frame now serves as a rejected malformed-frame control. This is a tiny
synthetic fixture, not a corpus performance or compression-record result.

Reproducibility limitation: the full builds/runtime/library-test evidence is
bound to the frozen complete 334-file source snapshot and isolated 261-package
candidate Cargo.lock. Some canonical peer work remains uncommitted and is NOT
part of these five accepted files. Checkout of this checkpoint ALONE therefore
does not reproduce the qualified full release candidate. Source snapshots,
recovery archives, binaries and provider assets remain preserved locally under
benchmark-work; they are excluded from this private source/evidence commit.
The live Cargo.lock is unchanged. Server, distribution, broader suite and RC51
qualification remain open; the benchmark remains HOLD. No publication or new
compression claim is made.

The ARM64 Rust sysroot was reversibly retired after exact publisher-archive
preservation. Its retained 30815124-byte archive and per-file restore manifest
remain available. Future ARM64 work requires a separately admitted >=164 MB
offline restore and new smoke check; old receipts do not assert it is installed.

existing-inputs.json binds exactly 357 existing paths. stage-paths.txt enumerates
those plus the five new checkpoint proof files. freeze-manifest.json hashes all
staged paths except itself; its external hash is recorded in the coordination
receipt. Post-commit/push receipts live separately to avoid a self-referential
commit identity. No peer partial files, binary/corpus assets or export inputs
are included. All earlier negative evidence is retained.
