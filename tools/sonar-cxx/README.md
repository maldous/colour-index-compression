# CIX C/C++ Sonar analysis

The pinned SonarQube Community Build 26.9 image does not include commercial
CFamily. This runner installs the checksummed SonarOpenCommunity CXX 2.3.0.1496
plugin into each ephemeral scan server and imports real Cppcheck 2.13.0 findings.
It does not claim to install or reproduce SonarSource's licensed analyzer.

Remediation is restricted by the user's instruction to CIX-owned source,
adapters, wrappers, build configuration and analysis tooling. Do not correct
external upstream or vendored C/C++ source, including bundled/forked PAQ trees,
to clear findings. Keep third-party source identities unchanged and report its
findings separately. Scanning vendor code does not authorize editing it; retain
its findings without suppressing them to manufacture a clean result.

The current projects cover `rust/cix-native` core, adapters/bindings/consumer
sources, bundled libbsc/libzpaq, and the unchanged PAQ v215, v216,
joint-discount and store-state dependency roots. The CIX-owned PAQ bridges are
part of the core project. Vendor findings stay in separate projects and do not
authorize vendor changes. Two CUDA headers are inventoried separately:
CUDA/OpenMP are disabled in `rust/cix-native/build.rs` and CUDA is outside this
C/C++ analysis.

Preparation uses the current repository root. PAQ settings come from retained
compilation databases; host-adapter settings may come only from completed CMake
`flags.make` receipts after current source hashes match their compiled source
copies. It does not invent flags from CMake text. Every translation unit without
an exact receipt is recorded in `unconfigured_translation_units`; the prepared
plan is blocked and the runner refuses to start a server. This prevents a partial
scan from being presented as clean. Cppcheck configuration exploration remains
bounded to 12 configurations.

Every full scan and registration probe has a 96 MiB aggregate retained-evidence
ceiling. The runner admits JSON, XML and text before writing them, using
4 KiB-rounded allocation accounting from the attempt root and retaining a
256 KiB failure-receipt reserve. Cppcheck uses a process-group-isolated,
selector-drained stdout/stderr capture: the combined pipes are killed before
over-limit bytes are written. The scanner reserves its 8 MiB log sink plus
bounded metadata before it is launched. The local result collector applies the
same admission checks to task, issue and quality-gate responses; it does not
use the general runner's unbounded collector.

The server is read-only, uses no Docker log driver, and has only its declared
bounded Sonar tmpfs paths: data, logs, temp, extensions and `/tmp`. Its wrapper
invokes the recorded pinned-image entrypoint, copies startup output into the
bounded log tmpfs, and leaves an exit marker for an immediate readiness failure.
On failure the runner retains no more than 64 KiB from those in-container logs
through a bounded `docker exec` tail. Cppcheck
uses the staged dynamic-loader closure while preserving the host architecture
header tree through a read-only alias overlay. Five recorded GIO and 7-Zip
translation units are projected with their recorded compiler `-E` commands;
only GNU line-marker spelling, GCC diagnostic pragmas, and unquoted
`__extension__` annotations are normalised in that analyzer copy. The source
and vendor inputs remain unchanged and every projection records both hashes.

These controls bound retained evidence, not a remote service's in-memory API
response or the Sonar server's configured tmpfs. A limit failure preserves the
small failure receipt when prior retained evidence left the documented reserve;
it does not turn a partial scan into a successful analysis.

```sh
python3 tools/sonar-cxx/repair.py provision
python3 tools/sonar-cxx/repair.py prepare --out docs/research/2026-10-04-execution/sonar-preparation/prepared-current
python3 tools/sonar-cxx/repair.py run --prepared docs/research/2026-10-04-execution/sonar-preparation/prepared-current --out docs/research/2026-10-04-execution/sonar-preparation/scan-current
```

Before the compiler closure is complete, root may run the guarded plugin probe:

```sh
python3 tools/sonar-cxx/repair.py probe --out docs/research/2026-10-04-execution/sonar-preparation/probe-v1
```

It uses the same authenticated stop receipt, idle check, scheduler lock,
physical-core lease and resource slice as a full scan. It verifies local pinned
images and package hashes, CXX registration, CXX/Cppcheck rule activation, and
the intentional null-pointer fixture. Its success is explicitly
`PROBE_PASSED_NOT_PRODUCT_SCAN` and cannot satisfy source coverage.

Do not repeat `prepare` or `run` into an existing output directory. The old
`prepared-v1` is historical and does not describe current source. Full execution normally requires all 36 frozen
Silesia cells to be VERIFIED with the matching plan hash and identities. The
only alternative is the user-authorized stop: the runner pins the exact plan
hash, committed stop receipt and its hash, exactly five verified cells, one
named interrupted encode cell, and thirty named unstarted cells. It rejects
tampering, restart permission, unknown states, live confirmation
processes/cgroups/units, or failure to obtain the exclusive scheduler lock and
core leases before scanning. This hygiene-only exception never certifies the
interrupted confirmation.
It then obtains the existing exclusive WaveScheduler lock/core leases and uses
a verified four-core, 5 GiB, no-swap systemd slice for server, scanner and
Cppcheck. No frozen product source or binary is modified. Scan outputs are new
evidence, not alterations of historical unscanned/clean results.

The runner requires actual `cxx` registration, enables CXX and Cppcheck rules,
and first proves a deliberate null-pointer fixture appears as a Sonar issue.
It then reads back every project's indexed CXX file list, issues, completed
analysis and quality gate. Missing files, an inactive analyzer, parse failures,
or a missing probe issue fail the run. A successful scanner process alone is
insufficient. Findings are retained rather than suppressed to obtain a clean gate.

The 26.9 server/plugin pairing is not listed as an upstream tested pairing
(upstream tests 26.1/25.8); actual compatibility remains pending the scheduled
server start and probe. If the run fails, preserve its evidence, correct the
scanner configuration, and use a new attempt directory. Do not report this repair
as verified until the probe and all seven projects finish with complete coverage.

The existing benchmark agent owns post-confirmation execution and correction.
Small metadata/guard tests can run now with:

```sh
python3 -m unittest discover -s tools/sonar-cxx -p 'test_*.py' -v
```

Sources: [CXX release](https://github.com/SonarOpenCommunity/sonar-cxx/releases/tag/cxx-2.3.0),
[installation](https://github.com/SonarOpenCommunity/sonar-cxx/wiki/Install-the-Plugin),
[compatibility](https://github.com/SonarOpenCommunity/sonar-cxx/wiki/Compatibility-Matrix),
[rule activation](https://github.com/SonarOpenCommunity/sonar-cxx/wiki/Manage-Quality-Profiles).
