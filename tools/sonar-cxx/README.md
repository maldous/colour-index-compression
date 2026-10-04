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

The six scan projects cover the first-party bridge and Squash adapter, native
libbsc/libzpaq, and PAQ v215, v216, joint-discount and store-state source trees.
There is no vendor exclusion. Two CUDA headers are inventoried separately:
CUDA/OpenMP are disabled in the frozen native build and CUDA is outside this
C/C++ analysis. Operating-system SDKs and binary-only dependencies are not source
code in this export.

Preparation uses the immutable release source export. PAQ analysis settings are
rebased from retained compilation databases after translation-unit byte checks;
native settings are derived from frozen build.rs. These are explicitly analysis
configuration, not a new compilation or fresh build-wrapper capture. Source files
outside the databases remain in CXX's AST scan. Cppcheck configuration exploration
is bounded to 12 configurations and uses the recorded Linux build settings.

```sh
python3 tools/sonar-cxx/repair.py provision
python3 tools/sonar-cxx/repair.py prepare --out docs/research/2026-10-04-sonar-cxx-repair/prepared-v1
python3 tools/sonar-cxx/repair.py run --prepared docs/research/2026-10-04-sonar-cxx-repair/prepared-v1 --out docs/research/2026-10-04-sonar-cxx-repair/scan-v1
```

Do not repeat `prepare` or `run` into an existing output directory. The current
prepared-v1 already exists. Full execution normally requires all 36 frozen
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
as verified until the probe and all six projects finish with complete coverage.

The existing benchmark agent owns post-confirmation execution and correction.
Small metadata/guard tests can run now with:

```sh
python3 -m unittest discover -s tools/sonar-cxx -p 'test_*.py' -v
```

Sources: [CXX release](https://github.com/SonarOpenCommunity/sonar-cxx/releases/tag/cxx-2.3.0),
[installation](https://github.com/SonarOpenCommunity/sonar-cxx/wiki/Install-the-Plugin),
[compatibility](https://github.com/SonarOpenCommunity/sonar-cxx/wiki/Compatibility-Matrix),
[rule activation](https://github.com/SonarOpenCommunity/sonar-cxx/wiki/Manage-Quality-Profiles).
