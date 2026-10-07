# Numeric representation × incumbent M6 composition

Experiment `composition-m6-citytemp-v1-buildfix1` tests the finite paid SMC1 transform
family against the frozen incumbent CIXM6 body on one 4 KiB numeric slice. It
does not change production, select by filename or format, or generalize to a
corpus. `FORMAT.md` defines the complete archive; `EXPOSURE-REVIEW.md` defines
the receipt-limited eligibility statement.

The root scheduler builds the reviewed wrapper against the sealed d3a2 rlib,
deps and native directory, linking `-lzstd`. It then runs one comparison phase
under a single CPU8 / 100% quota lease with 2 GiB RAM, no swap and 64 MiB temp.
Build has 120 seconds; the complete comparison has 1,200 seconds and every
individual subprocess has a 120 second ceiling. Root alone may execute it.

The source is `citytemp_f32`, 11,625,304 bytes,
`3f8ba1a80684edea13185934a2ec4a612715f1942f81e94d76c60e00b568ba7f`.
Before extraction, the runner freezes `[1048576,1052672)` and its derived hash.
Its algorithmic unexposed status follows reviewed receipts only. It is not an
absolute claim about historical reads. A separate `[2097152,2101248)`
replication runs the same complete frozen 15-descriptor matrix only when E
strictly beats bare original M6 and each of the eight ordinary masks; it is
never read during qualification.

The fixed 15 descriptors are original `[0]`; masks 0 through 7 at width 4,
phase 0 with `[0, bit0*2, bit1*2, bit2*2]`; E `[0,2,1,0]`; drop-prevcol
`[0,0,1,0]`; row-xor `[0,2,4,0]`; last-residual `[0,2,1,2]`; E at width 4,
phase 1; and width-three `[0,2,1]`. Every transform is independently inverted
on the input and a partial-row oracle. M6 and Zstd compress each distinct
transformed byte sequence once, keyed by byte SHA-256 and backend; aliases
still receive their own paid SMC1 descriptor. Native proxy runs all 15
descriptors with its fixed route bank.

M6 is forced through the sealed CIX binary with
`--best --format cixm6 --threads 1 --memory 1536MiB --block-size 16KiB -c`; Zstd is
`/bin/zstd -q -19 -T1 -c`. Bare original M6 and Zstd are untaxed headline
controls. gzip -n -9, bzip2 -9 and xz -9e are also freshly decoded original
controls. Identity SMC1 is diagnostic only. Every SMC1 archive is parsed for
complete cost and freshly decoded through the sealed absolute CIX child, then
compared byte-for-byte and SHA-256 to the frozen source. Construction, backend
search/reject work and fresh decode have separate `/usr/bin/time -v` receipts.

The separately frozen wrapper qualification checks retain rejected receipts for
outer grammar, CIXM6 framing/varints/footer bounds, Zstd frame bounds and
native HUF/route validation. The reviewed wrapper independently enforces M6
source/payload/footer bounds, single-frame Zstd content/window constraints,
native HUF/route bounds and no output on rejection. A compile or runtime
failure is evidence under a new identity; cells are never silently rerun.

`results.json` is progressive and retains losses, logical descriptors, unique
backend trial count and receipt paths. `artifact-binding.json` hashes all
created input, body, archive and restoration artifacts. Root may later compute
the requested native retention k=1/2/3/5/15 and regret summaries, and compare
the best native, Zstd and M6 ranking from those complete archive rows.

The v1 build failed with E0034 (Read/Write by_ref ambiguity) and E0277
(Result<usize> collect). Original source/freeze/schedule and compiler logs are
retained. The repair qualifies Read::by_ref and sums bounded lane lengths;
no source slice was extracted and no archive cell ran before this repair.
