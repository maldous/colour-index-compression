# Share library codec instances and preserve independent boundary oracles

The independently reviewed library change replaces duplicate module loads with
public reexports of the existing CLI modules. Twelve codec module declarations
become public in main.rs. Public library paths and native format remain the same;
library calls now use the same codec globals as its included CLI. No CLI
throughput improvement is claimed from this structural change.

PPM fallback iteration preserves ascending symbol order. Its existing test
module moved unchanged in coverage to the end of the file. Rescale assertions
retain independent arithmetic oracles, including maximum-u32 cases. The rank
lowest-bit test uses a trailing-zero oracle rather than duplicating production's
builtin; all original boundary values remain.

Direct stable cargo check of the library and binaries exited 0. The separate
CPU 8 / 1 GiB/no-swap scope ran two PPM rescale tests and one rank boundary test:
all three passed. The two cargo child membership/affinity snapshots and the
scope limits/peak are retained. The compile check finished before an attempted
child sample, so its empty sample is not resource proof. This is compile and
focused correctness evidence; full optimized validation, CLI compatibility and
fresh Sonar are required on the next combined release. No new performance
measurement or zero-warning claim is made.

Raw source patch/base identity, executable runner, logs and exits are retained
in raw/. The runner inherited explicit stable RUSTC/RUSTDOC and a dedicated
root-owned target directory. Production allocators and encoding choices were
not changed. Existing incomplete warning-remediation attempts are separate.
