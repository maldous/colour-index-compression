# Track A result — paid composition feedback

The retained development receipt is `track-a-feedback-first-receipt.json`.
Both representations use arithmetic coding and the same high-nibble predecessor
context; the feedback representation pays its entire sparse successor-count
vector before using the resulting remaining-count deficits as predictor state.

| development input | causal bytes | paid feedback bytes | feedback − causal |
| --- | ---: | ---: | ---: |
| synthetic repeat/edit | 45,530 | 47,437 | +1,907 |
| enwik9 offset 0 | 38,281 | 38,086 | −195 (−0.509%) |
| enwik9 offset 100,000,000 | 37,609 | 37,434 | −175 (−0.465%) |
| enwik9 offset 400,000,000 | 38,922 | 38,697 | −225 (−0.578%) |

The overall four-input total loses 1,312 bytes because the deliberately
different synthetic distribution does not repay its metadata. The predeclared
Wikipedia gate was nevertheless met on two independent development regions.
The observed Wikipedia reductions are attributable to the transmitted
composition information: both residuals use range coding, so they are not a
claim for CIX rank coding.

The immutable promoted source and dependency set is in
`track-a-feedback-promotion-snapshot/`. The same unmodified mechanism then ran
on the previously unread holdouts, recorded in `track-a-feedback-holdout-receipt.json`:

| heldout input | causal bytes | paid feedback bytes | feedback − causal |
| --- | ---: | ---: | ---: |
| enwik9 offset 700,000,000 | 38,277 | 37,974 | −303 (−0.792%) |
| enwik9 offset 850,000,000 | 37,986 | 37,706 | −280 (−0.737%) |

All twelve physical frames (development and holdout) were independently
decoded in a fresh child process and SHA-256 checked. This is a verified local
composition-feedback result, not a Hutter score or a full-corpus projection.
The next test should retain the paid count-vector accounting while replacing
the weak high-nibble context with a stronger decoder-reproducible predictor;
it must compare directly against a range control given the same vector.

## Frozen contiguous scaling check

The validated feedback codec was not retuned after the holdout. On contiguous
enwik9 offset 0 it remained smaller, but the relative gain contracted with
length:

| input | causal bytes | paid feedback bytes | feedback − causal | elapsed |
| --- | ---: | ---: | ---: | ---: |
| 1 MiB | 602,638 | 601,805 | −833 (−0.138%) | 26.934 s |
| 8 MiB | 4,798,139 | 4,796,612 | −1,527 (−0.032%) | 212.745 s |

Both runs used the frozen configuration, logical CPU 2, 2 GiB RAM, no swap and
the 300-second hard tree limit. Both full physical streams independently decoded
and SHA-256 matched. The 8 MiB result establishes that the mechanism is not an
immediate short-block artefact, but its diminishing relative return means it is
not ready for a larger promotion or an incumbent claim. These codecs remain much
larger than stronger general-purpose baselines; the result is only a matched
mechanism measurement.
