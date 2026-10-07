# Adapter Sonar context probe v3

Root dispatches this one-scope probe only after the passing
`sonar-tool-tests-v15` receipt exists. It preserves v1 and v2 untouched.

## Frozen inputs

`frozen-scope.json` binds exactly the 55 paths from `prepared-v6` and the 43
retained compiler records. Three source bytes are deliberately newer than that
preparation: the SquashFS userspace profile, Node binding, and Squash contract.
They are current **analysis inputs** only. Their hashes are frozen before the
probe and checked both before and after it; no historical compiler-build claim
is made for them.

The command database remains historical compiler context for static analysis.
The runner does not alter it. `repair.py` may compiler-preprocess only its
reviewed fourteen translation units: the prior GIO/7-Zip set, six established
context targets, and the three diagnostic-bearing raw records from v2. It
records the compiler argv, isolated sandbox argv, projection digest, and any
removed dependency-output operand for every projection. The three kernel rows
must also carry fresh `NEW_ANALYSIS_INPUT_FREEZE_NOT_HISTORICAL_BUILD_PROOF`
evidence for their forced headers.

## Acceptance

The execution must retain direct include-context evidence for all 43 records,
index the frozen 55 sources, and preserve ordinary findings. It must reject
source or tool drift. It additionally rejects any retained Cppcheck
`preprocessorErrorDirective` or `unknownMacro` diagnostic, any projection count
other than fourteen, absent network-isolated compiler preprocessing, or absent
fresh kernel input evidence. Passing this bounded probe is not a full scan or
runtime qualification.

The root-owned lease retains the existing 12 GB aggregate memory, 4 GB temporary
capacity, four leased CPUs, exclusive scheduler lock, bounded evidence, and
cleanup contract. The recipe does not build product artifacts.
