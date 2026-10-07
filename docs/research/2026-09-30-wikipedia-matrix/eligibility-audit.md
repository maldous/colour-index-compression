# Wikipedia representation eligibility audit

This is a read-only policy-coverage audit for the current bounded body-line
and D2 column representations. It is not a compression measurement: no PAQ,
archive, entropy estimate, holdout or full `enwik9` run occurred. The audit
read exactly the three previously exposed 4 MiB development ranges on CPU 0 in
1.421 seconds, under a 300-second wall budget.

| Offset | Input SHA-256 | Complete body bytes / bodies | Candidate 48–512 lines / bytes | Selected families / bytes |
| ---: | --- | ---: | ---: | ---: |
| 0 | `5ba647fec2ba51b0383cbe7147e15a478d85613245b7131c41764dbdd5062f77` | 4,002,936 / 506 | 7,872 / 1,461,079 | 23 / 14,242 |
| 100,000,000 | `fd30602741222df957545a821556c8428bb8c3e4ed45634367ae8470d901c6ec` | 4,023,313 / 377 | 15,603 / 1,946,029 | 320 / 161,285 |
| 400,000,000 | `a07035d4de761fc30cee70f4528156e8128abf7430222cfd63c2311168ea7f17` | 3,740,456 / 1,190 | 9,483 / 1,604,314 | 29 / 122,377 |

The current body codec accepts only complete `<text...>...</text>` bodies and
newline-terminated lines with a 48–512 byte core, at least one LINK/URL/NUMBER
hole, at least 24 literal bytes, and a global family with at least three
members across two bodies and two distinct raw lines. The selected bytes are
the strict source coverage after every condition, not a failure count or a
compression gain.

| Offset | Too short lines | Over-512 lines | No-hole lines | Literal-under-24 lines | Unterminated lines | Primary family failures |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 27,478 | 2,205 | 1,392 | 1,377 | 443 | 7,322 under-three; 43 under-two-bodies |
| 100,000,000 | 26,910 | 1,564 | 804 | 2,969 | 364 | 12,840 under-three; 23 under-two-bodies; 3 under-two-distinct |
| 400,000,000 | 27,352 | 1,611 | 1,328 | 2,891 | 1,027 | 8,082 under-three; 83 under-two-bodies; 5 under-two-distinct |

These primary family exclusions are disjoint by the first failed threshold.
The JSON retains simultaneous secondary reasons: for example, many
under-three-member families also fail the body and distinct-raw thresholds.
Length, termination, hole and literal-budget exclusions are separate and never
enter family selection. No trailing incomplete `<text>` body was encountered
after a complete opening tag in these three ranges; if present, it would be
recorded as boundary-excluded bytes rather than a failure.

The 4 KiB and 16 KiB eligibility-equivalent scans do not change the first two
regions. At offset 400,000,000 they admit one additional family and raise strict
selected source bytes from 122,377 to 156,826. They are static observations
only: no long-line transform, frame or backend run has occurred.

| Offset | D2 raw columns | Article-text columns excluded | Non-article raw-table bytes | Values ≤256 | Palette ≤256 | Count/rank columns with ≥4 values |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 271 | 12 | 100,910 | 259 | 259 | 194 |
| 100,000,000 | 203 | 9 | 76,227 | 194 | 194 | 170 |
| 400,000,000 | 201 | 9 | 231,850 | 192 | 182 | 114 |

Column screening describes exact D2 raw value columns. Count/rank eligibility
excludes article text, values over 256 bytes, palettes over 256, and columns
with fewer than four values; any future block is bounded to 1,024 values. It
does not encode a column or infer a byte saving.

Current body-line framing never reaches paragraph relations crossing blank
lines, arbitrary bounded token sequences outside a complete line, incomplete
body boundary material, unterminated final lines, short lines, over-512 lines,
no-hole lines, low-literal lines, or sub-threshold families. Those are policy
boundaries, not failed compression evidence. Full per-region exclusion bytes,
family-size and distance statistics, 4 KiB/16 KiB observations, raw-column
costs and source/dependency hashes are in
[`eligibility-audit.json`](eligibility-audit.json).
