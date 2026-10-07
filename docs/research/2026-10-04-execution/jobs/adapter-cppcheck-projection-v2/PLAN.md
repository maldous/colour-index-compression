# Adapter Cppcheck projection prerequisite v2

v1 is retained as a failed pre-Sonar attempt: its canonical CIX decompressor
source lost the source-relative `upstream/` quoted-include directory from the
successful kernel stage. v2 runs only after `sonar-tool-tests-v17` passes.

It uses the same frozen 55 CIX source hashes and 43 compiler records as v4.
For the decompressor only, it appends `-iquote` with the exact retained
`kernel-module-v4/stage` directory. That directory comes from the successful
module-v4 receipt; the runner checks its receipt, manifest, current owned
source hash, CIX stage-copy identities, and every staged upstream header hash
before preprocessing. The filesystem-register row receives no `-iquote`; its
stage-local context is still bound and checked.

The runner does compiler preprocessing only and starts no Sonar or Docker. Its
normal limit remains 2 MiB; the decompressor and filesystem-register sources
alone retain the reviewed 8 MiB cap, within the shared 96 MiB evidence budget.
