# Input-grounded experiment priorities

This order was fixed from structural evidence before the new compression runs. Rows are alternatives, not an additive estimate of full-file savings. All discovery inputs are exact contiguous 4 MiB regions with SHA-256 identities in `targeted-input-set-v2.json`.

| Priority / opportunity | Eligibility | Scale | Candidate / control | Complete bytes / delta | Verification | Resources | Next decision |
|---|---:|---:|---|---|---|---|---|
| 1: census-style article families, offset 520,093,696 | Paragraph 2,852,634 B; line-4096 2,767,556 B; incumbent line-512 1,812,453 B | 4 MiB | Original PAQ / paragraph skeleton+PAQ / line-boundary ablation+PAQ | Pending; see live receipts | Pending | One core, 3 GB RAM, 1 GB temp, 1,200 s each | Complete physical comparison before any promotion |
| 2: table-rich region, offset 226,492,416 | Paragraph 831,588 B; line 577,303 B | 4 MiB | Paragraph or body-field adapter with paid dictionaries | NOT RUN | NOT RUN | Separate predeclared budget required | Reassess using census result; body-field adapter is not implemented |
| 3: redirects/title relations, offset 872,415,232 | Paragraph 728,381 B; line 739,737 B | 4 MiB | Causal title/target reference model with literal exceptions | NOT RUN | NOT RUN | Separate predeclared budget required | Implement only after explicit decoder-causal representation design |
| 4: long-line-rich region, offset 83,886,080 | Paragraph only 18,326 B; line only 1,457 B | 4 MiB | Existing long-unit modes | NOT RUN | NOT RUN | None allocated | Low priority: long lines mostly fail family matching |
| 5: conditional value composition within families | Not yet measured for a proposed body-field codec | 4 MiB initially | SAO-style grouping / paid dictionary+remaining-count arithmetic / matched rank control | NOT RUN | NOT RUN | None allocated | Profile residual fields after completed representation comparison |

The census target has **74 paragraph families versus 68 line families**. Although paragraphs used fewer families in the three fixed development ranges, that observation does not transfer to this selected target. Here the case for the paragraph experiment is greater eligible coverage and an explicit boundary ablation; dictionary savings are not assumed. Paragraph family recurrence spans 2,519 to 1,973,827 bytes (median 5,805 bytes) inside this region. Larger contiguous validation is appropriate only if physical results justify its cost.

The two current target jobs share six GB of reserved memory and two GB temporary space; the global wave cap remains four physical cores / 12 GB / 4 GB. Identical PAQ v216 `-4 -simd AVX2`, basename, initial state and outer metadata/header apply to all three modes. A separate original-byte control is required because this exact target/wrapper identity has not previously completed.

Every reconstruction rule, family dictionary, hole length/value, source-order descriptor, literal boundary and outer wrapper is inside the measured archive. Backend gains, representation gains and entropy-coder gains remain distinct: these unit trials use PAQ and contain no isolated CIX-rank advantage claim.

Successful targeted results must advance to disjoint fixed development and frozen real holdouts, with their exposure recorded. Sizes such as 4 → 16 → 64 MiB are future staged validation, not authorized automatic launches or projected scores. No full-enwik9 compression is launched here.

Canonical input and reference distinctions are in [INPUT-GROUNDING.md](INPUT-GROUNDING.md). Existing losses, the frozen input registry and the invalid first locator are all preserved. The current live measurements are in [LIVE-RESULTS.md](LIVE-RESULTS.md).
