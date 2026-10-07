Prepared artifact derivation only; **UNRUN**. The technical owner must first bind
one bounded helper in the existing system `/cix.slice/cix-bau139.slice`, account
for the public runtime copy, BEAMs and logs, and bind the exact preparation pins.
The builder requires CPU affinity 0, at most 2 GB memory and swap 0. No service,
tracker, credential operation, source edit, accepted check replay or installation
is part of this derivation.

Run `build-overlay.py` once inside that admitted helper. The fixed NEW output is
`/home/user/src/cix-approved-migration/runtime-cix243-v1`; an existing output is a
hold, and failed partial output is preserved. Inputs are the exact reviewed v2
source hashes and public installed Elixir 1.19.5 / ERTS 16.4 closure. Eight source
units are compiled: seven changed reviewed units plus the unchanged
`Tracker.Issue` foundation verified against exact upstream base `1c0fb6`. The
original runtime and source are read-only. No mix/dependency/full product build.

Only `lib`, `erts-16.4`, consolidated protocols and selected extracted release
entry/clean-boot files are copied. The old release COOKIE, workflows, credentials,
auth state, logs, scratch and root-level files are omitted. External symlinks are
rejected. The existing external `/tmp` musl interpreter remains an explicitly
pinned public dependency; this is not a fully self-contained native rebuild.
The compile VM receives an allowlisted environment without auth variables.

Outputs include `overlay/ebin/*.beam`, `overlay/beam-manifest.json`, the exact
source/BEAM/compiler/runtime closure pins, derivation log/result and measured
cgroup usage. Actual artifacts do not exist yet. A derivation result would qualify
only artifact construction, not service startup, live API persistence or broader
OS/AppServer cleanup.

Smallest supported entry: the copied official extracted `bin/symphony eval`
boots cleanly, evaluates `bootstrap.exs`, verifies all BEAM hashes, explicitly
loads the overlay before Symphony starts, then invokes the existing official
`SymphonyElixir.CLI.main(System.argv())`. The wrapper preserves all original CLI
arguments and its guardrails acknowledgment. Distribution is disabled and an
unused local cookie is supplied so no release COOKIE is read/copied. The old
Burrito executable is not relabeled as containing the extension.

Technical owner next binds the derived manifest, runtime root, effective entry,
workflow `failure_isolation_enabled` and exact context, ordinary existing auth
source, logs and system-service resources. Entry execution/activation is a
separate step. `preparation-pins.json` identifies these prepared inputs; this
preparation does not modify the existing activation or service configuration.

Before service binding, run the prepared `verify-argv.sh` inside the same admitted
artifact helper after derivation. It uses the copied official release eval entry
and checks exact arguments, including spaces and the acknowledgment flag, while
asserting that Symphony is not started. It calls no CLI, workflow, tracker or
scheduler. This probe is currently UNRUN; successful output must be retained
before claiming effective argument forwarding. The production wrapper uses the
same quoted `"$@"` forwarding inspected here.
