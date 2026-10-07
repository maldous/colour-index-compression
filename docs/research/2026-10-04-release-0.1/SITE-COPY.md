# CIX portal copy (private review draft)

This is factual copy for a future private portal. It is not a release claim or a benchmark table. Populate charts and platform badges only from final release receipts.

## Hero

### CIX: lossless compression for one file at a time

Keep the original, create a self-describing archive, and restore the exact bytes whenever you need them. CIX is a command-line compressor for arbitrary byte streams, built for ordinary shell workflows and transparent inspection.

`cix` compresses. `uncix` restores, tests, and lists archives. `cixcat` sends restored bytes to standard output.

**Primary actions:** Download source | Read the manual | Explore benchmarks

**Tooltip:** “Lossless” means restoration reproduces the original bytes exactly. CIX processes one input file per invocation; use `tar` or another archiver when a directory tree must be preserved.

## What it does

### A practical command-line utility

CIX writes CIX archives, retains the input file by default, and works with files or standard streams. Use `--fast` when latency matters and `--best` when you want CIX to consider a broader bounded set of candidates.

```sh
cix report.dat
uncix report.dat.cix
cix --fast -c input.bin > input.cix
cixcat input.cix | tar -x
uncix -t input.cix
```

**Tooltip:** `-f` permits replacement of an existing output; `-c` writes an archive to standard output.

### Automatic portfolio, explained plainly

CIX can build several bounded archive candidates and retain the smallest finished archive for an input or eligible region. That is an archive portfolio: each candidate is complete, with its representation and coder costs included.

It differs from a predictive mixture, which combines probability estimates for the same next symbol before entropy coding. CIX does not present post-hoc archive selection as a new predictive model.

**Tooltip:** “Bounded” describes the candidate set, memory admission, and archive framing. `--best` does not claim global optimality.

### Streaming and bounded resources

CIX supports command-line streaming workflows and resource-aware candidate admission. Its archive formats carry the information needed for restoration; the decoder reproduces the selected route without consulting the original input.

The 0.1 candidate has Linux streaming qualification for selected paths, including exact restoration, interruption behavior, empty input, and malformed-footer handling. Publish the exact qualifying modes, resource settings, and receipt links with the final release rather than extrapolating to every route or host.

**Tooltip:** A memory setting can exclude candidates that do not fit the configured admission budget. It is not a universal process-memory guarantee.

### Familiar backends, clear attribution

CIX can use established compression backends and system libraries where a route calls for them, including zlib, bzip2, liblzma, Zstandard, and Brotli. Those are named as backends. A result from an external backend is not presented as a new native CIX prediction method.

## Performance and benchmarks

### Read the numbers the useful way

Every final chart should show original bytes, complete archive bytes, wall time, CPU time where available, peak-memory evidence, route/profile, host, and exact command. “Complete archive” includes framing, model descriptions, metadata, termination, and checksums where they apply.

**Compression-size tooltip:**

`size reduction = (original bytes - complete archive bytes) / original bytes × 100`

A positive percentage means the complete CIX archive is smaller. A negative percentage means expansion. Never substitute ideal entropy bits, payload bytes, or transformed-substream size for complete archive bytes.

### Comparison records: scope before ranking

Public records are useful context only when input bytes, version, options, hardware, resource limits, archive accounting, and validation rules match. Name and link the original record. When those conditions differ, label the result “not directly comparable” rather than implying a rank.

| Chart field | Tooltip copy |
| --- | --- |
| Dataset | Name, byte hash or canonical source, and whether it is public or local-only. |
| CIX FAST / DEFAULT / BEST | Complete archive bytes and reduction percentage; each profile has its own command. |
| Comparator | Tool, version, options, and source link. |
| Time | Wall and CPU time, host, and concurrency. |
| Memory | Process RSS and cgroup measurement, with lower-bound language where applicable. |
| Validation | Exact restoration status and checksum method. |
| Comparability | Matched, partially matched, or not directly comparable, with reason. |

**Chart placeholder:** Final qualification data will populate this section. Do not prefill ratios, record positions, platform throughput, or cross-dataset totals.

## Research note: a useful negative result

### We tested whether existing predictors should cooperate more closely

A private predictive-information audit traced 28 existing causal experts on 53,248 held-out real bytes. The best single traced expert used 163,134.352 ideal predictive bits. A fixed-share causal combination improved this by 937.523 ideal bits (0.5747%). The hindsight oracle, explicitly not a compressor because it selects after seeing the byte, showed a 47,163.564-bit gap (28.911%).

The causal gain did not pass the predeclared material gate, so no physical mixed codec was added. Null controls also showed that a large hindsight gap can arise from selection advantage without new usable causal information.

**Tooltip — ideal predictive bits:** A log-loss diagnostic from assigned probabilities. It is not archive size and must never be described as bytes saved.

**Tooltip — hindsight oracle:** A diagnostic that chooses the best expert only after it knows the actual symbol. A decoder cannot do that without extra information, so it is not achievable compression.

For publication, cite a public evidence page only if its methodology and receipts are released. Do not use this result to claim a theoretical compression limit or a performance record.

## Origin story

### Built by measuring the whole archive

CIX began with a simple standard: an idea earns its place only when the complete archive is smaller, the decoder restores exact bytes, and description, framing, time, and memory costs are visible. Some synthetic mechanisms worked; several did not transfer once ordinary packing, metadata, and the incumbent archive were counted.

The result is a focused 0.1 candidate: a practical lossless utility with explicit formats, a bounded candidate portfolio, and evidence that separates measured results from future work.

## Platform and packaging

### Source-first 0.1 candidate

The source candidate includes recipes for Linux, macOS, and Windows builds, plus Debian and RPM source packaging. Linux x86_64 is the currently qualified host. macOS and Windows recipes are provided for native qualification; do not show them as shipped or qualified binary downloads until their own receipts exist.

Optional Squash integration is separate from the base package and needs its own plugin-load qualification.

**Badge copy:**

- Linux x86_64 — qualified source candidate
- macOS — source recipe; qualification pending
- Windows — source recipe; qualification pending
- Debian / RPM — source package recipes
- Squash — optional integration; not part of the base package

## Trust and help

### Inspect before you rely on it

Use `uncix -t` to test an archive when you need integrity verification without restoring its contents for use. Link format compatibility, security, support, third-party notices, build instructions, and manual pages beside downloads.

## Footer microcopy

CIX is a lossless command-line compressor. Results vary by input, profile, machine, installed libraries, and resource settings. Published benchmarks show complete archives and reproducible commands; they do not claim universal rankings or a theoretical limit on compression.
