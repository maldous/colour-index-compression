# Hutter Prize eligibility track — 2026-09-29

**Status: NOT YET QUALIFIED.** Hutter Prize/enwik9 is now the sole active goal.
The earlier Silesia and broad evidence programmes are preserved historical work;
their results do not establish a Hutter Prize result.

The canonical local input is
`/home/user/src/cix-baseline-data/inputs/enwik9`: 1,000,000,000 bytes and
SHA-256 `159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc`.
The current official record cited by the Prize is 110,793,128 bytes. Its
requirement for at least one-percent saving therefore permits at most 109,685,196 bytes; 109,685,197
does not qualify.

The detailed rules use the split-program accounting

`compressor + (1 if compressor and decoder have the same SHA-256, else 2) × decoder + archive + required option bytes`.

The primary self-extracting form, used by the current fx2-cmix winner, instead
counts `compressor + complete self-extracting archive + required option bytes`.
In `mode: self-extracting`, the archive is the decoder, and its full hash binds
both encode/decode receipts and the packaging audit. The decode receipt must
record invoking that counted archive without arguments. A separate uncounted
launcher or a split-decoder receipt is rejected. This support avoids charging
the already-embedded decoder a second time; it does not relax resource,
offline, canonical-input or public-source requirements.

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

## Offline draft profile

`benchmarks/hutter_submission_profile.py` builds an exact-file-inventory draft
bundle for `cix-stdlib-text-v1-draft`. It contains the CIX Python package plus
`benchmarks/hutter_cix.py`, uses only Python's standard library, and encodes with
`-9 --no-bwt` so an optional suffix-array package is not an implicit dependency.
The draft can be reproduced with:

```sh
.venv/bin/python -m benchmarks.hutter_submission_profile \
  --output results/hutter/cix-stdlib-text-v1-draft.zip \
  --manifest results/hutter/cix-stdlib-text-v1-draft.json
```

It reports every packaged path, byte count and SHA-256 and marks itself
`DRAFT_NOT_ELIGIBLE_NO_PROJECT_LICENSE_OR_PUBLIC_RELEASE`. This is an inventory
and isolation starting point, not a counted submission or a claim that this
profile reaches the target. The existing broad competitive CLI closure is not a
minimal text-path dependency certificate; its 105-module inventory and optional
dependency roots remain preserved in the Hutter evidence directory.

`benchmarks/hutter_measure.py` is the paired local instrumentation harness. It
pins a command to one requested CPU, samples its Linux `/proc` process tree for
combined RSS, samples an otherwise-empty dedicated temporary directory, records
the exact command/exit state, and hashes supplied input/archive/restored paths.
It intentionally leaves GPU non-use and Geekbench calibration unset until an
audited measurement supplies them; an instrumented run cannot become a local
candidate merely by filling in those fields.

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
