# Independent review: ERC1/RDIC record evidence

**Reviewed:** 2026-10-03  
**Scope:** `record-evidence` source bindings, frozen inputs, complete-size
results, retained artifacts, fresh restoration, independent arithmetic checks,
malformed cases and resource receipts. This review did not rerun a codec or
benchmark.

## Verdict

No result-correctness blocker was found. The evidence supports a narrow pass
of the six declared conditions for the frozen synthetic record family and its
six-control reference set. In particular, `dev-eight` and `held-ten` satisfy
the predeclared strict test

```text
LE >= L0 && LC >= L0 && LEC < L0
```

by 12 and 59 complete bytes respectively. All six reference methods are
present and verified for every row; `reference_gaps` is empty throughout.

The result is a compact-model-description result. It does not establish a new
coding theory, a general-purpose compressor, real-data effectiveness,
streaming scalability or a production route. The held-out positive is a
second fixed sample from the same synthetic generator family, rather than an
external or natural-data validation.

The evidence packet should be called immutable only after a final manifest
seals the completed report, results, measurements, artifact binding,
supplement, review and raw receipts. This is a packaging requirement, not a
reason to reject the measured result.

## Reproducible read-back

The current source and harness hashes match their freezes:

| Item | SHA-256 |
|---|---|
| ERC1 source and copied executed source | `1308d501cc253bca64a7431c1eff30cd7dfecd5ea6d3c6bbe5474d65bd6eafa0` |
| RDIC source and copied executed source | `cc1cf83a91ca0c9945281187be0136ca26d7c5e49237e29b5b8b8d7d1c07dbfb` |
| Main runner | `799e062f2a319e6efb05259658a6c709036105b6953c218bc80cb9e90671c37d` |
| Main scheduler | `b5b179da03669b33a9491b5c7829839ac477def7158338e317aa3b41879397cd` |
| Fixture generator | `88596d82f69afac82f0fde05562d4ab4e209c17dcc1c740a1c7e61c5345566e9` |
| Tiny-oracle source | `a421fcffde5d3ab07fffc4a4ac63c7b8afb4c83ddece8d3bb61627ddb40d07e4` |
| Tiny-oracle scheduler | `49bb9a095bc8fd3946fb9b0671da74dbb02aa501d3544adeddc5a7412e0d80eb` |
| Built ERC1 binary | `20aba2f2051f5b2eba016f623d0711c7244a104c2510f4c44934303a8d721eb9` |
| Built RDIC binary | `b78ac8b188510a94532ef244923763b982fb168c42fb67ac7929f893b45da19a` |
| Main results | `c289f1740766aac69b2219273344b4162fde303fcfcd5606acd3d7e6f245266e` |
| Artifact binding | `d863db504c2d4b21f48bfcedcce2943b75661ae250b8c6e0f1d1c4a4e3ac6620` |
| Supplement results | `a1b23f2698378c0f9e65d5bbc58252a6cfb2b0c79437b79ef54d9ebd597efbea` |

The eight frozen fixture files total 84,992 bytes. Their present bytes match
all hashes in `input-freeze.json`. A read-only rehash of every retained path in
`artifact-binding.json` found no missing file, length mismatch or digest
mismatch. Its 164 entries comprise 79 successful archives, 79 restorations and
six malformed archives. Every retained restoration has the frozen source
digest. The binding intentionally points to bytes outside Git, so it remains
an identity record after those working files are removed.

The main batch receipt records exit 0, CPU8, `cpu.max=100000 100000`, a 2 GiB
memory ceiling, zero swap, 360.48 seconds elapsed, 359.95 cgroup CPU seconds,
135,585,792 bytes sampled cgroup high-water and 10,500,749 bytes peak monitored
work-directory footprint. The supplement receipt separately records exit 0
under the same CPU, quota, memory and swap settings. These are actual child
cgroup read-backs. The sampled high-water is correctly reported as a lower
bound and does not establish a precise process peak.

## Complete-size and mode checks

The five strong rows reproduce the report exactly:

| Input | L0 method | L0 | LE | LC | LEC | Delta | Strict |
|---|---|---:|---:|---:|---:|---:|---|
| dev-six | RDIC | 792 | 1304 | 1131 | 792 | 0 | no |
| dev-eight | RDIC | 979 | 1368 | 1201 | 967 | 12 | yes |
| dev-four | RDIC | 404 | 792 | 1017 | 408 | -4 | no |
| held-six | RDIC | 696 | 1144 | 993 | 696 | 0 | no |
| held-ten | RDIC | 1173 | 1464 | 1301 | 1114 | 59 | yes |

The positive rows use the same selected width for E, C and EC. `dev-four` does
not: E selects width 2 while C/EC select width 4, and the report correctly
labels that row a portfolio-cost comparison rather than a fixed-width
ablation. The weak, absent and empty forced structural modes exit with `no
applicable candidate`; Auto selects Raw and these are retained losses. They are
expected unsupported routes, not missing reference results.

The six-control wording is exact: RDIC plus zstd, xz, bzip2, gzip and frozen
CIX BEST. Their recorded commands match the frozen settings, each successful
archive is decoded in a separate process, and every restored digest matches
the corresponding source. The measurements are single observations. The
experimental encoder performs discovery, rejected trials and an internal
round trip while the conventional controls do not, so the timing data cannot
support a speed comparison; the report disclaims one.

## Metadata-only direct-control result

For every strong row, ERC1 EC and RDIC use the same ascending vocabulary and
the same mixed-radix sequence width. Their payload ranks are therefore equal.
With the measured formats,

```text
LEC = 24 + P
LD  = 19 + Q + P
LD - LEC = Q - 5
```

where `P` is the byte-rounded sequence rank and `Q` is the byte-rounded
combinadic dictionary rank. The physical rows confirm the identity:

* width 6: 33 dictionary bits round to 5 bytes, producing a tie;
* width 8: 130 bits round to 17 bytes, producing the 12-byte win;
* width 10: 506 bits round to 64 bytes, producing the 59-byte win;
* width 4: 7 bits round to 1 byte, producing the 4-byte loss.

Thus the positive result comes entirely from describing the same local set
with equality/count parameters more cheaply than with a generic subset rank.
It is valid complete-size evidence for automatic model combination, while also
showing why it is not evidence for a new rank code or an entropy-limit escape.

## Reconstruction and negative-path evidence

The main Python arithmetic checks recompute each structured ERC table and rank
from the frozen source, and independently recompute RDIC combinadic dictionary
and sequence ranks. These checks validate the encoded integers; they are not a
second complete decoder. Separate fresh Rust decoder processes establish the
full archive-to-source restorations.

The supplement independently constructs complete tiny archives and exercises
all 104 ERC E/C/EC ranks and all 24 RDIC two-word dictionary/sequence cases.
Together with the overfull-dictionary regression it records 129 successful
fresh decoder cases. This is strong small-space coverage of the rank/unrank
conventions, though still not an independent full decoder implementation.

All six malformed cases return nonzero and leave no output. Truncation and a
CRC mutation exercise integrity rejection. Invalid width, mask, mode and rank
width have recomputed CRCs and therefore reach semantic validation. This is
useful targeted coverage and is correctly not described as fuzzing or an
exhaustive hostile-input proof.

## Qualification limits and later hardening

* The successful inputs are generated, binary-alphabet record streams of at
  most 12,800 bytes under a source implementation capped at 16,384 bytes.
  The held-out seed, length, width and alphabet differ, but the grammar and
  generator family are shared.
* Only one held-out row wins; the other ties. This is sufficient for the stated
  bounded replication gate and insufficient for a broad effectiveness claim.
* The weak row shows that exact global rules have no exception path: Auto falls
  back to Raw and loses heavily to RDIC. Exception coding, larger-scale search,
  natural inputs and streaming remain open.
* The direct dictionary is the decisive same-information control. A more
  compact normalized dictionary/model syntax could reproduce the metadata
  advantage. The report correctly confines the result to these actual formats
  and the declared reference set.
* The phrase “all executable hashes” in the report should be read as all
  measured codec executables. The compiler is identified by verbose version,
  and Python, `/usr/bin/time` and other orchestration executables are not all
  hash-bound. Narrowing that wording would make the provenance boundary exact,
  but it does not change archive sizes or reconstruction evidence.

Subject to final manifest sealing, this packet supports the report's narrow
qualified-mechanism conclusion and its explicit rejection of novelty and
production claims.
