# Sonar CXX evidence-budget review v3

**Scope:** read-only adversarial review of `tools/sonar-cxx/repair.py` after
`probe-v12`, with `scan-v3` left untouched.  This review covers the Sonar
server contract, bounded evidence retention, and the outer slice receipt.  It
does not make a claim about findings from the active scan.

## Result

No remaining blocker was found in the reviewed paths.

The successful probe records a 4,000,000,000-byte temporary-work policy and a
3,935,105,024-byte reservation, leaving 64,894,976 bytes.  The reservation
charges 3,314,348,032 bytes of retained native work, all six tmpfs ceilings
(520,093,696 bytes), and 96 MiB of evidence.  Image layers and packaged tools
are deliberately recorded as immutable provenance rather than temporary work.

## Server writable-state contract

The inspected server image declares exactly these Docker volumes:

- `/opt/sonarqube/data`
- `/opt/sonarqube/extensions`
- `/opt/sonarqube/logs`
- `/opt/sonarqube/temp`

`server_start_contract()` applies `--read-only` and mounts each of those paths
as a size-bounded tmpfs: data 256 MiB, extensions 16 MiB, logs 16 MiB, and temp
64 MiB.  It also bounds `/tmp` to 16 MiB.  The recorded
`server-start-contract.json` lists the same image-volume and bounded-volume
sets, so none of the image-declared writable volumes falls back to Docker
managed storage.

Both server and scanner specify `--log-driver none`; server output is drained
through a wrapper that retains only the first 65,536 bytes in its bounded logs
tmpfs and sends the rest to `/dev/null`.  The retained host-side server log is
collected through a 65,536-byte bounded pipe.  The wrapper leaves the
container alive after the entrypoint exits solely to expose a small exit marker;
`wait_server_or_exit()` reads that marker and fails early.  The enclosing
`finally` stops and removes the named server in every normal, startup-failure,
and later-analysis path.

The scanner uses the same read-only-root/no-Docker-log policy, has only a 128
MiB `/tmp` tmpfs, and binds one pre-created, size-reserved evidence file.  Its
log sink has an 8 MiB file limit and rejects report-task metadata larger than
65,536 bytes before retaining it.

## Evidence admission and receipts

`EvidenceBudget.admit()` calculates allocation before creating a path.  It
charges the target allocation, a prospective directory entry, and both the
new directory block and possible parent-directory growth for every missing
directory.  File writes then recheck physical allocation after the write.
External scanner evidence is reserved before the container starts and is
accepted only after its actual size and block allocation meet the declared
limit.

Ordinary evidence preserves a 256 KiB failure-receipt reserve.  Optional
failure diagnostics preserve a separate 64 KiB terminal-result reserve, and
`save_terminal_result()` compacts its JSON to that maximum when necessary.  The
parent `run()` and `probe()` paths use the same `EvidenceBudget` to write
`slice-receipt.txt` after the worker returns; this is pre-write checked and
fails closed rather than exceeding the evidence allocation.

## Evidence reviewed

- `docs/research/2026-10-04-execution/sonar-preparation/probe-v12/raw/temporary-accounting.json`
- `docs/research/2026-10-04-execution/sonar-preparation/probe-v12/raw/server-image-inspect.json`
- `docs/research/2026-10-04-execution/sonar-preparation/probe-v12/raw/server-start-contract.json`
- `tools/sonar-cxx/repair.py`
