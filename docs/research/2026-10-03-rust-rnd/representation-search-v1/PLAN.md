# RSL1 reversible representation search

Status: prepared; no compilation, test, or benchmark has been run.  This is a
new experiment identity rather than a change to the frozen generic selector.

Hypothesis: for some arbitrary byte streams, a compact, stored reversible
program followed by the same native CIXG1 backend produces fewer complete
stored bytes than identity.  It is falsified for a qualification input when
the minimum RSL1 frame is not smaller than its identity RSL1 frame.  No claim
about CIX generally follows from one input.

`rust/cix-native/experiments/representation-search-v1/main.rs` defines RSL1,
a byte-program format whose decoder needs neither the search procedure nor a
learned model.  RSL1 v2 frame bytes are `RSL1`, version, program length,
backend tag, original length, payload length, two bytes per operation, payload
and an IEEE CRC-32 trailer. The CRC covers every preceding frame byte,
including header lengths and serialized operations. Tag zero holds a complete
CIX archive and tag one holds the literal raw fallback.
The selected byte count includes program instructions and, for CIX payloads,
the nested archive's framing, model state, histograms, dictionaries, residuals
and padding.

The later full candidate set is exactly 307 programs: the 18 one-step atoms and
the 289 ordered two-step pairs where neither step is `literal`.  Atoms are
identity, literal, lane transpose {2,4,8,16}, modular delta {1,4,8,16}, XOR
{1,4,8,16}, and previous-stride residual {1,4,8,16}.  Delta and residual are
currently intentionally identical byte predictors; retaining both makes the
semantic ablation explicit, while the result ledger shows whether their
stored instruction distinction costs bytes.  The full depth-two Cartesian
set is evaluated without estimates, pruning, or a no-expansion rule.  This is
finite exhaustive enumeration, not a proof beyond the declared language.

The first permitted screen is a fixed 12-candidate subset at at most 8 KiB,
FAST only: identity, literal, transpose-4, delta-1/delta-4, XOR-1/XOR-4,
residual-1/residual-4, transpose-4→delta-4, delta-4→transpose-4 and
XOR-4→transpose-4.  There is one measurement per candidate and no averages.
The full set is later work.  Each non-literal candidate uses the same supplied
immutable `cix` binary with one thread, 512 MiB CIX memory and `--format
cixg1`; literal stores arbitrary bytes directly.  A fresh `uncix` process
decodes nested CIX, then RSL1 inversion reconstructs every byte.  `rsl1
decode ARCHIVE OUTPUT UNCIX` is the separate archive-only restoration path.
The driver permits up to 64 MiB input and 128 MiB transformed data.  It records
once per candidate transform, payload, instruction and complete bytes,
encode/decode duration, GNU `time -v` maximum RSS per native child, and all
scratch bytes. Scratch includes transformed bytes, nested archives, restored
bytes and GNU-time logs. Literal has zero native time and RSS by definition.
Source and archive reads use one opened file handle, check its metadata, then
read at most limit-plus-one bytes before allocating beyond the declared cap.
The archive parser checks count, lengths, trailing CRC and exact frame length
before inversion.
Nested decoder stdout is streamed into a file with the stored source length as
a hard output limit, then its exact byte count is checked. Raw fallback accepts
only a one-op literal frame, and is covered by the outer CRC. The nested CIX
encoder runs under a 128 MiB `ulimit -f` cap; RSL1-owned raw and outer files
are bounded by their checked source/archive limits. Every native child is
polled against a 60-second wall bound. Decoder stdout is read on a bounded
four-chunk channel. `setsid` places the GNU `time`/`timeout`/native command
chain in its own process group; GNU timeout uses `--foreground` to retain that
group and a one-second kill-after period. Its installed help states foreground
mode does not time out command children, so RSL1's own process-group cleanup
remains responsible for descendants. Timeout, output overflow, pipe error and output-write failure signal the whole
negative-PID process group, then drop the queue receiver before joining the
reader and waiting for the direct child.

Pre-run freeze is [freeze.json](freeze.json).  Dispatch only after root grants
a WaveScheduler lease.  One local run is enough for this time-critical screen;
there are no averages.  Use an already-authorized, hash-bound input and an
immutable build.  Example command after lease:

```sh
/tmp/rsl1 screen INPUT RSL1.ARC result.jsonl CIX UNCIX fast
/tmp/rsl1 decode RSL1.ARC restored.bin UNCIX
```

The predeclared native pair is
`benchmark-work/ptt5-fixed-8439/final/{cix,uncix}`. The driver binds each
execution to SHA-256 values for input, both binaries, its untracked source,
`Cargo.lock`, git revision, and `rustc --version` before any candidate row.

Existing evidence and boundary: `chain.rs` is the frozen mode-7 transform
selector (nine transform IDs, bounded beam) and `numeric.rs` contains CIXM6
word FOR/delta/delta2/PFOR candidates.  `legacy_lz.rs` and `bwt_legacy.rs`
are inner coders.  These are private CLI modules, so RSL1 uses the supported
native CLI archive boundary and does not modify their selector or Cargo
manifest.  Existing BWT/LZ and numeric findings remain controls; this study
does not recast any prior result as a representation win.

OpenZL supports a graph of reversible codecs whose decoder runs the reversed
graph ([concepts](https://openzl.org/getting-started/concepts/)); its example
selects delta before a numeric LZ graph only when the inspected integers are
sorted ([introduction](https://openzl.org/getting-started/introduction/)).
RSL1 adopts the narrower useful idea: serialize an encoder-selected,
finite transform program and reverse it during decode.  It does not use
format parsing, corpus identity, training, a graph runtime, or external
decoder assets.  Brevis’s public project description says its transforms are
fixed-width deterministic and exactly reversible, and its nonzero search
budget learns an encoder-only prior before tensor A* search
([repository](https://github.com/jiekeshi/Brevis)).  RSL1 intentionally has
no such prior, A*, checkpoint, or pretrained decoder asset; its enumeration
is transparent and generic.

Arithmetic is byte modular: delta/residual subtraction and inverse addition
wrap modulo 256; XOR is self-inverse; lane transpose is an exact permutation.
All byte patterns, including floating-point special values and container
metadata, are therefore preserved. Promotion requires a smaller complete RSL1
archive, independent exact restore, and a matched identity control under the
same profile and build. Any later production integration requires a distinct
experiment ID and generic-policy review.


## Execution checkpoint

The frozen 12-candidate screen is now verified; see REPORT.md/results.json. Full307enumeration and production integration remain unexecuted.
