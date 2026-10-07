# Tiny exact constraint-space qualification v1

The isolated Rust prototype compiled successfully and completed one frozen
batch: **13 exact-cardinality cases, 25 complete archives and fresh-process
restorations, three malformed archive rejections**. No production CIX code or
format was changed. `freeze.json` binds source, runner, scheduler and parent
revision before execution. The experiment identity is separate from that
parent revision; the source was a new uncommitted prototype when executed.

## Physical results

| Object/model | Admissible objects | Raw CSP1 bytes | Ranked CSP1 bytes |
|---|---:|---:|---:|
| Two bytes, no constraint | 65,536 | 17 | 17 |
| First byte <128 | 32,768 | 17 | 16 |
| First byte >=127 | 33,024 | 17 | 17 |
| Both: first byte =127 | 256 | 17 | 16 |
| Contradictory thresholds | 0 | 17 | rejected |
| Vacuous first byte >=0 | 65,536 | 17 | 17 |
| Five nibbles, no constraint | 1,048,576 | 16 | 16 |
| All five equal | 16 | 16 | 14 |
| First nibble even | 524,288 | 16 | 16 |
| Equality and even | 8 | 16 | 14 |
| Five zero nibbles, histogram constraint | 1 | 16 | 14 |
| Same histogram plus redundant equality | 1 | 16 | 14 |
| Two nibbles, first congruent to15 mod16 | 16 | 15 | 14 |

**No complete archive beats its bare original.** Byte inputs contain two
bytes; nibble inputs contain five or two bytes whose values lie in 0..15.
The nibble universe's ideal raw width is 4n bits, not the physical 8n bits of
that input representation. Both comparisons are explicit; neither is a win.
Raw CSP1 is a framed control, not an established compression record.

CSP1 stores four magic bytes, a bit prefix, zero alignment padding and four
CRC bytes. Prefix widths are 49 bits for byte models and 42 bits for nibble
models, before raw/rank payload. It includes version, domain, mode, length,
all model fields, payload width and padding. Inactive fields still cost bits.
Thus redundant predicates can cost no *additional* bits in this deliberately
fixed-width experimental header; this is not a free general constraint code.
An independent counting oracle enumerates every object in each frozen domain.
It checks membership cardinality, not every possible rank/unrank pair.

The selected encodings invoke a fresh instance of the native binary with only
archive path and output path. Every restored output equals the source byte
sequence; hashes, exact settings, object values and archive hashes are in
`results.json`. CRC is independently checked with the orchestration library.
Rank procedures share prototype source; an independent rank-value oracle is
still needed before claiming exhaustive ranking verification.

## Theory controls and limitations

The individually-unprofitable/jointly-profitable threshold illustration in
the main report is an **analytical prefix-language example**, not one of
these serialized measured trials. These measured trials demonstrate counting,
intersection, exact reconstruction and metadata losses. The Boolean-expression
example in `adversarial-math.md` is a mathematical existence example, not a
measured practical result. Its conjunction has a shorter direct constant
description in the same language; this must be counted as a competing model.

Same-information uniform enumerative and conditional arithmetic costs are
equal ideally by the completion-count telescoping proof in the main report.
No native arithmetic implementation or conventional compressor was benchmarked
here, and no measured superiority over those methods is claimed.

Malformed checks change CRC, truncate one byte, or append a trailing byte.
They return nonzero and create no output. All three fail integrity first; these are
not CRC-valid semantic-malformation or exhaustive fuzz tests. Contradictory
constraints reject rank coding while the explicitly requested raw mode
restores the object. There is no automatic selector or fallback policy.

## Resource evidence and reproducibility

Root held the existing WaveScheduler lock and a physical-core lease. Actual
receipts show CPU8, quota100000/100000, memory268435456 bytes, swap0. Active
temporary allowance was67108864 bytes. Build wall budget120s, batch180s.
The controls finished in1.29s wall/1.21s user/0.03s system with17152KiB peak
RSS and zero swaps. Those are **aggregate harness** measurements, including
independent enumeration and child processes; not codec throughput or per-model
timings. Per-row elapsed includes encoding and its fresh verification decoder.

Reproduce from the repository with:

```sh
python3 docs/research/2026-10-03-constraint-space/evidence/schedule.py
```

This asserts frozen source/runner hashes and acquires the shared lease. It
requires the recorded toolchain path and local systemd/sudo policy. Do not run
this to restart completed evidence unnecessarily. Archive-only decode example:

```sh
benchmark-work/constraint-space/build/csp decode INPUT.csp OUTPUT.bin
```

The retained source/binary hashes and toolchain output are in `binding.json`.
No datasets, downloads, external dictionaries, Python codecs or Actions ran.
