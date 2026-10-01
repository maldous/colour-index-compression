# Native FAST opportunity: reproducible evidence

This is a narrow local evidence record for the Gipfeli investigation and the
native CIX FAST change. It is not a Squash ranking, a general compression
claim, or a release qualification on its own.

## Scope and identities

All local MR measurements used the existing cached `benchmark-work/silesia/mr`
input: 9,970,564 bytes, SHA-256
`68637ed52e3e4860174ed2dc0840ac77d5f1a60abbcb13770d5754e3774d53e6`.
Each cell used a fresh encoder and a separate archive-only decoder, with
CPUs 16, 17, 18 and 19 reserved, a 3,000,000,000-byte RSS limit, a
512,000,000-byte temporary-space limit, no swap, and `/usr/bin/time -v`.
The runner materialized the input as the neutral name `source.bin`.

The candidate build was source `d5e7d4ba148f234cd5fd42ecfe6a6cbb2c369fea`:

| binary | SHA-256 |
| --- | --- |
| `cix` | `c1ce98c218207cd1b9b9b4aac3efa04ec133e9d716e3fe288d52c0dac910f65a` |
| `uncix` | `acd2764a2184f000f6147c29372e793765787b8bc4d5b3fdcf4522cd916753de` |

The current integration checkout is `d66739120c40fc409f2bf011b165389fc1062c2b`.
The candidate evidence build remains identified separately because it is the
binary that produced these archives.

The immutable manifests and receipts record the exact expanded commands. Their
common command forms are:

```text
/usr/bin/time -v -o {workdir}/encode.time.txt CIX --fast --verbose -o {workdir}/archive.cix {workdir}/source.bin
/usr/bin/time -v -o {workdir}/decode.time.txt UNCIX -o {workdir}/restored.bin {workdir}/archive.cix

/usr/bin/time -v -o {workdir}/encode.time.txt GIPFELI encode {workdir}/source.bin {workdir}/archive.cix
/usr/bin/time -v -o {workdir}/decode.time.txt GIPFELI decode {workdir}/archive.cix {workdir}/restored.bin
```

`CIX` and `UNCIX` resolve to the snapshotted binaries in each receipt. `GIPFELI`
is the pinned `65b9721308a357f6aa261c11d0af291d10d0b96c` control wrapper.
The CIX command includes automatic route selection and all selection time.

## MR results

| local artifact / effort | repetitions | complete archive bytes | archive SHA-256 | encode wall / CPU | decode wall / CPU | max RSS encode / decode | status |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| release CIX `--fast` (`938e8805`) | 2 | 3,258,331 | `3fd0d43cab71a38120801fb5e4dbbec37c2d06e21e14977a46b989de3816d288` | 5.94, 5.82 s / 21.58, 21.46 s | 1.42, 1.43 s / 1.40, 1.40 s | 16,788–16,960 / 4,352 KiB | verified screening |
| candidate CIX `--fast` (`d5e7d4ba`) | 2 | 3,370,778 | `baa8d52d473587e09b157bd43a3bd7b11e2cdf57cc9e21f084c4d762dce7ca1a` | 0.17, 0.17 s / 0.50, 0.51 s | 0.09, 0.08 s / 0.07, 0.07 s | 7,088–7,092 / 4,096 KiB | verified screening |
| candidate CIX `--best` (`d5e7d4ba`) | 1 | 2,441,327 | `ddecc67e6759785a9104d898adc09e0ee1c7742aee52fb75df93257a4a75e557` | 226.68 s / 509.57 s | 0.27 s / 0.25 s | 224,120 / 19,200 KiB | verified screening; one screen |
| local Gipfeli buffered control, copy branches | 2 | 4,702,538 | `4cc7e3d04ca7d57ca0c62fd8ae1c38b0560d71ec10873431e951e9483aa79656` | 0.07, 0.07 s / 0.06, 0.07 s | 0.04 s / 0.04, 0.03 s | 25,180 / 17,988–17,992 KiB | verified screening control |

The candidate FAST path is approximately 35 times faster to encode and 17
times faster to decode on these two local repetitions, while making the MR
archive 112,447 bytes (3.45%) larger. These are local screening observations,
not stable throughput estimates.

The FAST change uses a fixed 256 KiB LZ table and excludes hidden exact-rank
trials from FAST selection. It retains the existing format and decoder wire
grammar; DEFAULT and BEST were not changed by this FAST mechanism. Profile
accounting fell from about 22.388 accumulated CPU seconds in the baseline to
0.464 seconds in the candidate, which establishes that selection work is a
major measured mechanism in this path. An isolation ablation has not yet
assigned the remaining speedup between matcher, coding and allocation changes.

`--best` selected the complete CIXB1 direct bzip2 level-9 result above. It is
one verified local screen only, so it is not a replicated ranking result.
The cached historical Python `size` archive was rehashed and is byte-identical
to the Rust BEST archive (`ddecc…e557`). The historical `current` archive has
the same 2,441,327-byte size but a different archive hash because its CIXB1
header effort byte is `02` rather than `03`. No Python codec process ran for
this comparison.

## Gipfeli result and decoder diagnosis

The local pinned Gipfeli control did **not** reproduce the peltast 1,885,645 B
row. The imported Squash data records 4,702,538 B on eight other hosts and
1,885,645 B with 0.024767 s compression CPU time on peltast. The catalog does
not provide enough matched input identity and environment evidence to treat
that peltast row as locally reproduced. In particular, local wall time is not
compared with imported Squash CPU time.

The local control initially restored the wrong bytes. A pristine buffered
build and a build with only a `ReadBits` guard both produced the same
4,702,538-B archive (`4cc7…79656`) and failed fresh restoration. Replacing
**both** optimized decoder copy branches with incremental-copy code restored
the same archive SHA-256 exactly. That identifies the local decoder mismatch
in this control; it does not establish the cause of the historical peltast
size result. The latest `04fe241` streaming control still failed and remains
a failed control.

The local control is kept separate from native CIX: it is not a production
Gipfeli backend, it is not wrapped as a CIX route, and it has no claim of
bounded-memory streaming equivalence.

## CCA gate

`fast-lz-cca-v2` completed all 33 existing CCA inputs, with an exact fresh
archive-only decode for both incumbent and candidate on every input. Sixteen
v1 receipts were rehashed and imported only after validating input identity,
public flags, binaries, archive, restoration and receipt provenance; fifty
cells were newly executed. The v1 cell-ID collision is preserved as evidence;
v2 includes label and path in the cell identity.

| stratum | pairs | candidate wins | candidate losses | ties |
| --- | ---: | ---: | ---: | ---: |
| Canterbury | 11 | 3 | 6 | 2 |
| Calgary | 18 | 3 | 13 | 2 |
| Artificial | 4 | 2 | 1 | 1 |
| total | 33 | 8 | 20 | 5 |

The candidate total was 2,077,582 complete archive bytes versus 2,027,529
for the incumbent: +50,053 bytes. Per-input CCA GNU-time/RSS fields are kept
in the ledger, but no precise timing conclusion is drawn from this small-file
gate. Its role here is exactness and complete-size regression detection.

## Native ABI and streaming checks

The native FFI smoke record exercised 131,071 input bytes through irregular
partial callbacks: 98 read and 24 write callbacks while encoding, then 28
read and 208 write callbacks while decoding. It restored exactly, and read,
write, truncated-decode and invalid-level errors all propagated as failures.
The prior `938e8805` `uncix` also freshly decoded the candidate FAST MR
archive to the MR SHA-256.

For the current integration, an actual pipe stayed open after a 2,048-byte
prefix and used `--stream --fast --threads 2 --parallelism blocks
--block-size 64KiB --flush-interval 100ms --memory 16MiB -c -`. A complete
frame appeared at 0.151153 s and decoded bytes at 0.151244 s, both before
EOF. The fresh decoder exactly restored the 1 MiB test input. This is a
correctness/latency observation on one host, not a throughput qualification.

## Preserved evidence and remaining work

The machine-readable ledger is [FINDINGS.json](FINDINGS.json). It references
every current MR summary, failure control and the CCA result ledger. Individual
receipts include complete commands, input/archive hashes, binary hashes,
resource budgets, and decoder verification.

Remaining gaps:

- no production Gipfeli backend or native compact literal/copy-command codec;
- FAST LZ dictionary state resets at independent-block boundaries; persistent
  FAST LZ history has not been implemented or qualified;
- pending generic word-16 and retained-history hypotheses;
- the Squash SDK control is absent, so the exact wrapper path used for the
  imported catalog cannot yet be matched locally. Native Squash FFI is
  verified, but SDK shim loading is not;
- CCA is complete. Native ABI and one pipe-latency check are in
  `native-release-validation.json` and `native-latency.json`; broader
  qualification remains separate.


## Delivered release and local verification

The exact integration build at
`d66739120c40fc409f2bf011b165389fc1062c2b` was rebuilt with offline locked
full LTO. All four artifacts match the candidate binary/library bytes exactly;
[the build attestation](release-build-attestation.json) records each hash.
They are installed at `dist/cix`, `dist/uncix`, `dist/cixcat` and
`dist/libcix_native.so`, with [release metadata](release-native-metadata.json).
The standard Rust benchmark adapter snapshots these paths for future cells.
The previous immutable qualified-release directory stays preserved as an
explicit historical control.

[Focused release verification](release-tests.json) passes parser/production
substream tests, expert override behavior, implicit stdin, real streaming
pipes, stdout writes, parallel CLI and automatic BEST portfolio coverage.
The pipe suite includes a 20 MiB+313-byte stream through an 8 MiB configured
working budget, one worker, irregular chunks and pre-EOF idle flush. A
mistyped test-target invocation was preserved and corrected; it ran no product
test and is recorded as a harness error separately.

Build the portable current-host binaries from the named source revision:

```sh
CARGO_BUILD_JOBS=2 cargo build --offline --locked --profile release-lto --manifest-path rust/cix-native/Cargo.toml --bin cix --bin uncix --bin cixcat --lib
```

The Rust dependency lock and required native development libraries are listed
in `rust/cix-native/README.md`. Current-host native library versions are in
release metadata. No build or execution is claimed on other platforms.

```sh
dist/cix --fast -c input.bin > output.cix
dist/cix --best -o smallest.cix input.bin
dist/cix --stream --fast --block-size 64KiB --memory 16MiB --threads 2 --flush-interval 100ms -c - < input.bin > stream.cix
dist/uncix --stream -c - < stream.cix > restored.bin
```

The new FAST grammar is the existing CIXG1 route 3; previous native decoding
compatibility was verified on the full MR archive. Streaming frames can be
verified/emitted before EOF, but final whole-stream integrity is confirmed only
after footer verification. The BEST named-file portfolio and independently
framed FAST pipe policy remain distinct bounded search choices.
