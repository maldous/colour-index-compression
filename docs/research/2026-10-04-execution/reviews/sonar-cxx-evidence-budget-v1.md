# Sonar C++ evidence-budget review v1

Read-only adversarial review of `tools/sonar-cxx/repair.py` current at review time.
No scan, test, or source-tool mutation was performed.

## Blocking cap/accounting gaps

1. **The Sonar server has an unaccounted writable Docker layer.** Both `execute` and
   `execute_probe` start the server without `--read-only`. Only the three declared
   Sonar tmpfs paths are charged in `probe_temporary_accounting()`. Writes elsewhere
   in the container root filesystem use Docker's writable layer and can consume host
   temporary storage outside the 4 GB calculation. The scanner container correctly
   has `--read-only`; the server needs the same property after every required writable
   path is explicitly mounted as a bounded tmpfs.

2. **The Sonar server uses Docker's default log driver, which is not accounted or
   bounded.** The server launch also lacks `--log-driver none` or an equivalent
   explicitly bounded driver. Its stdout/stderr can therefore create an engine-side
   JSON log outside `/opt/sonarqube/logs` and outside the 96 MiB evidence budget.
   The later `docker logs` call reads that external log with `capture_output=True`, so
   it also has no input-size cap before it reaches process memory. A repair must make
   server logging bounded and account for its retained physical allocation; merely
   bounding the in-container Sonar log tmpfs is insufficient.

3. **`EvidenceBudget.admit()` does not charge a new file's directory entry.** It
   charges missing directories and the file allocation, but a write into an existing
   directory can grow that directory by an allocation unit. A sequence of small new
   files near the 96 MiB boundary can therefore pass pre-write admission and leave
   `allocated_bytes(out)` above the cap. Charge one allocation unit for a new entry
   (or prove/reserve exact parent growth before the write), and enforce the measured
   total after every mutation as a fail-closed backstop.

## Failure-path gap

`failure_reserve` does not actually guarantee a final failure receipt. `write_*` with
`failure=True` may consume the entire nominal limit; both worker `finally` blocks
write the potentially unbounded `docker logs` capture with that flag before writing
`result.json` with the same flag. If prior evidence nearly fills the budget, the log
can consume the reserved 256 KiB and the subsequent result receipt can fail. Container
stopping remains nested in `finally`, so the stop attempt is present, but preservation
of the failure reason is not guaranteed. Reserve a receipt allocation that no failure
log is permitted to consume, or write the small terminal receipt before any optional
failure log.

## Confirmed controls

- `collect_bounded_pipes()` drains stdout and stderr together, compares their combined
  retained bytes with `budget.remaining()`, and kills the isolated process group on
  timeout or excess before returning data for persistence.
- The scanner uses a read-only container, bounded tmpfs, no Docker log driver, and a
  pre-created external log file. `commit_external()` rejects a symlink, apparent-size
  excess, or allocation excess before the file is retained.
- `bounded_scanner()` and both outer workers call container stop from `finally` paths.
  This addresses normal scanner/server cleanup but does not cure the unaccounted
  writable layer or engine log above.
