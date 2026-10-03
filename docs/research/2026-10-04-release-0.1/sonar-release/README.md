# Release-export Sonar harness

`run_release_scan.py` is a root-only, lease-gated local Sonar scan for the
standalone `/home/user/src/cix-0.1-release` export. It does not accept a Git
revision because the export has no repository metadata. Instead it computes a
sorted, path/mode/content SHA-256 tree digest, excluding only generated Cargo
and scanner directories. The expected digest is checked before container
startup and again after Clippy.

`schedule_release_scan.py` consumes the separately scheduled, bounded,
warnings-denied `cargo-clippy-v2` JSON receipt. It refuses to start unless that
receipt passed, and then starts the scanner only if the export tree is
unchanged. It preserves the earlier bounded Docker
configuration, importer accounting, scrubbed container inspect records, and
token lifecycle receipt. The source is mounted read-only and the temporary
token file is removed in cleanup.

The harness is prepared only. Root owns the scheduler lease and execution.
