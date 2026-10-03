# Pre-held-out duplicate quarantine

After development extraction and fitting, but before any held-out extraction,
the frozen input hash ledger identified identical 4096-byte samples for
development `canterbury-ptt5` and held-out `calgary-pic`. The latter remains in
the CCA integrity screen but is excluded from all primary held-out decisions,
mixture tables, null matrices and marginal-value calculations. It is reported
separately with an explicit exclusion flag. The other 13 real held-out files
remain the decision set; two Artificial files are diagnostics only.

This amendment does not change experts, extraction, weights, online rules,
hyperparameters, development membership, or gate thresholds. No held-out losses
were inspected. Original analysis and freeze are preserved in
`analyse-before-exposure-amendment.py` and
`freeze-before-exposure-amendment.json`. A numerical reporting correction also
sets highest-probability ties to absolute tolerance 1e-12 with zero relative
tolerance. The trained.json bytes remain unchanged.

The earlier build-v1 selfcheck failed only because its expected PPM mass used
method-0's 256/257 instead of frozen method-1's 1/2. The native result was 1/2.
Build-v2 corrects that test expectation and column names before real tracing;
raw failure and success receipts are retained. The earlier pre-build run-length
review correction moved its update after observation; no real trace used a
target-informed run feature.
