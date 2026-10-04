# Current C/C++ Sonar preparation

`prepared-v1` under `docs/research/2026-10-04-sonar-cxx-repair/` is retained
historical evidence. It names the retired `cix-integrated-source-candidate`
export and does not represent the release-candidate `rust/cix-native` tree.

The current preparation command inventories these source groups from the active
repository root:

- CIX native headers, bridges, codec, example and qualification sources,
  including all four CIX-owned PAQ bridge families;
- CIX adapters, bindings, packaging consumers and native tests;
- unchanged bundled libbsc and libzpaq vendor source; and
- unchanged PAQ v215, v216, joint-discount and store-state source dependencies
  from the retained reference roots.

Vendor groups remain separate Sonar projects. Their findings are evidence only;
they do not authorize vendor edits or count as CIX-owned remediation.

The preparation reuses only exact retained PAQ compilation databases, completed
CMake `flags.make` receipts, and successful direct compiler argv recorded in a
completed job's stdout. Each receipt is accepted only when the current source
file hashes exactly to the file built by that job. Direct argv is retained
verbatim apart from rebasing that verified translation-unit path to the current
identical file.
Every remaining C or C++ translation unit is written to
`unconfigured_translation_units` in the plan. This produces
`PREPARED_BLOCKED_COMPILER_CLOSURE`, and execution fails before a server starts;
it cannot report a partial scan as clean. A later completed job must supply an
exact compiler receipt for each listed translation unit, followed by a new
prepared directory.

The runner retains the authenticated benchmark-stop, process-idle, exclusive
scheduler lock, physical-core lease and resource-slice checks. Preparation does
not run Sonar, Cppcheck, a compiler, or a benchmark.

`prepared-v2` records the first current-tree inventory but predates inclusion
of the native example and qualification C sources. `prepared-v3` adds the
first completed-receipt map. Retain both as preparation history; neither is a
current release decision after later source and receipt-map changes. Create a
new unused prepared directory only after the remaining compiler closures have
matching current-source receipts.

```sh
python3 tools/sonar-cxx/repair.py prepare \
  --out docs/research/2026-10-04-execution/sonar-preparation/prepared-vNEXT
```

The resulting plan is evidence of intended scope and compiler-closure state,
not C++ analysis completion. Do not execute it until all listed compiler
configuration gaps are resolved.

After the reader job releases the shared scheduler lease, root may run:

```sh
python3 tools/sonar-cxx/repair.py probe \
  --out docs/research/2026-10-04-execution/sonar-preparation/probe-v6
```

The probe retains the same stop, idle, lease and resource controls, then checks
the local CXX plugin/image setup and detects an intentional null-pointer
fixture. Its receipt cannot be used as product-source coverage.

`probe-v3` is intentionally CXX-only. The fixed server image's built-in
extension layer is listed in `raw/image-core-extension-inventory.json` and is
replaced by an empty read-only bind mount. This omits the image's C#, Flex, Go,
HTML, IaC, Java, JavaScript, Kotlin, PHP, Python, Ruby, Rust, Scala, Text,
VB.NET and XML analyzers, plus its non-language CAYC and JaCoCo extensions.
The separately checksummed CXX plugin remains mounted in
`/opt/sonarqube/extensions/plugins`. The probe records that omission and its
limits; it makes no claim about the omitted product languages, which require
separate coverage later. The immutable image is never modified.

The privately extracted Ubuntu Cppcheck 2.13 binary was compiled with its
configuration directory fixed at `/usr/lib/x86_64-linux-gnu/cppcheck/cfg`.
`probe-v3` preserved the resulting `std.cfg` lookup failure. `probe-v4` first
stages a checked private ELF closure: Cppcheck's `libtinyxml2`, `libstdc++`,
`libm`, `libgcc_s`, `libc`, ELF loader, and complete configuration directory.
It then runs the unchanged private binary through Bubblewrap, read-only-binding
that staged closure over the already-existing `/usr/lib/x86_64-linux-gnu`
mountpoint, including its staged loader at the loader's resolved architecture
library path. The receipt pins each source path and hash, plus the wrapper argv
and overlay. It does not install files under host `/usr`, replace the binary, or use explicit
library flags as a substitute for the binary's mandatory stock `std.cfg`
lookup.

`probe-v5` established that the staged Cppcheck runtime and CXX registration
work. Its scanner then exhausted the old 64 MiB `/tmp` while downloading and
extracting a replacement JRE. `probe-v6` uses the scanner image's installed
Java 21 and passes the scanner's own
`-Dsonar.scanner.skipJreProvisioning=true` property, which is present in the
pinned scanner 8.1 JAR. The scanner runs with a read-only root filesystem,
read-only source and report mounts, no Docker log driver, and a single 64 MiB
`/tmp` tmpfs for `HOME`, XDG configuration, `SONAR_USER_HOME`, and
`.scannerwork`. `probe-v6` also showed that Docker discards a stopped
container's tmpfs before `docker cp` can recover a cap-failure log. The next
attempt pre-creates and individually binds exactly two evidence files: an 8 MiB
stdout/stderr log and a 64 KiB scanner metadata (`report-task.txt`) file. The
scanner has no writable report directory, cache mount, or Docker writable
layer. These files are included in the already charged evidence reserve, so a
failure preserves its diagnostic and compute-task metadata without expanding
the temporary-space allocation.

`probe-v7` recovered the diagnostic but showed that a process-wide 8 MiB file
limit also constrained the scanner engine download. The scanner image inspection
records no preinstalled server analysis-engine cache; its runtime log identifies
the server `/api/v2/analysis/engine` download as the writer that exceeded 8
MiB. The 64 MiB scanner tmpfs was not reported full, so it remains a bounded
storage cap rather than being enlarged by guesswork. The next attempt applies
the 8 MiB limit only to a pipe log-sink. It records both the scanner and sink
statuses, writes `report-task.txt` in tmpfs, reads at most 65,537 bytes to
detect an over-64 KiB report, and copies that bounded content into the single
precreated evidence-file bind before exit.

`probe-v9` passed the CXX registration fixture: one C++ file was indexed and
the deliberate null-pointer finding was imported. It remains
`PROBE_PASSED_NOT_PRODUCT_SCAN`; it establishes the scanner path and does not
make a product coverage claim. The measured engine/plugin extraction required
the scanner tmpfs cap to increase to 128 MiB. The server caps remain 256 MiB
data, 16 MiB logs, and 64 MiB temp.

The completed `distribution-engineering-v4` compiler receipt contributes only
the 14 frozen-export translation units whose current bytes match exactly:
`zpaq_ffi`, libzpaq, and bundled libbsc. Its retained argv and source hashes
are recorded in the next preparation manifest. The remaining translation units
stay listed as compiler-closure gaps; this is not a clean product scan.

The probe charges physical blocks already used by
`benchmark-work/native-rc-check-v1`, its server and scanner tmpfs ceilings, and
a 32 MiB evidence reserve against the shared decimal 4 GB temporary-space
policy. The command records a fresh exact allocation receipt immediately before
lease acquisition and repeats it inside the worker; do not rely on a prior
directory-size observation. The probe refuses to start when the fresh accounting
exceeds the policy. Its caps are 256 MiB data, 16 MiB logs, 64 MiB server
temp and 64 MiB scanner temp. A cap failure is
evidence of an inadequate bounded probe, never a reason to enlarge it silently.

The retained native-work tree counts because it is build/job material on the
same temporary-work allocation. Immutable scanner images, the checksummed tool
packages and source inputs are recorded provenance, not temporary workspace.
No cleanup is automatic. Root may consider only unreferenced generated build
intermediates after preserving their source hashes and job receipts; previous
failed attempts and prepared manifests remain evidence and are not cleanup
eligible.
