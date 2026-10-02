# Raw qualification artifacts

`cixg1-idle-probe.json` and `cixg1-idle-probe-executed.py` are the executed CIXG1 pipe probe. They establish CIXG1 idle/slow behavior only.

`m6-incremental-probe.json` records the initial header-only observation. `m6-pipe-probe-invalid.py` is retained as `INVALID_MEASUREMENT`: it counted decoded bytes after EOF. `m6-pipe-probe.json` is the corrected bounded 60-second CIXM6 relay probe; its `before_eof` object is captured before closing encoder stdin and then the completed restore is verified separately.

`binary-identities.txt` contains frozen/candidate executable hashes and the candidate loader resolution captured after execution. M6 archive/cross-decode and malformed command results remain in `../m6-qualification.json`.
