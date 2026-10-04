# Native regression v1 dispatch plan

This recipe is prepared for root dispatch after root has confirmed the final
lint-remediated source. It must not run against the mutable checkout. Root
creates the new `execution-native-regression-v1` source snapshot, including
its `Cargo.lock`, and writes the adjacent freeze record named in `spec.json`.
That JSON record must set `approved_by_root` to true, repeat the snapshot
manifest and lockfile SHA-256 values, and contain an exact
`source_files_sha256` mapping of every regular source file relative to the
snapshot root. The helper recomputes that complete mapping before it creates
work. It requires `CIX_RELEASE_LEASE=1` and records the snapshot, freeze record
and full source identity; it does not claim an unrecorded revision was tested.

The scheduler owns the shared `benchmark-work/native-rc-check-v1` directory.
The helper requires its `native-regression-v1` child to be absent and creates
only that child, including a mode-0700 temporary directory. PAQ’s runtime
validates every ancestor, so its mode-0700 root is the fresh,
job-owned `/home/user/.cache/cix-paq-native-regression-v1` rather than the
shared benchmark directory; root reclaims that empty root after the job.
Cargo’s shared target directory is outside the child and is subject to root’s
separate cache-reclamation work. The scheduler reserves 3,936,000,000 bytes of
its temporary allowance and the PAQ root reserves the remaining 64,000,000
bytes. The helper samples that external root every 0.2 seconds through every
Cargo phase, records the sampled peak, and terminates the complete Cargo
process group if it crosses 64 MB. The aggregate is therefore within the
decimal 4 GB ceiling. The job declares four CPUs, 12 GB memory, no swap, and no
concurrent heavy job. Test execution is serial (`--test-threads=1`) while
compilation is bounded to four jobs. Both dev and test debug information are
disabled for this disposable qualification build to limit target-directory
growth; this changes no product build setting or performance claim.

The full `--lib` run is intentional. It activates the installed bridge tests
only when their variables are present. Before Cargo starts, the helper requires
and hashes the JXL bridge, spatial bridge, and every one of the four PAQ shared
libraries. It builds `cix` first, supplies that fresh binary through
`CIX_TEST_EXECUTABLE`, and supplies the PAQ directory plus a private root
through `CIX_TEST_PAQ_LIBDIR` and `CIX_TEST_PAQ_WORKROOT`. That makes PAQ’s
opt-in parent lifecycle test run all four variants; it does not describe an
absent provider as a skip. JXL and spatial are likewise present and configured
before their library tests begin.

The second invocation targets public C ABI, dictionary, CLI/full-engine job,
resource admission, and incremental/pipe/window transport tests. The recipe
does not run portfolio or compression evaluation suites and records no size or
speed comparison. A pass establishes only the named regression contracts on
the recorded source and provider identities; it is not package-manager,
distribution, or release acceptance evidence.
