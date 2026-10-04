# Adapter Cppcheck projection prerequisite v1

Run only after the passing `sonar-tool-tests-v16` receipt and before the v4
Sonar recipe. The runner freezes the same current 55 sources and 43 retained
compiler records as v4, validates all direct include mappings, then invokes
only the reviewed compiler preprocessing projections. It never starts Docker,
Sonar, or a scanner.

The normal per-TU output and `RLIMIT_FSIZE` cap remains 2 MiB. Only
`cix_squashfs_decompressor.c` and `cix_squashfs_fs_register.c` may use 8 MiB,
because v3 recorded the former failing at the 2 MiB limit. All projection bytes
remain admitted by the shared 96 MiB evidence budget. The receipt rejects any
other enlarged cap or source/tool drift.
