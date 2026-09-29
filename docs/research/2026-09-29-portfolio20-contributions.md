# What produces the first-equivalent result

CIX portfolio 20 totals **26,402,526 bytes**. The fully completed local native PAQ8px v216 `-8` control totals **28,803,779 bytes**. Four structural/image representations save **2,401,253 bytes (8.34%)**; eight files retain native PAQ payloads with a reversible, equal-length CIX header.

| File | CIX bytes | Local PAQ v216 -8 | CIX saving | Selected representation |
| --- | ---: | ---: | ---: | --- |
| dickens | 1,902,345 | 1,902,345 | 0 | PAQ v216 -8 |
| mozilla | 6,477,226 | 6,477,226 | 0 | PAQ v216 -8 |
| mr | 1,671,101 | 1,820,661 | 149,560 | Planar volume → JPEG XL; exact surrounding bytes |
| nci | 447,748 | 809,461 | 361,713 | Hydrogen-coordinate candidate slots → PAQ v215 -8 |
| ooffice | 1,267,529 | 1,267,529 | 0 | PAQ v216 -8 |
| osdb | 1,698,992 | 2,018,086 | 319,094 | Database fields / remaining-count constraints → PAQ v215 -8 |
| reymont | 746,894 | 746,894 | 0 | PAQ v216 -8 |
| samba | 1,625,132 | 1,625,132 | 0 | PAQ v216 -8 |
| sao | 2,159,749 | 3,730,635 | 1,570,886 | Coordinate grids + residual feedback + bounded integer ranks → Brotli |
| webster | 4,626,898 | 4,626,898 | 0 | PAQ v216 -8 |
| x-ray | 3,531,428 | 3,531,428 | 0 | PAQ v216 -8 |
| xml | 247,484 | 247,484 | 0 | PAQ v216 -8 |

All 24 selected/control streams have full independent local restoration evidence. The listed savings are complete physical stream differences. For NCI and OSDB this compares complete pipelines using different PAQ versions; it is not an isolated transform ablation or proof of intrinsic enumerative-coding superiority.

Against the published PAQ8px v215 -12L total, the net advantage is 1,422,985 bytes. Author-reported per-file values are retained separately from locally reproduced reference measurements. The reference run at that setting is still incomplete.

## Completion audit

| Requirement | Current evidence / status |
| --- | --- |
| All twelve canonical members, individually encoded | Complete portfolio20 artifacts, manifest MD5/SHA256 and independent per-member input histories |
| All physical bytes counted | Sum of twelve actual `.cixc` files; selectors are in existing frame magics; no sidecar required for decoding |
| Full byte-exact independent restoration | Completed per-member proofs, unchanged source/backend/frame identities; Mozilla decoded separately before qualification |
| Better than current published leader | Fresh source read on29September,322 entries;26,402,526 <27,825,511 |
| Reproducible ordinary source encoder | Portfolio20 CLI, complete source bundle, prior exact native rebuilds and fresh uncached isolated smoke; no full cold end-to-end portfolio timing claim |
| Every member investigated | PAQ filter inventory across12 files and structural controls; exhaustive per-model ablation and all local v215 -12L reproductions remain incomplete |
| Equivalent-rank reporting and preserved baseline | Complete baseline and subsequent qualified portfolios, source snapshots, history audit and Site; old winning frames retained |
| Same predictive information controls | PAQ residual, conditional composition, candidate-rank, Markov and adaptive-feedback trials; no general enumerative-over-arithmetic advantage established |
| Secondary evidence preserved | Canterbury/Calgary/Artificial artifacts preserved; broader corpus stack remains generality work, not a prerequisite for the current Silesia total |
| Local computation / no Actions | All qualified runs local; source package excludes workflow files; no source push in this continuation |
| Public freely downloadable source | INCOMPLETE: source repository private; prepared source package awaits explicit publication decision |
| Official leaderboard listing | INCOMPLETE: submission draft prepared, not sent; requires authorization and external acceptance |

The numerical size target is achieved. The published-listing objective remains active. This audit does not convert partial reference runs or future research into completed work.
