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

**No candidate passes the gate.**

* The physical CSP1 experiment verifies exact representation and selected
  round trips at tiny scale; it does not automatically discover a useful
  heterogeneous model, demonstrate practical scale, beat an established
  compressor or generalise.
* The exhaustive predicate search automatically examines a finite pair family,
  but does not provide an input-driven physical encoder/decoder or a paid pair
  win. Its logical counts and shared-implementation rank checks are preliminary
  evidence only.
* Equality/affine plus histogram intersections remain candidate investigations,
  with no qualified complete compression advantage.

Passing these six conditions establishes a **qualified compression mechanism**,
not automatically a new theory. A novelty claim additionally needs the precise
prior-art distinction and mathematical/algorithmic evidence described in the
research direction. Production integration remains gated; ordinary CIX
optimisation remains paused.
