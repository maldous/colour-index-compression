# Host adapters and constrained CLI checkpoint

The benchmark remains held and this is not a release candidate acceptance or a compression record. The preceding private checkpoint is `b7b2d1d3b`. Current Rust source/Cargo/build inputs match the frozen `constraints-v3` inputs; the installed executable comes from that job. [Machine receipts](host-adapters-evidence.json) retain successful and failed attempts.

## Qualified scope

| Boundary | Evidence and result |
| --- | --- |
| CLI constraints and PAQ admission | `constraints-v3`: all-target compilation and 46 focused Rust tests pass. Explicit native container, maximum block, backend, numeric effort and native scheduling strategy reach the appropriate native producer. CIXM6 uses its actual encoder. Incompatible outer/inner archive producers are omitted with diagnostics. |
| GNU tar and libarchive | `host-adapters-v3`: tar `-I`, explicit stdin/stdout stages, empty/multiple-member archives, exact restoration and truncation failure pass. The actual libarchive 3.7.2 program-filter consumer passes using explicit `--cix` arguments, because libarchive starts its child with an empty environment. This is an external program filter, not a registered in-process libarchive codec. |
| GIO | `host-adapters-v4`: four actual host contracts pass on GIO 2.80.0: empty/nonempty stream round trips, one-byte backpressure/flush/reset, truncation rejection and explicit cancellation. Cancellation is an atomic entry fence, not interruption of native codec work. GIO can buffer a write without calling the converter. |
| HDF5 and netCDF | `host-adapters-v6`: actual HDF5 1.10.10 plugin and netCDF 4.9.2 consumers pass. Reopened files exercise compressed chunks, optional raw fallback with its filter mask, damaged frames, persisted output limits, invalid parameters and deployment-cap rejection. Private filter ID 65001 is explicit; no public registration is claimed. |
| h5py | `host-adapters-v7`: h5py 3.10.0 with HDF5 1.10.10 and NumPy 1.26.4 writes, reopens, proves a compressed filter-mask-zero chunk, and restores exact values. It reuses the source-bound plugin from v6. |
| Relocated Linux runtime | `runtime-closure-v2`: explicit six bridges/eight companion libraries, aliases, loader closure, negative RUNPATH checks and JPEG-LS restoration pass for the current executable. `relocated-providers-v4` additionally proves actual gray/planar JXL operations and fresh-process PAQ encode/decode for all four variants at level 1. |

The HDF5 adapter now places deployment caps above file-supplied requests: 64 MiB maximum chunk/output, 512 MiB native memory admission and four workers by default. These are configurable build limits, and native admission is not an operating-system RSS guarantee. Serialized file metadata cannot increase them.

## Failures preserved and corrected

- `constraints-v1` exposed an obsolete test diagnostic and an unsuccessful BEST child; the latter passed after restoring the incumbent baseline block behavior. `constraints-v2` proved that passing `cixm6` into the CIXG producer did not enforce its wire. The corrected real M6 dispatch passes in v3.
- The first installed PAQ probe used level 0. v215 encoded but decoded with SIGSEGV both at 512 MiB and 1 GiB; level 1 passed. Inspection of all four unchanged pinned upstream trees found that level 0 leaves the predictor null while the filter dispatcher dereferences it. The CIX worker now rejects level-0 encoding and exact level-0 archive headers before DSO invocation. All four actual worker rejection paths return an error without publishing output. Catalogue levels 8/9L are retained. Direct unsupported calls to upstream DSOs remain outside the worker's admission contract.
- Host adapter failures include GIO conversion ordering/syntax/linkage, HDF5 lazy write checks and missing `lib` plugin prefix, libarchive's non-shell command parser and empty environment, and an incomplete h5py dependency provision. Every attempt remains recorded rather than overwritten.
- The GIO cancellation test initially assumed a buffered GIO write must fail immediately on cancellation. The adapter now provides and tests its explicit converter cancellation fence, with truthful host-buffering semantics.

HDF5's filename requirement is confirmed in its [pinned loader source](https://github.com/HDFGroup/hdf5/blob/hdf5-1_10_10/src/H5PLpath.c). GIO progress, error and flush behavior follows the [public converter contract](https://docs.gtk.org/gio/method.Converter.convert.html).

## Resources and remaining work

All codec/build checks used root's existing scheduler, physical CPUs 8/10/12/14, finite memory reservations within the shared decimal 12 GB ceiling, decimal 4 GB workspace cap and no swap. Sampled cgroup memory is explicitly a lower bound, not a true process peak. These small generated checks are not throughput benchmarks. The extracted .NET SDK was verified member-for-member against its retained publisher archive before removing the redundant expanded copy (`consumer-space-v3`).

Blosc2, QuixDB Squash, WiredTiger, 7-Zip and Hadoop adapters still need installed-host qualification. Their source-only state does not establish working interoperability. Full-engine bounded streaming, useful parallelism evidence, remaining adapters/filesystem work, source export, final quality/Sonar, optimized packaging and actual platform runners remain open. Native SquashFS and stock registry support are not implied by these checks. No required RC item is waived, no new corpus is acquired and no public repository, Actions or Site is enabled.

The next bounded action is to qualify the pinned Blosc2 and QuixDB Squash host boundaries, preserving any failures and their exact dependency identities.
