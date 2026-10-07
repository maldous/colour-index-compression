# Complete larger-window prerequisite gate

All 29 original and candidate artifacts were checked against the corpus manifest,
physical sizes and hashes, then freshly decoded exactly. One frozen generic
policy was used. No candidate stream grew.

- Canterbury: 500,926 → 498,574 bytes (2,352 saved).
- Calgary: 872,234 → 868,817 bytes (3,417 saved).
- Artificial: unchanged per-member sizes; see accompanying JSON.

The canonical core was unchanged; the experiment adds a four-byte hash-chain
LZ parse with the configured history window, chain 32 and lazy matching, then
selects against all incumbent block candidates by framed size. Complete-stream
fallback is also measured. This passes the prerequisite gate, but establishes
no Silesia rank or improvement yet. Native parsing is separately qualified and
was not used in this cohort. The measured Silesia PPM baseline still needs about
49% fewer bytes to tie the published leader, so these modest gains do not yet
provide evidence of a route to first place.
