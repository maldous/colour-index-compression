# PPM model-control helper qualification

Reviewed helpers retain model summation order, exclusion updates, strict
candidate ties, SEE updates and bounded prefix-history initialization.
`raw/` retains parent `40d` versus candidate fixed and SEE payload digests,
bidirectional fresh-process cross-decodes, all escape methods 0–3 for
v3/v4, prefix restoration, malformed-header rejection and binary identities.

Direct parent/candidate harness cgroup readbacks are retained. The later
all-method fresh processes were not individually cgroup-wrapped: those
results establish correctness only, not timing or resource qualification.
The harness source is `rust/cix-native/benches/ppm_sonar_audit.rs`; it is a
local audit target, not a production encoding policy or throughput benchmark.

The separate terminal-varint guard retains portable usize::MAX and rejects
excess high bits before shifting; 14 PPM tests passed on this host. No 32-bit
binary was built. Combined optimized validation remains due after all
reviewed changes are integrated.
