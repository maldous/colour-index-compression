# C/C++ quality-gate preflight

Prepared evidence is **not** a completed scan. RC46 requires a fresh execution
against the final source identity; RC47 follows only after its retained result.

## Gate status

`tools/sonar-cxx/repair.py` already has the required user-stop alternative. If
all 36 cells are not verified, it calls `require_stopped_confirmation`, which
pins the committed stop receipt and plan hashes, validates exactly five
verified cells, the named interrupted Mozilla encode, and thirty unstarted
cells, requires no automatic restart, then checks processes, units, cgroups,
the WaveScheduler lock, and four core leases. The worker repeats the receipt
check. This is the required narrow hygiene exception. No code correction is
justified.

## Callable tooling

The checksummed CXX 2.3.0.1496 plugin and extracted Cppcheck 2.13 are present
under `/home/user/src/cix-sonar-cxx-tools`; the runner creates an ephemeral
local server and scanner. The remaining live compatibility question is the
prepared SonarQube 26.9 / CXX 2.3 pairing, which the null-pointer probe checks
before CIX source analysis. It has not been exercised in this preflight.

## Source identity blocker

`prepared-v1/plan.json` binds the old immutable export
`/home/user/src/cix-integrated-source-candidate`, with its 1,346-file manifest
and old build metadata. It cannot qualify the subsequently changed final RC.
The runner correctly rejects a differing inventory. Prepare a new immutable
final-source export and new `prepared-v2` manifest first; do not alter
`prepared-v1` or its receipts.

## Later command

After root creates and verifies that final export, prepares a unique directory,
and confirms the user-stop/idle state is still true:

```sh
python3 tools/sonar-cxx/repair.py run \
  --prepared docs/research/2026-10-04-sonar-cxx-repair/prepared-v2 \
  --out docs/research/2026-10-04-sonar-cxx-repair/scan-v2
```

The command itself acquires the exclusive lease and records tool/source
identities. It must not be run concurrently with builds or benchmarks. A scan
result is required before any claim of fresh C/C++ analysis or quality closure.
