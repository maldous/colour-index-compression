# Mandatory research success gate

All six conditions below must pass for the **same frozen mechanism and
configuration**. Partial results, analytical examples, or wins from different
methods cannot be combined into a success claim.

| Condition | Required evidence |
|---|---|
| 1. Automatic heterogeneous discovery | A generic encoder discovers constraints from input bytes in at least two distinct structural families. Record discovery/search costs, rejected candidates and selected constraints. Human-supplied winning constraints or equivalent descriptions of one relationship do not qualify. |
| 2. Exact intersection representation | The archive defines the joint admissible space unambiguously, including parameters, outcome labels, variable order, dimensions, exceptions and any compiled certificate. Prove that the original belongs to it. No hidden decoder assets. |
| 3. Practical COUNT/RANK/UNRANK | Implement all three and measure their time and peak memory within predeclared encoder/decoder budgets at the claimed input scale. Tiny exhaustive enumeration alone does not establish practical scalability. Preserve exact integer precision. |
| 4. Exact reconstruction | A fresh archive-only decoder restores every source byte. Verify source/restored hashes; use independently verified small counting/ranking oracles and corruption/truncation controls. Decoder must not require search or original input. |
| 5. Complete-size improvement | The complete candidate archive is strictly smaller than the strongest appropriate measured established control under declared comparable resource limits. Count every constraint, model, parameter, rank, exception, framing, padding and decoder asset. Include a direct-model/same-information control to expose simpler explanations. |
| 6. Generalisation | Freeze mechanism, grammar and selection policy before disjoint replication. Demonstrate the same automatically discovered mechanism on held-out inputs beyond the discovery example; retain weak/absent-opportunity cases and losses. No corpus, filename, MIME or identity dispatch. |

## Comparison rules

The established reference set, exact versions/settings, identical input hashes
and budgets must be declared before comparative trials. Include appropriate
strong general-purpose references and the closest established structural
method. “Strongest” means the smallest qualified complete output in that
declared set; do not assert an unknowable global optimum over all compressors.
If a relevant stronger control is missing or unqualified, the gate remains
open rather than silently dropping it.

Discovery, failed trials and compilation count toward encoding cost. Report
decode cost, peak memory and temporary storage separately. One observation
per cell is sufficient under the user's current timing instruction; do not
claim statistically established speed gains from it. Reuse verified existing
baselines when settings, identity and measurement conditions match.

For practical byte-based comparisons, headline improvement is
`Delta = bytes(control) - bytes(complete candidate archive)`.
It must be positive. Cardinality interaction, ideal-bit savings, or a smaller
payload are supporting diagnostics, never substitutes for condition5.

## Current assessment

**ERC1 passes the narrow pilot gate on the frozen synthetic family relative
to its six declared controls.** It is not a novel theory, a general-purpose
production route, or a claim against every established compressor. See
[the complete four-cost evidence](record-evidence/REPORT.md).

The earlier candidates below retain their negative/partial assessment:

* The physical CSP1 experiment verifies exact representation and selected
  round trips at tiny scale; it does not automatically discover a useful
  heterogeneous model, demonstrate practical scale, beat an established
  compressor or generalise.
* The exhaustive predicate search automatically examines a finite pair family,
  but does not provide an input-driven physical encoder/decoder or a paid pair
  win. Its logical counts and shared-implementation rank checks are preliminary
  evidence only.
* Equality/count records now have two complete-size wins (12 and59bytes),
  including a frozen held-out ten-position case. Both individual models lose
  to the control while the intersection wins. Exact reconstruction, paid
  metadata, independent selected ranks and128tiny all-rank cases are verified.
  The gain over a direct dictionary is solely a cheaper model description.
  Broader affine/histogram methods and real-data/streaming effectiveness remain
  unqualified.

Passing these six conditions establishes a **qualified compression mechanism**,
not automatically a new theory. A novelty claim additionally needs the precise
prior-art distinction and mathematical/algorithmic evidence described in the
research direction. Production integration remains gated; ordinary CIX
optimisation remains paused.
