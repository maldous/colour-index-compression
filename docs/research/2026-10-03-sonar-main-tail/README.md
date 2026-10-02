# Encoder helper extraction

Base source a628bda23, tree `74c5b9c90d1e554b1f87089b6a5a1c758630073b.
The independently reviewed source patch preserves M6 trial order, complete cost,
strict ties, admission, state/history updates, error handling and EINTR behavior.
Raw source, command journal, binary hashes, build logs and parity artifacts are
retained in raw/ and bound by its manifest.

The 512-byte zero fixture has two 256-byte frames, selected modes 1 then 9.
Complete archives are identical and the candidate restores the baseline archive.
Other selected model paths have static equivalence review, not dynamic coverage
in this tiny check. CPU16/1GiB/no-swap launch properties and successful service
completion are recorded. The original internal readback stdout was not retained;
no independent per-binary child readback is claimed.
