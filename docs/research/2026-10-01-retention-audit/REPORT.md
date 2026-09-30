# Route-retention evidence report

This report is generated only from frozen collection receipts. Missing, failed and unqualified cells remain visible; no historic reference is merged into current-hardware comparisons.

| Status | Count |
|---|---:|
| FAILED | 43 |
| VERIFIED_SCREENING | 1247 |

## Route matrices

Each evidence set is separate. A cell status is `WIN`, `TIE`, `LOSS`, `UNQUALIFIED`, or `NOT MEASURED`; the latter includes a stated missing-control reason. Percent deltas use `(candidate − control) / control`, so a smaller archive has a negative delta.

| Evidence set | Input | Profile | Route | Archive bytes | Status | Δ bytes | Δ % |
|---|---|---|---|---:|---|---:|---:|
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | runs | 32105 | LOSS | 29284 | 1038.0716058135413 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | composition | 11380 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | lz | 2959 | LOSS | 138 | 4.89188231123715 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | predictor | 5479 | LOSS | 2658 | 94.22190712513293 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | bwt | 2988 | LOSS | 167 | 5.919886565047856 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | stride | 7016 | LOSS | 4195 | 148.7061325771003 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | phrases | 3877 | LOSS | 1056 | 37.43353420772775 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | ppm | 3625 | LOSS | 804 | 28.500531726338178 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | deflate | 2821 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | runs | 32105 | LOSS | 29284 | 1038.0716058135413 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | composition | 11380 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | lz | 2959 | LOSS | 138 | 4.89188231123715 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | predictor | 5479 | LOSS | 2658 | 94.22190712513293 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | bwt | 2988 | LOSS | 167 | 5.919886565047856 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | stride | 7016 | LOSS | 4195 | 148.7061325771003 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | phrases | 3877 | LOSS | 1056 | 37.43353420772775 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | ppm | 3625 | LOSS | 804 | 28.500531726338178 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | deflate | 2821 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | runs | 32105 | LOSS | 29284 | 1038.0716058135413 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | composition | 11380 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | lz | 2959 | LOSS | 138 | 4.89188231123715 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | predictor | 5479 | LOSS | 2658 | 94.22190712513293 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | bwt | 2988 | LOSS | 167 | 5.919886565047856 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | stride | 7016 | LOSS | 4195 | 148.7061325771003 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | phrases | 3877 | LOSS | 1056 | 37.43353420772775 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | ppm | 3625 | LOSS | 804 | 28.500531726338178 |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | deflate | 2821 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | current | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | current | runs | 31897 | LOSS | 29125 | 1050.6854256854258 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | current | composition | 11273 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | current | lz | 2927 | LOSS | 155 | 5.591630591630592 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | current | predictor | 5570 | LOSS | 2798 | 100.93795093795094 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | current | bwt | 2931 | LOSS | 159 | 5.735930735930736 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | current | stride | 7173 | LOSS | 4401 | 158.76623376623377 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | current | phrases | 3896 | LOSS | 1124 | 40.54834054834055 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | current | ppm | 3601 | LOSS | 829 | 29.906204906204906 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | current | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | current | deflate | 2772 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | speed | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | speed | runs | 31897 | LOSS | 29125 | 1050.6854256854258 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | speed | composition | 11273 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | speed | lz | 2927 | LOSS | 155 | 5.591630591630592 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | speed | predictor | 5570 | LOSS | 2798 | 100.93795093795094 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | speed | bwt | 2931 | LOSS | 159 | 5.735930735930736 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | speed | stride | 7173 | LOSS | 4401 | 158.76623376623377 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | speed | phrases | 3896 | LOSS | 1124 | 40.54834054834055 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | speed | ppm | 3601 | LOSS | 829 | 29.906204906204906 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | speed | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | speed | deflate | 2772 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | size | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | size | runs | 31897 | LOSS | 29125 | 1050.6854256854258 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | size | composition | 11273 | TIE | 0 | 0.0 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | size | lz | 2927 | LOSS | 155 | 5.591630591630592 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | size | predictor | 5570 | LOSS | 2798 | 100.93795093795094 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | size | bwt | 2931 | LOSS | 159 | 5.735930735930736 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | size | stride | 7173 | LOSS | 4401 | 158.76623376623377 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | size | phrases | 3896 | LOSS | 1124 | 40.54834054834055 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | size | ppm | 3601 | LOSS | 829 | 29.906204906204906 |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | size | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | compression-golf-github-events-prefix-fresh-midrange-16k | size | deflate | 2772 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-mhd | current | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-mhd | current | runs | 13219 | LOSS | 12655 | 2243.794326241135 |
| prior-exposure-development | fcbench-mhd | current | composition | 3258 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-mhd | current | lz | 500 | WIN | -64 | -11.347517730496454 |
| prior-exposure-development | fcbench-mhd | current | predictor | 644 | LOSS | 80 | 14.184397163120567 |
| prior-exposure-development | fcbench-mhd | current | bwt | 542 | WIN | -22 | -3.900709219858156 |
| prior-exposure-development | fcbench-mhd | current | stride | 709 | LOSS | 145 | 25.70921985815603 |
| prior-exposure-development | fcbench-mhd | current | phrases | 584 | LOSS | 20 | 3.5460992907801416 |
| prior-exposure-development | fcbench-mhd | current | ppm | 1643 | LOSS | 1079 | 191.31205673758865 |
| prior-exposure-development | fcbench-mhd | current | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-mhd | current | deflate | 564 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-mhd | speed | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-mhd | speed | runs | 13219 | LOSS | 12655 | 2243.794326241135 |
| prior-exposure-development | fcbench-mhd | speed | composition | 3258 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-mhd | speed | lz | 500 | WIN | -64 | -11.347517730496454 |
| prior-exposure-development | fcbench-mhd | speed | predictor | 644 | LOSS | 80 | 14.184397163120567 |
| prior-exposure-development | fcbench-mhd | speed | bwt | 542 | WIN | -22 | -3.900709219858156 |
| prior-exposure-development | fcbench-mhd | speed | stride | 709 | LOSS | 145 | 25.70921985815603 |
| prior-exposure-development | fcbench-mhd | speed | phrases | 584 | LOSS | 20 | 3.5460992907801416 |
| prior-exposure-development | fcbench-mhd | speed | ppm | 1643 | LOSS | 1079 | 191.31205673758865 |
| prior-exposure-development | fcbench-mhd | speed | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-mhd | speed | deflate | 564 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-mhd | size | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-mhd | size | runs | 13219 | LOSS | 12655 | 2243.794326241135 |
| prior-exposure-development | fcbench-mhd | size | composition | 3258 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-mhd | size | lz | 500 | WIN | -64 | -11.347517730496454 |
| prior-exposure-development | fcbench-mhd | size | predictor | 644 | LOSS | 80 | 14.184397163120567 |
| prior-exposure-development | fcbench-mhd | size | bwt | 542 | WIN | -22 | -3.900709219858156 |
| prior-exposure-development | fcbench-mhd | size | stride | 709 | LOSS | 145 | 25.70921985815603 |
| prior-exposure-development | fcbench-mhd | size | phrases | 584 | LOSS | 20 | 3.5460992907801416 |
| prior-exposure-development | fcbench-mhd | size | ppm | 1643 | LOSS | 1079 | 191.31205673758865 |
| prior-exposure-development | fcbench-mhd | size | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-mhd | size | deflate | 564 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | current | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | current | runs | 19571 | LOSS | 15939 | 438.84911894273125 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | current | composition | 7117 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | current | lz | 3602 | WIN | -30 | -0.8259911894273128 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | current | predictor | 4688 | LOSS | 1056 | 29.07488986784141 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | current | bwt | 4308 | LOSS | 676 | 18.612334801762113 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | current | stride | 3223 | WIN | -409 | -11.26101321585903 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | current | phrases | 3259 | WIN | -373 | -10.269823788546255 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | current | ppm | 5572 | LOSS | 1940 | 53.414096916299556 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | current | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | current | deflate | 3632 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | speed | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | speed | runs | 19571 | LOSS | 15939 | 438.84911894273125 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | speed | composition | 7117 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | speed | lz | 3602 | WIN | -30 | -0.8259911894273128 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | speed | predictor | 4688 | LOSS | 1056 | 29.07488986784141 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | speed | bwt | 4308 | LOSS | 676 | 18.612334801762113 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | speed | stride | 3223 | WIN | -409 | -11.26101321585903 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | speed | phrases | 3259 | WIN | -373 | -10.269823788546255 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | speed | ppm | 5572 | LOSS | 1940 | 53.414096916299556 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | speed | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | speed | deflate | 3632 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | size | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | size | runs | 19571 | LOSS | 15939 | 438.84911894273125 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | size | composition | 7117 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | size | lz | 3602 | WIN | -30 | -0.8259911894273128 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | size | predictor | 4688 | LOSS | 1056 | 29.07488986784141 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | size | bwt | 4308 | LOSS | 676 | 18.612334801762113 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | size | stride | 3223 | WIN | -409 | -11.26101321585903 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | size | phrases | 3259 | WIN | -373 | -10.269823788546255 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | size | ppm | 5572 | LOSS | 1940 | 53.414096916299556 |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | size | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-mhd-fresh-midrange-16k | size | deflate | 3632 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-msg | current | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-msg | current | runs | 31265 | LOSS | 16433 | 110.79422869471414 |
| prior-exposure-development | fcbench-msg | current | composition | 15524 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-msg | current | lz | 14907 | LOSS | 75 | 0.5056634304207119 |
| prior-exposure-development | fcbench-msg | current | predictor | 15243 | LOSS | 411 | 2.7710355987055015 |
| prior-exposure-development | fcbench-msg | current | bwt | 15477 | LOSS | 645 | 4.348705501618123 |
| prior-exposure-development | fcbench-msg | current | stride | 13074 | WIN | -1758 | -11.852750809061488 |
| prior-exposure-development | fcbench-msg | current | phrases | 12746 | WIN | -2086 | -14.064185544768069 |
| prior-exposure-development | fcbench-msg | current | ppm | 20956 | LOSS | 6124 | 41.2891046386192 |
| prior-exposure-development | fcbench-msg | current | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-msg | current | deflate | 14832 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-msg | speed | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-msg | speed | runs | 31265 | LOSS | 16433 | 110.79422869471414 |
| prior-exposure-development | fcbench-msg | speed | composition | 15524 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-msg | speed | lz | 14907 | LOSS | 75 | 0.5056634304207119 |
| prior-exposure-development | fcbench-msg | speed | predictor | 15243 | LOSS | 411 | 2.7710355987055015 |
| prior-exposure-development | fcbench-msg | speed | bwt | 15477 | LOSS | 645 | 4.348705501618123 |
| prior-exposure-development | fcbench-msg | speed | stride | 13074 | WIN | -1758 | -11.852750809061488 |
| prior-exposure-development | fcbench-msg | speed | phrases | 12746 | WIN | -2086 | -14.064185544768069 |
| prior-exposure-development | fcbench-msg | speed | ppm | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-msg | speed | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-msg | speed | deflate | 14832 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-msg | size | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-msg | size | runs | 31265 | LOSS | 16433 | 110.79422869471414 |
| prior-exposure-development | fcbench-msg | size | composition | 15524 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-msg | size | lz | 14907 | LOSS | 75 | 0.5056634304207119 |
| prior-exposure-development | fcbench-msg | size | predictor | 15243 | LOSS | 411 | 2.7710355987055015 |
| prior-exposure-development | fcbench-msg | size | bwt | 15477 | LOSS | 645 | 4.348705501618123 |
| prior-exposure-development | fcbench-msg | size | stride | 13074 | WIN | -1758 | -11.852750809061488 |
| prior-exposure-development | fcbench-msg | size | phrases | 12746 | WIN | -2086 | -14.064185544768069 |
| prior-exposure-development | fcbench-msg | size | ppm | 20956 | LOSS | 6124 | 41.2891046386192 |
| prior-exposure-development | fcbench-msg | size | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-msg | size | deflate | 14832 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | current | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | current | runs | 32719 | LOSS | 17163 | 110.33041913088198 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | current | composition | 15712 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | current | lz | 15587 | LOSS | 31 | 0.19928002057084082 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | current | predictor | 16286 | LOSS | 730 | 4.692723065055284 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | current | bwt | 16381 | LOSS | 825 | 5.303419902288506 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | current | stride | 13167 | WIN | -2389 | -15.357418359475444 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | current | phrases | 14771 | WIN | -785 | -5.046284391874518 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | current | ppm | 22241 | LOSS | 6685 | 42.973772177937775 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | current | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | current | deflate | 15556 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | speed | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | speed | runs | 32719 | LOSS | 17163 | 110.33041913088198 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | speed | composition | 15712 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | speed | lz | 15587 | LOSS | 31 | 0.19928002057084082 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | speed | predictor | 16286 | LOSS | 730 | 4.692723065055284 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | speed | bwt | 16381 | LOSS | 825 | 5.303419902288506 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | speed | stride | 13167 | WIN | -2389 | -15.357418359475444 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | speed | phrases | 14771 | WIN | -785 | -5.046284391874518 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | speed | ppm | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | speed | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | speed | deflate | 15556 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | size | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | size | runs | 32719 | LOSS | 17163 | 110.33041913088198 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | size | composition | 15712 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | size | lz | 15587 | LOSS | 31 | 0.19928002057084082 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | size | predictor | 16286 | LOSS | 730 | 4.692723065055284 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | size | bwt | 16381 | LOSS | 825 | 5.303419902288506 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | size | stride | 13167 | WIN | -2389 | -15.357418359475444 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | size | phrases | 14771 | WIN | -785 | -5.046284391874518 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | size | ppm | 22241 | LOSS | 6685 | 42.973772177937775 |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | size | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-msg-fresh-midrange-16k | size | deflate | 15556 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-pt-heldout | current | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-pt-heldout | current | runs | 32739 | LOSS | 16978 | 107.7215912695895 |
| prior-exposure-development | fcbench-pt-heldout | current | composition | 16489 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-pt-heldout | current | lz | 15795 | LOSS | 34 | 0.2157223526425988 |
| prior-exposure-development | fcbench-pt-heldout | current | predictor | 16443 | LOSS | 682 | 4.327136603007423 |
| prior-exposure-development | fcbench-pt-heldout | current | bwt | 16428 | LOSS | 667 | 4.231964976841571 |
| prior-exposure-development | fcbench-pt-heldout | current | stride | 12749 | WIN | -3012 | -19.110462534103167 |
| prior-exposure-development | fcbench-pt-heldout | current | phrases | 14629 | WIN | -1132 | -7.182285387982996 |
| prior-exposure-development | fcbench-pt-heldout | current | ppm | 22237 | LOSS | 6476 | 41.08876340333735 |
| prior-exposure-development | fcbench-pt-heldout | current | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-pt-heldout | current | deflate | 15761 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-pt-heldout | speed | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-pt-heldout | speed | runs | 32739 | LOSS | 16978 | 107.7215912695895 |
| prior-exposure-development | fcbench-pt-heldout | speed | composition | 16489 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-pt-heldout | speed | lz | 15795 | LOSS | 34 | 0.2157223526425988 |
| prior-exposure-development | fcbench-pt-heldout | speed | predictor | 16443 | LOSS | 682 | 4.327136603007423 |
| prior-exposure-development | fcbench-pt-heldout | speed | bwt | 16428 | LOSS | 667 | 4.231964976841571 |
| prior-exposure-development | fcbench-pt-heldout | speed | stride | 12749 | WIN | -3012 | -19.110462534103167 |
| prior-exposure-development | fcbench-pt-heldout | speed | phrases | 14629 | WIN | -1132 | -7.182285387982996 |
| prior-exposure-development | fcbench-pt-heldout | speed | ppm | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-pt-heldout | speed | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-pt-heldout | speed | deflate | 15761 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-pt-heldout | size | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-pt-heldout | size | runs | 32739 | LOSS | 16978 | 107.7215912695895 |
| prior-exposure-development | fcbench-pt-heldout | size | composition | 16489 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-pt-heldout | size | lz | 15795 | LOSS | 34 | 0.2157223526425988 |
| prior-exposure-development | fcbench-pt-heldout | size | predictor | 16443 | LOSS | 682 | 4.327136603007423 |
| prior-exposure-development | fcbench-pt-heldout | size | bwt | 16428 | LOSS | 667 | 4.231964976841571 |
| prior-exposure-development | fcbench-pt-heldout | size | stride | 12749 | WIN | -3012 | -19.110462534103167 |
| prior-exposure-development | fcbench-pt-heldout | size | phrases | 14629 | WIN | -1132 | -7.182285387982996 |
| prior-exposure-development | fcbench-pt-heldout | size | ppm | 22237 | LOSS | 6476 | 41.08876340333735 |
| prior-exposure-development | fcbench-pt-heldout | size | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-pt-heldout | size | deflate | 15761 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | current | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | current | runs | 32761 | LOSS | 16969 | 107.45314083080041 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | current | composition | 16489 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | current | lz | 15823 | LOSS | 31 | 0.19630192502532928 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | current | predictor | 16327 | LOSS | 535 | 3.387791286727457 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | current | bwt | 16422 | LOSS | 630 | 3.9893617021276597 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | current | stride | 12990 | WIN | -2802 | -17.743161094224924 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | current | phrases | 14655 | WIN | -1137 | -7.199848024316109 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | current | ppm | 22215 | LOSS | 6423 | 40.672492401215806 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | current | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | current | deflate | 15792 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | speed | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | speed | runs | 32761 | LOSS | 16969 | 107.45314083080041 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | speed | composition | 16489 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | speed | lz | 15823 | LOSS | 31 | 0.19630192502532928 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | speed | predictor | 16327 | LOSS | 535 | 3.387791286727457 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | speed | bwt | 16422 | LOSS | 630 | 3.9893617021276597 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | speed | stride | 12990 | WIN | -2802 | -17.743161094224924 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | speed | phrases | 14655 | WIN | -1137 | -7.199848024316109 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | speed | ppm | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | speed | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | speed | deflate | 15792 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | size | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | size | runs | 32761 | LOSS | 16969 | 107.45314083080041 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | size | composition | 16489 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | size | lz | 15823 | LOSS | 31 | 0.19630192502532928 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | size | predictor | 16327 | LOSS | 535 | 3.387791286727457 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | size | bwt | 16422 | LOSS | 630 | 3.9893617021276597 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | size | stride | 12990 | WIN | -2802 | -17.743161094224924 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | size | phrases | 14655 | WIN | -1137 | -7.199848024316109 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | size | ppm | 22215 | LOSS | 6423 | 40.672492401215806 |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | size | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-pt-heldout-fresh-midrange-16k | size | deflate | 15792 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-rsim-heldout | current | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-rsim-heldout | current | runs | 103 | WIN | -10 | -8.849557522123893 |
| prior-exposure-development | fcbench-rsim-heldout | current | composition | 113 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-rsim-heldout | current | lz | 147 | LOSS | 34 | 30.088495575221238 |
| prior-exposure-development | fcbench-rsim-heldout | current | predictor | 117 | LOSS | 4 | 3.5398230088495577 |
| prior-exposure-development | fcbench-rsim-heldout | current | bwt | 137 | LOSS | 24 | 21.238938053097346 |
| prior-exposure-development | fcbench-rsim-heldout | current | stride | 116 | LOSS | 3 | 2.6548672566371683 |
| prior-exposure-development | fcbench-rsim-heldout | current | phrases | 139 | LOSS | 26 | 23.008849557522122 |
| prior-exposure-development | fcbench-rsim-heldout | current | ppm | 105 | WIN | -8 | -7.079646017699115 |
| prior-exposure-development | fcbench-rsim-heldout | current | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-rsim-heldout | current | deflate | 113 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-rsim-heldout | speed | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-rsim-heldout | speed | runs | 103 | WIN | -10 | -8.849557522123893 |
| prior-exposure-development | fcbench-rsim-heldout | speed | composition | 113 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-rsim-heldout | speed | lz | 147 | LOSS | 34 | 30.088495575221238 |
| prior-exposure-development | fcbench-rsim-heldout | speed | predictor | 117 | LOSS | 4 | 3.5398230088495577 |
| prior-exposure-development | fcbench-rsim-heldout | speed | bwt | 137 | LOSS | 24 | 21.238938053097346 |
| prior-exposure-development | fcbench-rsim-heldout | speed | stride | 116 | LOSS | 3 | 2.6548672566371683 |
| prior-exposure-development | fcbench-rsim-heldout | speed | phrases | 139 | LOSS | 26 | 23.008849557522122 |
| prior-exposure-development | fcbench-rsim-heldout | speed | ppm | 105 | WIN | -8 | -7.079646017699115 |
| prior-exposure-development | fcbench-rsim-heldout | speed | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-rsim-heldout | speed | deflate | 113 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-rsim-heldout | size | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-rsim-heldout | size | runs | 103 | WIN | -10 | -8.849557522123893 |
| prior-exposure-development | fcbench-rsim-heldout | size | composition | 113 | TIE | 0 | 0.0 |
| prior-exposure-development | fcbench-rsim-heldout | size | lz | 147 | LOSS | 34 | 30.088495575221238 |
| prior-exposure-development | fcbench-rsim-heldout | size | predictor | 117 | LOSS | 4 | 3.5398230088495577 |
| prior-exposure-development | fcbench-rsim-heldout | size | bwt | 137 | LOSS | 24 | 21.238938053097346 |
| prior-exposure-development | fcbench-rsim-heldout | size | stride | 116 | LOSS | 3 | 2.6548672566371683 |
| prior-exposure-development | fcbench-rsim-heldout | size | phrases | 139 | LOSS | 26 | 23.008849557522122 |
| prior-exposure-development | fcbench-rsim-heldout | size | ppm | 105 | WIN | -8 | -7.079646017699115 |
| prior-exposure-development | fcbench-rsim-heldout | size | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | fcbench-rsim-heldout | size | deflate | 113 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | current | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | current | runs | 32537 | LOSS | 18095 | 125.2942805705581 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | current | composition | 14510 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | current | lz | 14492 | LOSS | 50 | 0.34621243595069934 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | current | predictor | 13772 | WIN | -670 | -4.639246641739371 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | current | bwt | 15440 | LOSS | 998 | 6.910400221575959 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | current | stride | 11544 | WIN | -2898 | -20.066472787702534 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | current | phrases | 14557 | LOSS | 115 | 0.7962886026866085 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | current | ppm | 20095 | LOSS | 5653 | 39.14277800858607 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | current | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | current | deflate | 14442 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | speed | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | speed | runs | 32537 | LOSS | 18095 | 125.2942805705581 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | speed | composition | 14510 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | speed | lz | 14492 | LOSS | 50 | 0.34621243595069934 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | speed | predictor | 13772 | WIN | -670 | -4.639246641739371 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | speed | bwt | 15440 | LOSS | 998 | 6.910400221575959 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | speed | stride | 11544 | WIN | -2898 | -20.066472787702534 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | speed | phrases | 14557 | LOSS | 115 | 0.7962886026866085 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | speed | ppm | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | speed | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | speed | deflate | 14442 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | size | raw | 16479 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | size | runs | 32537 | LOSS | 18095 | 125.2942805705581 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | size | composition | 14510 | TIE | 0 | 0.0 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | size | lz | 14492 | LOSS | 50 | 0.34621243595069934 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | size | predictor | 13772 | WIN | -670 | -4.639246641739371 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | size | bwt | 15440 | LOSS | 998 | 6.910400221575959 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | size | stride | 11544 | WIN | -2898 | -20.066472787702534 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | size | phrases | 14557 | LOSS | 115 | 0.7962886026866085 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | size | ppm | 20095 | LOSS | 5653 | 39.14277800858607 |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | size | mixture | — | UNQUALIFIED | — | — |
| fresh-16kib-replication | fcbench-rsim-heldout-fresh-midrange-16k | size | deflate | 14442 | TIE | 0 | 0.0 |
| prior-exposure-development | golf | current | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | golf | current | runs | 31755 | LOSS | 28902 | 1013.0389064143008 |
| prior-exposure-development | golf | current | composition | 11308 | TIE | 0 | 0.0 |
| prior-exposure-development | golf | current | lz | 3015 | LOSS | 162 | 5.678233438485805 |
| prior-exposure-development | golf | current | predictor | 5529 | LOSS | 2676 | 93.79600420609884 |
| prior-exposure-development | golf | current | bwt | 2989 | LOSS | 136 | 4.766912022432527 |
| prior-exposure-development | golf | current | stride | 7150 | LOSS | 4297 | 150.61338941465124 |
| prior-exposure-development | golf | current | phrases | 3849 | LOSS | 996 | 34.91062039957939 |
| prior-exposure-development | golf | current | ppm | 3678 | LOSS | 825 | 28.916929547844376 |
| prior-exposure-development | golf | current | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | golf | current | deflate | 2853 | TIE | 0 | 0.0 |
| prior-exposure-development | golf | speed | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | golf | speed | runs | 31755 | LOSS | 28902 | 1013.0389064143008 |
| prior-exposure-development | golf | speed | composition | 11308 | TIE | 0 | 0.0 |
| prior-exposure-development | golf | speed | lz | 3015 | LOSS | 162 | 5.678233438485805 |
| prior-exposure-development | golf | speed | predictor | 5529 | LOSS | 2676 | 93.79600420609884 |
| prior-exposure-development | golf | speed | bwt | 2989 | LOSS | 136 | 4.766912022432527 |
| prior-exposure-development | golf | speed | stride | 7150 | LOSS | 4297 | 150.61338941465124 |
| prior-exposure-development | golf | speed | phrases | 3849 | LOSS | 996 | 34.91062039957939 |
| prior-exposure-development | golf | speed | ppm | 3678 | LOSS | 825 | 28.916929547844376 |
| prior-exposure-development | golf | speed | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | golf | speed | deflate | 2853 | TIE | 0 | 0.0 |
| prior-exposure-development | golf | size | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | golf | size | runs | 31755 | LOSS | 28902 | 1013.0389064143008 |
| prior-exposure-development | golf | size | composition | 11308 | TIE | 0 | 0.0 |
| prior-exposure-development | golf | size | lz | 3015 | LOSS | 162 | 5.678233438485805 |
| prior-exposure-development | golf | size | predictor | 5529 | LOSS | 2676 | 93.79600420609884 |
| prior-exposure-development | golf | size | bwt | 2989 | LOSS | 136 | 4.766912022432527 |
| prior-exposure-development | golf | size | stride | 7150 | LOSS | 4297 | 150.61338941465124 |
| prior-exposure-development | golf | size | phrases | 3849 | LOSS | 996 | 34.91062039957939 |
| prior-exposure-development | golf | size | ppm | 3678 | LOSS | 825 | 28.916929547844376 |
| prior-exposure-development | golf | size | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | golf | size | deflate | 2853 | TIE | 0 | 0.0 |
| prior-exposure-development | golf-heldout | current | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | golf-heldout | current | runs | 32063 | LOSS | 29293 | 1057.5090252707582 |
| prior-exposure-development | golf-heldout | current | composition | 11329 | TIE | 0 | 0.0 |
| prior-exposure-development | golf-heldout | current | lz | 2932 | LOSS | 162 | 5.8483754512635375 |
| prior-exposure-development | golf-heldout | current | predictor | 5318 | LOSS | 2548 | 91.985559566787 |
| prior-exposure-development | golf-heldout | current | bwt | 2931 | LOSS | 161 | 5.812274368231047 |
| prior-exposure-development | golf-heldout | current | stride | 7150 | LOSS | 4380 | 158.12274368231047 |
| prior-exposure-development | golf-heldout | current | phrases | 3812 | LOSS | 1042 | 37.6173285198556 |
| prior-exposure-development | golf-heldout | current | ppm | 3556 | LOSS | 786 | 28.375451263537904 |
| prior-exposure-development | golf-heldout | current | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | golf-heldout | current | deflate | 2770 | TIE | 0 | 0.0 |
| prior-exposure-development | golf-heldout | speed | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | golf-heldout | speed | runs | 32063 | LOSS | 29293 | 1057.5090252707582 |
| prior-exposure-development | golf-heldout | speed | composition | 11329 | TIE | 0 | 0.0 |
| prior-exposure-development | golf-heldout | speed | lz | 2932 | LOSS | 162 | 5.8483754512635375 |
| prior-exposure-development | golf-heldout | speed | predictor | 5318 | LOSS | 2548 | 91.985559566787 |
| prior-exposure-development | golf-heldout | speed | bwt | 2931 | LOSS | 161 | 5.812274368231047 |
| prior-exposure-development | golf-heldout | speed | stride | 7150 | LOSS | 4380 | 158.12274368231047 |
| prior-exposure-development | golf-heldout | speed | phrases | 3812 | LOSS | 1042 | 37.6173285198556 |
| prior-exposure-development | golf-heldout | speed | ppm | 3556 | LOSS | 786 | 28.375451263537904 |
| prior-exposure-development | golf-heldout | speed | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | golf-heldout | speed | deflate | 2770 | TIE | 0 | 0.0 |
| prior-exposure-development | golf-heldout | size | raw | 16479 | TIE | 0 | 0.0 |
| prior-exposure-development | golf-heldout | size | runs | 32063 | LOSS | 29293 | 1057.5090252707582 |
| prior-exposure-development | golf-heldout | size | composition | 11329 | TIE | 0 | 0.0 |
| prior-exposure-development | golf-heldout | size | lz | 2932 | LOSS | 162 | 5.8483754512635375 |
| prior-exposure-development | golf-heldout | size | predictor | 5318 | LOSS | 2548 | 91.985559566787 |
| prior-exposure-development | golf-heldout | size | bwt | 2931 | LOSS | 161 | 5.812274368231047 |
| prior-exposure-development | golf-heldout | size | stride | 7150 | LOSS | 4380 | 158.12274368231047 |
| prior-exposure-development | golf-heldout | size | phrases | 3812 | LOSS | 1042 | 37.6173285198556 |
| prior-exposure-development | golf-heldout | size | ppm | 3556 | LOSS | 786 | 28.375451263537904 |
| prior-exposure-development | golf-heldout | size | mixture | — | UNQUALIFIED | — | — |
| prior-exposure-development | golf-heldout | size | deflate | 2770 | TIE | 0 | 0.0 |

Timing uses the median of all three complete leaf encoder/decoder processes. It includes startup, I/O, profiling, and all selector trials, including discarded candidates. Physical sizes include outer framing and all metadata retained in the selected archive.

## Integrated portfolio before/after

Each row is one frozen integrated CIX portfolio result. The v2 delta has equal outer caps (180 s, 2 GB RSS, 100 MB temporary disk); it is a complete-archive portfolio comparison, not a claim for a particular native route.

| Input | Profile | v2 bytes | Selected bytes | Δ bytes | Selected candidate | Best framed external |
|---|---|---:|---:|---:|---|---:|
| fcbench-msg | current | 12746 | 12746 | 0 | cix-adaptive | 13391 |
| fcbench-msg | speed | 14832 | 14832 | 0 | cix-adaptive | 14847 |
| fcbench-msg | size | 12746 | 12731 | -15 | xz:direct | 12731 |
| fcbench-mhd | current | 500 | 438 | -62 | zstd:direct | 438 |
| fcbench-mhd | speed | 500 | 500 | 0 | cix-adaptive | 598 |
| fcbench-mhd | size | 500 | 431 | -69 | zstd:direct | 431 |
| golf | current | 2853 | 2619 | -234 | xz:direct | 2619 |
| golf | speed | 2853 | 2853 | 0 | cix-adaptive | 3052 |
| golf | size | 2853 | 2615 | -238 | xz:direct | 2615 |
| fcbench-pt-heldout | current | 12749 | 12749 | 0 | cix-adaptive | 13731 |
| fcbench-pt-heldout | speed | 12749 | 12749 | 0 | cix-adaptive | 15740 |
| fcbench-pt-heldout | size | 12749 | 12749 | 0 | cix-adaptive | 13731 |
| fcbench-rsim-heldout | current | 103 | 76 | -27 | zstd:direct | 76 |
| fcbench-rsim-heldout | speed | 103 | 103 | 0 | cix-adaptive | 125 |
| fcbench-rsim-heldout | size | 103 | 75 | -28 | zstd:direct | 75 |
| golf-heldout | current | 2770 | 2543 | -227 | xz:direct | 2543 |
| golf-heldout | speed | 2770 | 2770 | 0 | cix-adaptive | 2945 |
| golf-heldout | size | 2770 | 2535 | -235 | xz:direct | 2535 |
| compression-golf-github-events-prefix-fresh-midrange-16k | current | 2772 | 2551 | -221 | xz:direct | 2551 |
| compression-golf-github-events-prefix-fresh-midrange-16k | speed | 2772 | 2772 | 0 | cix-adaptive | 2937 |
| compression-golf-github-events-prefix-fresh-midrange-16k | size | 2772 | 2551 | -221 | xz:direct | 2551 |
| compression-golf-github-events-offset-1048576-fresh-midrange-16k | current | 2821 | 2575 | -246 | xz:direct | 2575 |
| compression-golf-github-events-offset-1048576-fresh-midrange-16k | speed | 2821 | 2821 | 0 | cix-adaptive | 2949 |
| compression-golf-github-events-offset-1048576-fresh-midrange-16k | size | 2821 | 2571 | -250 | xz:direct | 2571 |
| fcbench-mhd-fresh-midrange-16k | current | 3223 | 3119 | -104 | xz:direct | 3119 |
| fcbench-mhd-fresh-midrange-16k | speed | 3223 | 3223 | 0 | cix-adaptive | 3676 |
| fcbench-mhd-fresh-midrange-16k | size | 3223 | 3123 | -100 | xz:direct | 3123 |
| fcbench-pt-heldout-fresh-midrange-16k | current | 12990 | 12990 | 0 | cix-adaptive | 13839 |
| fcbench-pt-heldout-fresh-midrange-16k | speed | 12990 | 12990 | 0 | cix-adaptive | 15780 |
| fcbench-pt-heldout-fresh-midrange-16k | size | 12990 | 12990 | 0 | cix-adaptive | 13839 |
| fcbench-msg-fresh-midrange-16k | current | 13167 | 13167 | 0 | cix-adaptive | 14467 |
| fcbench-msg-fresh-midrange-16k | speed | 13167 | 13167 | 0 | cix-adaptive | 15543 |
| fcbench-msg-fresh-midrange-16k | size | 13167 | 13167 | 0 | cix-adaptive | 14467 |
| fcbench-rsim-heldout-fresh-midrange-16k | current | 11544 | 11544 | 0 | cix-adaptive | 13063 |
| fcbench-rsim-heldout-fresh-midrange-16k | speed | 11544 | 11544 | 0 | cix-adaptive | 14461 |
| fcbench-rsim-heldout-fresh-midrange-16k | size | 11544 | 11544 | 0 | cix-adaptive | 13023 |

The fast profile has a fixed shortlist. Its bzip2/XZ diagnostics are reported separately and are not silently treated as production candidates. The offline oracle records whether a completed wider candidate set beat the integrated plan; CIXM6 remains outside the integrated portfolio universe.

## Optional native recode

Scope: one native recoding pass over each frozen baseline CIXG1 selected archive, not every new external backend archive.
Strict native-recode wins: 0. Unchanged or rejected recodes: 36. A larger or tied native recode is never selected.

## 64 KiB scaling

| Input | Profile | Baseline bytes | Integrated bytes | Δ bytes |
|---|---|---:|---:|---:|
| compression-golf-github-events-offset-1048576-fresh-scaling-64k | current | 9792 | 7715 | -2077 |
| compression-golf-github-events-offset-1048576-fresh-scaling-64k | size | 9008 | 7727 | -1281 |
| compression-golf-github-events-prefix-fresh-scaling-64k | current | 10087 | 8023 | -2064 |
| compression-golf-github-events-prefix-fresh-scaling-64k | size | 9405 | 8055 | -1350 |
| fcbench-mhd-fresh-scaling-64k | current | 1905 | 1748 | -157 |
| fcbench-mhd-fresh-scaling-64k | size | 1812 | 1730 | -82 |
| fcbench-msg-fresh-scaling-64k | current | 50920 | 50920 | 0 |
| fcbench-msg-fresh-scaling-64k | size | 50794 | 50794 | 0 |
| fcbench-pt-heldout-fresh-scaling-64k | current | 50992 | 50992 | 0 |
| fcbench-pt-heldout-fresh-scaling-64k | size | 50447 | 50447 | 0 |
| fcbench-rsim-heldout-fresh-scaling-64k | current | 46317 | 46317 | 0 |
| fcbench-rsim-heldout-fresh-scaling-64k | size | 44980 | 44980 | 0 |

## Explicit fast shortlist penalties

All diagnostics restore exactly in three repetitions. The 47-byte wrapper is charged separately; these forced routes are outside the production fast shortlist.

| Input | Omitted backend | Standalone B | Wrapper B | Complete B | Selected fast B | Shortlist penalty B |
|---|---|---:|---:|---:|---:|---:|
| fcbench-msg | bzip2 | 15201 | 47 | 15248 | 14832 | 0 |
| fcbench-msg | xz | 12692 | 47 | 12739 | 14832 | 2093 |
| fcbench-mhd | bzip2 | 649 | 47 | 696 | 500 | 0 |
| fcbench-mhd | xz | 476 | 47 | 523 | 500 | 0 |
| golf | bzip2 | 2834 | 47 | 2881 | 2853 | 0 |
| golf | xz | 2820 | 47 | 2867 | 2853 | 0 |
| fcbench-pt-heldout | bzip2 | 16453 | 47 | 16500 | 12749 | 0 |
| fcbench-pt-heldout | xz | 13544 | 47 | 13591 | 12749 | 0 |
| fcbench-rsim-heldout | bzip2 | 52 | 47 | 99 | 103 | 4 |
| fcbench-rsim-heldout | xz | 124 | 47 | 171 | 103 | 0 |
| golf-heldout | bzip2 | 2777 | 47 | 2824 | 2770 | 0 |
| golf-heldout | xz | 2716 | 47 | 2763 | 2770 | 7 |
| compression-golf-github-events-prefix-fresh-midrange-16k | bzip2 | 2840 | 47 | 2887 | 2772 | 0 |
| compression-golf-github-events-prefix-fresh-midrange-16k | xz | 2708 | 47 | 2755 | 2772 | 17 |
| compression-golf-github-events-offset-1048576-fresh-midrange-16k | bzip2 | 2845 | 47 | 2892 | 2821 | 0 |
| compression-golf-github-events-offset-1048576-fresh-midrange-16k | xz | 2744 | 47 | 2791 | 2821 | 30 |
| fcbench-mhd-fresh-midrange-16k | bzip2 | 4347 | 47 | 4394 | 3223 | 0 |
| fcbench-mhd-fresh-midrange-16k | xz | 3092 | 47 | 3139 | 3223 | 84 |
| fcbench-pt-heldout-fresh-midrange-16k | bzip2 | 16467 | 47 | 16514 | 12990 | 0 |
| fcbench-pt-heldout-fresh-midrange-16k | xz | 13968 | 47 | 14015 | 12990 | 0 |
| fcbench-msg-fresh-midrange-16k | bzip2 | 16291 | 47 | 16338 | 13167 | 0 |
| fcbench-msg-fresh-midrange-16k | xz | 14528 | 47 | 14575 | 13167 | 0 |
| fcbench-rsim-heldout-fresh-midrange-16k | bzip2 | 15425 | 47 | 15472 | 11544 | 0 |
| fcbench-rsim-heldout-fresh-midrange-16k | xz | 13788 | 47 | 13835 | 11544 | 0 |

## Scope and limits

- Exact reconstruction, archive hashes, three retained repetitions, source-inaccessible decode, and selected-minimum assertions are required for every qualified row.
- Count-range is a matched-information size control that computes exact rank before arithmetic sequence coding. Its timing is not evidence that CIX is faster than range coding.
- Historic specialized Silesia results and CIXM6 are not folded into these generic portfolio results. Program/runtime footprint is reported separately and this report is not a Hutter package-size claim.
- Removal ablations are the 198 already executed v2 diagnostics. No additional targeted-removal counterfactual cells were executed or inferred.
