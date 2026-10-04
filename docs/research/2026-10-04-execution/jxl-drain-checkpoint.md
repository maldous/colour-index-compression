# Shared JXL output boundary

Both native JXL encoder entry points now use one private output-drain helper.
The helper retains the existing 4 KiB scratch buffer, pre-insertion output-cap
check, error mapping, and final C-buffer allocation. Image configuration,
public ABI, provider source, and decoder behavior are unchanged.

`jobs/jxl-drain-contract-v1` passed a fresh Release bridge build and an
optimized `-DNDEBUG -Wall -Wextra -Werror` contract. The contract verifies gray
8/16-bit and planar exact round trips, an output cap one byte below the
produced archive, null/zero output on rejection, and appended-byte rejection.
The retained regression scripts also passed six gray and eighteen planar
cases, including independent imagecodecs decoding and native decoding of
reference streams. These are generated focused checks, not corpus results.

All six new native gray archives match the retained pre-refactor archives
byte for byte. The planar report records reference-encoder hashes; its eighteen
passing cases establish cross-interface decoding, not a native before/after
bitstream comparison. Source and pinned dependency hashes remained unchanged
through the job.

The new bridge is isolated in the job's installation prefix. It is not yet
the selected final distribution provider. This maintenance change makes no
compression-ratio or throughput claim and does not reopen benchmarking.
