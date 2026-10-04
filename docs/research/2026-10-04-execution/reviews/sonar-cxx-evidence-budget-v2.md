# Sonar C++ evidence-budget follow-up v2

Read-only review of the latest `tools/sonar-cxx/repair.py`. No execution was performed.

## Verified repairs

- Both Sonar server launches now use `--read-only` and `--log-driver none`. The
  declared data, logs, and temp tmpfs paths are therefore the server's writable
  storage, and engine-side stdout/stderr logging is disabled.
- `bounded_server_log()` reads at most 64 KiB from the server's bounded log tmpfs
  through `collect_bounded_pipes()`. It replaces the unbounded `docker logs` capture.
- The scanner remains read-only, uses no Docker log driver, and keeps its host-bound
  evidence file checked before retention. Preprocessor projections have an RLIMIT,
  a per-unit reservation, and bounded stdout/stderr collection.

## Remaining correctness issues

1. **Pre-write evidence admission still undercounts a new file entry in an existing
   directory.** `EvidenceBudget.admit()` remains:
   `used - old_file_allocation + missing_directory_bytes + rounded(file_size)`.
   It does not reserve the allocation that an existing parent directory may need for
   the new entry. `write_bytes()` and `symlink()` therefore can take actual
   `evidence_allocated_bytes()` over 96 MiB after an admitted write. This now applies
   to the new projected-TU and header-overlay paths as well. Charge an allocation unit
   for a nonexistent final path (including symlink creation), or pre-reserve measured
   parent growth; then enforce the actual total immediately after each mutation.

2. **The failure receipt reserve is still not exclusive.** Bounded server-log capture
   correctly uses `budget.remaining()` with the normal reserve subtracted, but the
   following `budget.write_text(..., failure=True)` is allowed to consume the 256 KiB
   receipt reserve. A near-cap attempt can thus leave less than the full receipt
   reserve for `result.json`. Make optional failure logs use normal admission, or
   persist `result.json` before the log and reserve its measured maximum separately.

3. **Outer slice receipts also use `failure=True`.** `run()` and `probe()` instantiate
   a fresh `EvidenceBudget(out)` and append `slice-receipt.txt` with `failure=True`.
   This bypasses the configured receipt reserve after the worker returns. Use normal
   admission for this optional receipt, or reserve it as a fixed part of the worker's
   terminal receipt plan.

The nested `finally` structure still attempts scanner/server stop even if the bounded
log or result write fails. The remaining issues concern strict cap preservation and
receipt retention, not absence of a stop attempt.
