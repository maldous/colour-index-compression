# NNLCB source reconciliation

Source revision: `91eeea5094a49bd1e60fa9ee4bf3a8e50891da63`.
Paper: Sun et al., DOI `10.1007/s11704-024-40300-5`, 2025.
Supplement dated 18 December 2024. Retrieval: 29 September 2026 UTC.
Original files and SHA-256 references are archived under `sources/` and
`manifests/external-source-hashes.json`.

The importer preserves 16 aggregate rows, 481 D1–D28 algorithm/dataset rows,
and eight separate Cmix/LLMZip prefix rows. LLMZip did not complete D1–D28;
its enwik3–6 prefix tests must not appear as full-dataset measurements.

## Definitions and discrepancies

- Eq. (1) defines CR as 8 × compressed bytes / original bytes. The prose's
  pixel/character examples do not change the byte denominator. Supplementary
  CS/CR values agree with byte counts and binary MiB, although CS is labelled
  “MegaBytes”. Original labels and rounded values are preserved. Rounded CS
  values are not exact compressed-byte counts.
- Weighted CR and SSP use **compressed-size weights**, as printed on paper p.8.
  Applying these weights to the supplementary rows reproduces the aggregate
  table within printed rounding. Original-size weights produce different results.
- Eq. (3), visually checked on p.7, is population standard deviation / mean ×100.
  Applying it to NNCP's 28 printed CR values yields 69.232964%, whereas the
  published aggregate is 13.084%. Dividing that CV by sqrt(28) yields 13.083800%.
  The same extra factor reconciles 15 of 16 rows within printed rounding. This is
  an **inference from published numbers, not an author-confirmed correction**.
  CIX calculations preserve the paper-defined CRP and expose the inferred table
  bridge separately. No complete CRP compatibility claim is justified yet.
- Lstm-compress has a further independent inconsistency: supplementary CR rows
  average 3.023071, whereas the aggregate table reports 2.786. Its reconstructed
  weighted CR is 5.339764 versus published 5.395, and compression times sum to
  493.762217 hours versus published 492.869. Both authoritative tables are
  preserved verbatim as numeric records; no values are repaired to force a match.
- The advertised `results.xlsx` contains placeholder tables, not benchmark
  values. It is archived, but no invented workbook results are imported.
- The supplement's XZ example repeats PBzip2 commands. These are preserved as
  a source defect; local XZ uses an explicitly recorded real XZ command.
- README descriptions use 2^8 / 2^9 where the listed enwik sizes are 10^8 / 10^9.
  Acquisition follows named canonical files and verified exact byte counts.
- Multi-file datasets often omit concatenation order and container preparation.
  Byte-size equality alone does not prove an exact NNLCB input representation.

## Qualification discipline

The 28×19 matrix has no blank statuses. Unknown inputs remain NOT REPRODUCIBLE;
unmeasured full-universe aggregates remain unavailable. Failed or slow cases
cannot disappear from the denominator. CIX contains adaptive PAQ prediction
models, so Params/FLOPs/MIL are not falsely marked “no neural model”. The frozen
code lacks their instrumentation; this limitation is explicit.

The reference table belongs to NNLCB's platform. Local CIX and local reference
timings belong to a separate same-machine table. This work does not constitute
independent validation by the NNLCB authors.
