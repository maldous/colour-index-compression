# Complete candidate table

All sizes include the completed physical stream and framing. Failed partial archives have no qualified size.

| Input / stratum | Configuration | Complete bytes | Encode / decode s | RSS KiB E/D | Status |
|---|---|---:|---:|---:|---|
| fcbench-msg (development) | `{"mode": "baseline"}` | 14432 | 10.53 / 0.89 | 59124 / 22528 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"mode": "gzip"}` | 14745 | 0.03 / 0.03 | 13568 / 13568 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"mode": "bzip2"}` | 15201 | 0.04 / 0.04 | 13824 / 13568 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"mode": "xz"}` | 13344 | 0.05 / 0.03 | 30208 / 13568 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"mode": "brotli"}` | 14752 | 0.04 / 0.03 | 16640 / 13824 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"effort": "fast", "mode": "pipeline"}` | 14832 | 0.27 / 0.06 | 23552 / 20736 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"effort": "balanced", "mode": "pipeline"}` | 12746 | 0.49 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"effort": "maximum", "mode": "pipeline"}` | 12746 | 5.31 / 0.05 | 205412 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "hybrid", "effort": "maximum", "force": "composition", "mode": "pipeline"}` | 15524 | 0.19 / 0.26 | 23808 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "cix", "effort": "maximum", "force": "lz", "mode": "pipeline"}` | 15143 | 0.23 / 0.25 | 23896 / 20736 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "count-range", "effort": "maximum", "force": "lz", "mode": "pipeline"}` | 15178 | 0.32 / 0.27 | 23900 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "deflate", "effort": "maximum", "force": "lz", "mode": "pipeline"}` | 14913 | 0.14 / 0.07 | 23900 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "cix", "effort": "maximum", "force": "predictor", "mode": "pipeline"}` | 16489 | 0.14 / 0.09 | 23892 / 20736 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "count-range", "effort": "maximum", "force": "predictor", "mode": "pipeline"}` | 15821 | 0.28 / 0.28 | 23892 / 20736 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "deflate", "effort": "maximum", "force": "predictor", "mode": "pipeline"}` | 15243 | 0.14 / 0.09 | 23824 / 20736 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "cix", "effort": "maximum", "force": "bwt", "mode": "pipeline"}` | 15796 | 0.24 / 0.11 | 23892 / 23552 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "count-range", "effort": "maximum", "force": "bwt", "mode": "pipeline"}` | 15470 | 0.41 / 0.27 | 23900 / 23808 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "deflate", "effort": "maximum", "force": "bwt", "mode": "pipeline"}` | 15712 | 0.23 / 0.08 | 23808 / 23552 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "cix", "effort": "maximum", "force": "stride", "mode": "pipeline"}` | 13933 | 0.13 / 0.08 | 23896 / 20992 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "count-range", "effort": "maximum", "force": "stride", "mode": "pipeline"}` | 13942 | 0.25 / 0.08 | 23904 / 20992 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "deflate", "effort": "maximum", "force": "stride", "mode": "pipeline"}` | 13074 | 0.12 / 0.07 | 23808 / 20992 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "hybrid", "effort": "maximum", "force": "phrases", "mode": "pipeline"}` | 12746 | 0.14 / 0.07 | 23828 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "hybrid", "effort": "maximum", "force": "ppm", "mode": "pipeline"}` | 20956 | 0.88 / 0.84 | 26112 / 29260 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"backend": "hybrid", "effort": "maximum", "force": "mixture", "mode": "pipeline"}` | — | 4.12 / 0.05 | 202964 / 20480 | ROUTE_TIME_BUDGET |
| fcbench-msg (development) | `{"disable": ["runs"], "effort": "balanced", "mode": "pipeline"}` | 12746 | 0.48 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"disable": ["deflate"], "effort": "balanced", "mode": "pipeline"}` | 12746 | 0.48 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"disable": ["composition"], "effort": "balanced", "mode": "pipeline"}` | 12746 | 0.5 / 0.07 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"disable": ["lz"], "effort": "balanced", "mode": "pipeline"}` | 12746 | 0.35 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"disable": ["predictor"], "effort": "balanced", "mode": "pipeline"}` | 12746 | 0.46 / 0.06 | 23552 / 20736 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"disable": ["bwt"], "effort": "balanced", "mode": "pipeline"}` | 12746 | 0.35 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"disable": ["stride"], "effort": "balanced", "mode": "pipeline"}` | 12746 | 0.47 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"disable": ["phrases"], "effort": "balanced", "mode": "pipeline"}` | 13074 | 0.44 / 0.06 | 23552 / 20992 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"disable": ["ppm"], "effort": "balanced", "mode": "pipeline"}` | 12746 | 0.49 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"disable": ["mixture"], "effort": "balanced", "mode": "pipeline"}` | 12746 | 0.48 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (development) | `{"effort": "maximum", "mode": "pipeline", "offline": true}` | 12746 | 5.37 / 0.06 | 198840 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"mode": "baseline"}` | 618 | 2.41 / 0.11 | 37492 / 20992 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"mode": "gzip"}` | 474 | 0.03 / 0.04 | 13568 / 13312 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"mode": "bzip2"}` | 649 | 0.04 / 0.03 | 13824 / 13568 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"mode": "xz"}` | 472 | 0.05 / 0.03 | 30208 / 13568 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"mode": "brotli"}` | 367 | 0.03 / 0.04 | 15360 / 13824 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"effort": "fast", "mode": "pipeline"}` | 500 | 0.17 / 0.07 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"effort": "balanced", "mode": "pipeline"}` | 500 | 0.34 / 0.07 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"effort": "maximum", "mode": "pipeline"}` | 500 | 4.53 / 0.06 | 25956 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "hybrid", "effort": "maximum", "force": "composition", "mode": "pipeline"}` | 3258 | 0.13 / 0.11 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "cix", "effort": "maximum", "force": "lz", "mode": "pipeline"}` | 500 | 0.13 / 0.07 | 23296 / 20736 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "count-range", "effort": "maximum", "force": "lz", "mode": "pipeline"}` | 503 | 0.13 / 0.07 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "deflate", "effort": "maximum", "force": "lz", "mode": "pipeline"}` | 516 | 0.13 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "cix", "effort": "maximum", "force": "predictor", "mode": "pipeline"}` | 2408 | 0.15 / 0.13 | 23552 / 20736 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "count-range", "effort": "maximum", "force": "predictor", "mode": "pipeline"}` | 2440 | 0.19 / 0.14 | 23552 / 20736 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "deflate", "effort": "maximum", "force": "predictor", "mode": "pipeline"}` | 644 | 0.14 / 0.08 | 23296 / 20736 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "cix", "effort": "maximum", "force": "bwt", "mode": "pipeline"}` | 595 | 0.2 / 0.07 | 23552 / 23296 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "count-range", "effort": "maximum", "force": "bwt", "mode": "pipeline"}` | 601 | 0.19 / 0.07 | 23552 / 23552 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "deflate", "effort": "maximum", "force": "bwt", "mode": "pipeline"}` | 548 | 0.2 / 0.07 | 23552 / 23552 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "cix", "effort": "maximum", "force": "stride", "mode": "pipeline"}` | 1468 | 0.14 / 0.07 | 23296 / 20736 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "count-range", "effort": "maximum", "force": "stride", "mode": "pipeline"}` | 1473 | 0.16 / 0.07 | 23552 / 20736 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "deflate", "effort": "maximum", "force": "stride", "mode": "pipeline"}` | 709 | 0.12 / 0.06 | 23040 / 20992 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "hybrid", "effort": "maximum", "force": "phrases", "mode": "pipeline"}` | 584 | 0.14 / 0.07 | 23040 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "hybrid", "effort": "maximum", "force": "ppm", "mode": "pipeline"}` | 1643 | 0.23 / 0.2 | 23552 / 20736 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"backend": "hybrid", "effort": "maximum", "force": "mixture", "mode": "pipeline"}` | — | 4.11 / 0.06 | 26048 / 20480 | ROUTE_TIME_BUDGET |
| fcbench-mhd (development) | `{"disable": ["runs"], "effort": "balanced", "mode": "pipeline"}` | 500 | 0.33 / 0.07 | 23296 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"disable": ["deflate"], "effort": "balanced", "mode": "pipeline"}` | 500 | 0.34 / 0.07 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"disable": ["composition"], "effort": "balanced", "mode": "pipeline"}` | 500 | 0.31 / 0.06 | 23296 / 20736 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"disable": ["lz"], "effort": "balanced", "mode": "pipeline"}` | 542 | 0.33 / 0.07 | 23552 / 23552 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"disable": ["predictor"], "effort": "balanced", "mode": "pipeline"}` | 500 | 0.28 / 0.07 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"disable": ["bwt"], "effort": "balanced", "mode": "pipeline"}` | 500 | 0.25 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"disable": ["stride"], "effort": "balanced", "mode": "pipeline"}` | 500 | 0.3 / 0.07 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"disable": ["phrases"], "effort": "balanced", "mode": "pipeline"}` | 500 | 0.35 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"disable": ["ppm"], "effort": "balanced", "mode": "pipeline"}` | 500 | 0.34 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"disable": ["mixture"], "effort": "balanced", "mode": "pipeline"}` | 500 | 0.34 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (development) | `{"effort": "maximum", "mode": "pipeline", "offline": true}` | 500 | 4.5 / 0.06 | 25640 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"mode": "baseline"}` | 2810 | 2.71 / 0.13 | 38572 / 21248 | VERIFIED_SCREENING |
| golf (development) | `{"mode": "gzip"}` | 2745 | 0.03 / 0.03 | 13568 / 13568 | VERIFIED_SCREENING |
| golf (development) | `{"mode": "bzip2"}` | 2834 | 0.04 / 0.04 | 13824 / 13568 | VERIFIED_SCREENING |
| golf (development) | `{"mode": "xz"}` | 2572 | 0.05 / 0.03 | 30208 / 13568 | VERIFIED_SCREENING |
| golf (development) | `{"mode": "brotli"}` | 2619 | 0.04 / 0.04 | 16640 / 13824 | VERIFIED_SCREENING |
| golf (development) | `{"effort": "fast", "mode": "pipeline"}` | 2853 | 0.21 / 0.05 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"effort": "balanced", "mode": "pipeline"}` | 2853 | 0.45 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"effort": "maximum", "mode": "pipeline"}` | 2853 | 4.67 / 0.05 | 56180 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "hybrid", "effort": "maximum", "force": "composition", "mode": "pipeline"}` | 11308 | 0.16 / 0.15 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "cix", "effort": "maximum", "force": "lz", "mode": "pipeline"}` | 3045 | 0.14 / 0.1 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "count-range", "effort": "maximum", "force": "lz", "mode": "pipeline"}` | 3060 | 0.16 / 0.09 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "deflate", "effort": "maximum", "force": "lz", "mode": "pipeline"}` | 3093 | 0.13 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "cix", "effort": "maximum", "force": "predictor", "mode": "pipeline"}` | 7363 | 0.18 / 0.15 | 23552 / 20736 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "count-range", "effort": "maximum", "force": "predictor", "mode": "pipeline"}` | 7395 | 0.2 / 0.16 | 23552 / 20736 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "deflate", "effort": "maximum", "force": "predictor", "mode": "pipeline"}` | 5529 | 0.13 / 0.08 | 23296 / 20992 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "cix", "effort": "maximum", "force": "bwt", "mode": "pipeline"}` | 3165 | 0.2 / 0.11 | 23296 / 23296 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "count-range", "effort": "maximum", "force": "bwt", "mode": "pipeline"}` | 3187 | 0.23 / 0.11 | 23552 / 23552 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "deflate", "effort": "maximum", "force": "bwt", "mode": "pipeline"}` | 3163 | 0.19 / 0.07 | 23552 / 23552 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "cix", "effort": "maximum", "force": "stride", "mode": "pipeline"}` | 13160 | 0.17 / 0.16 | 23296 / 21248 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "count-range", "effort": "maximum", "force": "stride", "mode": "pipeline"}` | 13192 | 0.23 / 0.17 | 23040 / 21504 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "deflate", "effort": "maximum", "force": "stride", "mode": "pipeline"}` | 7150 | 0.12 / 0.07 | 23296 / 21504 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "hybrid", "effort": "maximum", "force": "phrases", "mode": "pipeline"}` | 3849 | 0.17 / 0.06 | 23296 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "hybrid", "effort": "maximum", "force": "ppm", "mode": "pipeline"}` | 3678 | 0.27 / 0.24 | 23552 / 21504 | VERIFIED_SCREENING |
| golf (development) | `{"backend": "hybrid", "effort": "maximum", "force": "mixture", "mode": "pipeline"}` | — | 4.12 / 0.06 | 54724 / 20480 | ROUTE_TIME_BUDGET |
| golf (development) | `{"disable": ["runs"], "effort": "balanced", "mode": "pipeline"}` | 2853 | 0.44 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"disable": ["deflate"], "effort": "balanced", "mode": "pipeline"}` | 2989 | 0.43 / 0.1 | 23552 / 23552 | VERIFIED_SCREENING |
| golf (development) | `{"disable": ["composition"], "effort": "balanced", "mode": "pipeline"}` | 2853 | 0.39 / 0.06 | 23296 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"disable": ["lz"], "effort": "balanced", "mode": "pipeline"}` | 2853 | 0.4 / 0.06 | 23296 / 20736 | VERIFIED_SCREENING |
| golf (development) | `{"disable": ["predictor"], "effort": "balanced", "mode": "pipeline"}` | 2853 | 0.39 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"disable": ["bwt"], "effort": "balanced", "mode": "pipeline"}` | 2853 | 0.35 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"disable": ["stride"], "effort": "balanced", "mode": "pipeline"}` | 2853 | 0.37 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"disable": ["phrases"], "effort": "balanced", "mode": "pipeline"}` | 2853 | 0.44 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"disable": ["ppm"], "effort": "balanced", "mode": "pipeline"}` | 2853 | 0.46 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"disable": ["mixture"], "effort": "balanced", "mode": "pipeline"}` | 2853 | 0.44 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (development) | `{"effort": "maximum", "mode": "pipeline", "offline": true}` | 2853 | 4.62 / 0.06 | 55760 / 20736 | VERIFIED_SCREENING |
| fcbench-pt-heldout (heldout) | `{"mode": "baseline"}` | 13361 | 4.74 / 0.27 | 49388 / 22784 | VERIFIED_SCREENING |
| fcbench-pt-heldout (heldout) | `{"mode": "gzip"}` | 15674 | 0.03 / 0.04 | 13568 / 13568 | VERIFIED_SCREENING |
| fcbench-pt-heldout (heldout) | `{"mode": "bzip2"}` | 16453 | 0.04 / 0.04 | 13824 / 13568 | VERIFIED_SCREENING |
| fcbench-pt-heldout (heldout) | `{"mode": "xz"}` | 13684 | 0.05 / 0.04 | 30208 / 13568 | VERIFIED_SCREENING |
| fcbench-pt-heldout (heldout) | `{"mode": "brotli"}` | 15292 | 0.03 / 0.04 | 16640 / 13824 | VERIFIED_SCREENING |
| fcbench-pt-heldout (heldout) | `{"effort": "fast", "mode": "pipeline"}` | 12749 | 0.19 / 0.07 | 23296 / 20992 | VERIFIED_SCREENING |
| fcbench-pt-heldout (heldout) | `{"effort": "balanced", "mode": "pipeline"}` | 12749 | 0.37 / 0.06 | 23296 / 20992 | VERIFIED_SCREENING |
| fcbench-pt-heldout (heldout) | `{"effort": "maximum", "mode": "pipeline"}` | 12749 | 5.15 / 0.06 | 217580 / 20992 | VERIFIED_SCREENING |
| fcbench-rsim-heldout (heldout) | `{"mode": "baseline"}` | 29 | 0.68 / 0.07 | 36864 / 19968 | VERIFIED_SCREENING |
| fcbench-rsim-heldout (heldout) | `{"mode": "gzip"}` | 56 | 0.03 / 0.04 | 13568 / 13312 | VERIFIED_SCREENING |
| fcbench-rsim-heldout (heldout) | `{"mode": "bzip2"}` | 52 | 0.04 / 0.03 | 13312 / 13568 | VERIFIED_SCREENING |
| fcbench-rsim-heldout (heldout) | `{"mode": "xz"}` | 124 | 0.04 / 0.04 | 30208 / 13568 | VERIFIED_SCREENING |
| fcbench-rsim-heldout (heldout) | `{"mode": "brotli"}` | 19 | 0.03 / 0.04 | 14080 / 13824 | VERIFIED_SCREENING |
| fcbench-rsim-heldout (heldout) | `{"effort": "fast", "mode": "pipeline"}` | 103 | 0.18 / 0.06 | 23296 / 20480 | VERIFIED_SCREENING |
| fcbench-rsim-heldout (heldout) | `{"effort": "balanced", "mode": "pipeline"}` | 103 | 0.3 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| fcbench-rsim-heldout (heldout) | `{"effort": "maximum", "mode": "pipeline"}` | 103 | 4.44 / 0.05 | 23552 / 20480 | VERIFIED_SCREENING |
| golf-heldout (heldout) | `{"mode": "baseline"}` | 2740 | 2.52 / 0.12 | 38528 / 21248 | VERIFIED_SCREENING |
| golf-heldout (heldout) | `{"mode": "gzip"}` | 2658 | 0.03 / 0.04 | 13568 / 13568 | VERIFIED_SCREENING |
| golf-heldout (heldout) | `{"mode": "bzip2"}` | 2777 | 0.04 / 0.03 | 13824 / 13568 | VERIFIED_SCREENING |
| golf-heldout (heldout) | `{"mode": "xz"}` | 2496 | 0.05 / 0.04 | 30208 / 13568 | VERIFIED_SCREENING |
| golf-heldout (heldout) | `{"mode": "brotli"}` | 2532 | 0.04 / 0.04 | 16640 / 13824 | VERIFIED_SCREENING |
| golf-heldout (heldout) | `{"effort": "fast", "mode": "pipeline"}` | 2770 | 0.22 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| golf-heldout (heldout) | `{"effort": "balanced", "mode": "pipeline"}` | 2770 | 0.44 / 0.06 | 23296 / 20480 | VERIFIED_SCREENING |
| golf-heldout (heldout) | `{"effort": "maximum", "mode": "pipeline"}` | 2770 | 4.67 / 0.06 | 53748 / 20480 | VERIFIED_SCREENING |
| canterbury-alice29.txt (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 59455 | 1.27 / 0.05 | 23552 / 20480 | VERIFIED_SCREENING |
| canterbury-asyoulik.txt (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 52480 | 1.1 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| canterbury-cp.html (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 8060 | 0.29 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| canterbury-fields.c (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 3221 | 0.19 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| canterbury-grammar.lsp (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 1321 | 0.14 / 0.06 | 23296 / 20480 | VERIFIED_SCREENING |
| canterbury-kennedy.xls (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 82984 | 6.24 / 0.22 | 24064 / 20736 | VERIFIED_SCREENING |
| canterbury-lcet10.txt (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 160456 | 3.43 / 0.06 | 23296 / 20736 | VERIFIED_SCREENING |
| canterbury-plrabn12.txt (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 212458 | 4.03 / 0.06 | 23296 / 20480 | VERIFIED_SCREENING |
| canterbury-ptt5 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 57344 | 2.57 / 0.12 | 23552 / 20736 | VERIFIED_SCREENING |
| canterbury-sum (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 13989 | 0.44 / 0.06 | 23552 / 20736 | VERIFIED_SCREENING |
| canterbury-xargs.1 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 1835 | 0.15 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| calgary-bib (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 40115 | 0.98 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| calgary-book1 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 341964 | 6.31 / 0.06 | 23808 / 20480 | VERIFIED_SCREENING |
| calgary-book2 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 228738 | 4.97 / 0.06 | 23808 / 20480 | VERIFIED_SCREENING |
| calgary-geo (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 52846 | 1.08 / 0.16 | 25528 / 22656 | VERIFIED_SCREENING |
| calgary-news (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 155832 | 3.25 / 0.06 | 23552 / 20736 | VERIFIED_SCREENING |
| calgary-obj1 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 10416 | 0.32 / 0.06 | 23296 / 20480 | VERIFIED_SCREENING |
| calgary-obj2 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 86198 | 2.15 / 0.06 | 23552 / 20736 | VERIFIED_SCREENING |
| calgary-paper1 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 19710 | 0.55 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| calgary-paper2 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 32062 | 0.78 / 0.06 | 23296 / 20480 | VERIFIED_SCREENING |
| calgary-paper3 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 19057 | 0.5 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| calgary-paper4 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 5616 | 0.23 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| calgary-paper5 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 5075 | 0.22 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| calgary-paper6 (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 13793 | 0.45 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| calgary-pic (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 57344 | 2.52 / 0.12 | 23296 / 20736 | VERIFIED_SCREENING |
| calgary-progc (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 13982 | 0.42 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| calgary-progl (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 17419 | 0.66 / 0.05 | 23552 / 20480 | VERIFIED_SCREENING |
| calgary-progp (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 11905 | 0.47 / 0.06 | 23296 / 20480 | VERIFIED_SCREENING |
| calgary-trans (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 23291 | 0.8 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| artificial-a.txt (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 96 | 0.11 / 0.07 | 23552 / 20480 | VERIFIED_SCREENING |
| artificial-aaa.txt (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 233 | 0.47 / 0.06 | 23552 / 20480 | VERIFIED_SCREENING |
| artificial-alphabet.txt (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 464 | 0.41 / 0.07 | 23552 / 20736 | VERIFIED_SCREENING |
| artificial-random.txt (generic-regression) | `{"effort": "fast", "mode": "pipeline"}` | 75985 | 1.04 / 0.05 | 26016 / 20480 | VERIFIED_SCREENING |
| golf-scaling (scaling) | `{"backend": "hybrid", "block": 16384, "effort": "balanced", "force": "lz", "history": 0, "mode": "pipeline"}` | 24037 | 0.43 / 0.2 | 23552 / 20736 | VERIFIED_SCREENING |
| golf-scaling (scaling) | `{"backend": "hybrid", "block": 65536, "effort": "balanced", "force": "lz", "history": 0, "mode": "pipeline"}` | 20081 | 0.34 / 0.11 | 23552 / 20736 | VERIFIED_SCREENING |
| golf-scaling (scaling) | `{"backend": "hybrid", "block": 16384, "effort": "balanced", "force": "lz", "history": 65536, "mode": "pipeline"}` | 20262 | 0.49 / 0.22 | 23552 / 20992 | VERIFIED_SCREENING |
| golf-scaling (scaling) | `{"backend": "hybrid", "block": 65536, "effort": "balanced", "force": "lz", "history": 65536, "mode": "pipeline"}` | 19117 | 0.37 / 0.11 | 23552 / 20992 | VERIFIED_SCREENING |
| fcbench-msg (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "lz"}` | 15169 | 0.19 / 0.26 | 26368 / 20736 | VERIFIED_SCREENING |
| fcbench-msg (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "lz"}` | 15221 | 0.27 / 0.28 | 26368 / 20480 | VERIFIED_SCREENING |
| fcbench-msg (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "predictor"}` | 15786 | 0.18 / 0.27 | 22528 / 20736 | VERIFIED_SCREENING |
| fcbench-msg (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "predictor"}` | 15821 | 0.25 / 0.28 | 22528 / 20736 | VERIFIED_SCREENING |
| fcbench-msg (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "bwt"}` | 15407 | 0.28 / 0.26 | 25088 / 23808 | VERIFIED_SCREENING |
| fcbench-msg (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "bwt"}` | 15470 | 0.36 / 0.27 | 25344 / 23552 | VERIFIED_SCREENING |
| fcbench-msg (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "stride"}` | 14014 | 0.15 / 0.22 | 23040 / 21248 | VERIFIED_SCREENING |
| fcbench-msg (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "stride"}` | 14048 | 0.22 / 0.24 | 23040 / 20992 | VERIFIED_SCREENING |
| fcbench-mhd (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "lz"}` | 506 | 0.1 / 0.07 | 23296 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "lz"}` | 511 | 0.09 / 0.06 | 23296 / 20480 | VERIFIED_SCREENING |
| fcbench-mhd (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "predictor"}` | 2408 | 0.13 / 0.13 | 22528 / 20736 | VERIFIED_SCREENING |
| fcbench-mhd (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "predictor"}` | 2440 | 0.15 / 0.13 | 22528 / 20736 | VERIFIED_SCREENING |
| fcbench-mhd (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "bwt"}` | 595 | 0.16 / 0.07 | 24832 / 23552 | VERIFIED_SCREENING |
| fcbench-mhd (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "bwt"}` | 601 | 0.16 / 0.07 | 24576 / 23552 | VERIFIED_SCREENING |
| fcbench-mhd (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "stride"}` | 1661 | 0.11 / 0.1 | 23040 / 20992 | VERIFIED_SCREENING |
| fcbench-mhd (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "stride"}` | 1695 | 0.13 / 0.11 | 23040 / 20992 | VERIFIED_SCREENING |
| golf (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "lz"}` | 3045 | 0.12 / 0.09 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "lz"}` | 3060 | 0.14 / 0.09 | 23552 / 20480 | VERIFIED_SCREENING |
| golf (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "predictor"}` | 7363 | 0.13 / 0.14 | 22528 / 20736 | VERIFIED_SCREENING |
| golf (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "predictor"}` | 7395 | 0.18 / 0.16 | 22528 / 20736 | VERIFIED_SCREENING |
| golf (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "bwt"}` | 3165 | 0.17 / 0.11 | 25344 / 23552 | VERIFIED_SCREENING |
| golf (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "bwt"}` | 3187 | 0.19 / 0.11 | 25344 / 23552 | VERIFIED_SCREENING |
| golf (coder-control) | `{"coder": "exact", "mode": "forced-ordering", "route": "stride"}` | 13160 | 0.14 / 0.16 | 23040 / 21248 | VERIFIED_SCREENING |
| golf (coder-control) | `{"coder": "count-range", "mode": "forced-ordering", "route": "stride"}` | 13192 | 0.2 / 0.18 | 23040 / 21504 | VERIFIED_SCREENING |
