# Hutter Prize eligibility track — 2026-09-29

**Status: NOT YET QUALIFIED.** This is a separate enwik9-specific track. It
does not alter the frozen external evidence configuration and does not turn the
Silesia result into a Hutter Prize claim.

The canonical local input is
`/home/user/src/cix-baseline-data/inputs/enwik9`: 1,000,000,000 bytes and
SHA-256 `159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc`.
The current official record cited by the Prize is 110,793,128 bytes. Its
requirement for at least one-percent saving therefore permits at most 109,685,196 bytes; 109,685,197
does not qualify.

The detailed rules use the split-program accounting

`compressor + (1 if compressor and decoder have the same SHA-256, else 2) × decoder + archive + required option bytes`.

Even where the executable is identical, that means one compressor and one
decoder copy are counted. The preflight counts exact UTF-8 bytes for every
declared required option. It uses the detailed rules' `70,000 / T` hours per
program, where `T` is the measured Geekbench 5 single-core score. The FAQ has
older `100 h`/`500,000 / T` wording; this discrepancy is retained for reviewer
attention rather than silently treating the limits as interchangeable.

The conservative local resource policy is one CPU core, no GPU, at most
10,000,000,000 bytes whole-process-tree RSS, and at most 100,000,000,000 bytes
temporary disk. Measurements must cover each complete canonical enwik9 encode
and decode, not merely a child process or a prefix.

Run the audit only against a real prepared candidate manifest:

```sh
.venv/bin/python -m benchmarks.hutter_eligibility \
  --manifest results/hutter/submission-manifest.json \
  --output results/hutter/eligibility-report.json --strict
```

The gate hashes the input by default and fails if that check is skipped. It also
requires the actual restored billion-byte artifact, hash-pinned completed encode
and decode receipts bound to the exact programs and archive, measured whole-run
limits, and a hash-pinned packaging review. The review must record offline
execution, public-source access, OSI-license verification and license-completeness
checks; declarations and filenames alone cannot pass it. It can state only
`LOCAL_ELIGIBILITY_CANDIDATE`; it always records `official_approval: false`
because Prize reviewers alone can approve a submission.

## Missing before a local candidate can exist

- A complete CIX enwik9 archive with exact split-package bytes below the strict
  threshold.
- Measured one-core, no-GPU whole-enwik9 encode/decode resource records,
  including calibrated Geekbench 5 `T` and process-tree memory/temp usage.
- An offline, self-contained encoder/decoder/archive package and exact command
  options.
- A documented public source release and an OSI license. The current repository
  has no root `LICENSE`, `COPYING`, or `NOTICE` file; no license is inferred.
- Dependency provenance/licenses, build/use instructions, and an algorithm
  document suitable for the submitted package.
- External review and acceptance by the Hutter Prize maintainers.

The official rule, FAQ, and main-page snapshots used for this audit, with retrieval
metadata and SHA-256 records, are committed in
`docs/evidence/hutter-prize-20260929/`. Source references are
https://www.hutter1.net/prize/hrules.htm,
https://www.hutter1.net/prize/hfaq.htm, and
https://www.hutter1.net/prize/.
