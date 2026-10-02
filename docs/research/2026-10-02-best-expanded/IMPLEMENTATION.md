# Expanded BEST: implementation checkpoint

This checkpoint fixes concrete eligibility and selection gaps in the frozen
Rust catalog. It makes no new dataset rank or superiority claim.

## Enabled changes

- All fourteen configured direct backend candidates are eligible: including
  generic Brotli q11, XZ 128 MiB dictionaries, pinned ZPAQ 7.15 L5 and libbsc
  3.3.12 BWT/static QLFC/LZP. Their complete CIXB1 envelope costs count.
- Ordinary BEST and native decoding default to 2 GiB; explicit memory limits
  remain authoritative. The bounded whole-file cap is 128 MiB.
- Whole-file search compares CIXG1, CIXG2 and CIXM6 with 16/32/64 KiB block
  trials for inputs at most 16 MiB and 64 KiB above that. Family budgets stop
  an early trial starving later packaging. Block overrides retain compatible M6.
- BEST generates all legal context-range and Huffman substream pairs for
  routes 2–7. Twenty-four newly eligible pairs passed fresh CLI decoding.
- CIXZ1 compares bounded raw/native frames with persistent Zstd history.
  Strict nested-output limits, Zstd window limits, exact epilogues, framing,
  idle flushing and footer validation are enforced. Live decoding produced
  69 bytes before the producer closed; all 141 final bytes restored exactly.
- Explicit portfolio verification accounts for parent buffers and decoder
  workspaces. Brotli trailing payloads and forged empty BSC archives reject.

`local-gates.json` records local correctness gates. New backend improvements
are backend gains until matched representation/native-model trials establish
otherwise. Portable binaries require no Python or codec subprocess.

## Qualification and remaining scope

The new BEST-only queue uses frozen existing inputs, 33 CCA gate cells followed
by 17 remaining catalog cells, covering all 28 dashboard datasets. It requires
fresh exact restoration, complete archive hash/size, wall/CPU time, RSS, and a
ledger proving every expected candidate was evaluated or explicitly omitted.
The running, separately authorized full Hutter attempt keeps its frozen d667
build and shared scheduler reservation. No full catalog cells bypass that lease.

CIXB1 candidates in streaming frames and a single-context Zstd trial strategy
remain unqualified follow-up work. Explicit retained-history constraints are
not supported in this mixed-stream path. BEST searches a finite legal candidate
space with declared memory/deadline bounds; it is not a proof of the smallest
possible lossless encoding. One-shot native calls can delay interruption.
Release smoke exposed a zero-input libzpaq behavior: its compressor emits no
framed block. The ZPAQ candidate now explicitly rejects empty input; ordinary
BEST retains its valid CIXM6/native fallback. The 2 GiB default-memory empty
CLI regression passes. No new corpus rankings, timings, or Site records are
published until verified.
