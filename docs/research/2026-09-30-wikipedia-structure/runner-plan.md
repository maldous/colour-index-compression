# Wikipedia structure screening runner

The matched control is mode `original`: the same bytes, PAQ v216 `-4`, source
filename `source.bin`, and self-contained outer frame as each later representation.
All metadata, mode/selection bytes and PAQ payload bytes count.  The completed
minimum physical frame selects the candidate; no fallback estimate is eligible.

Predeclared input sequence: one deterministic synthetic control and 32 KiB enwik9
development ranges at offsets 0, 100,000,000 and 400,000,000.  Hold-out offsets
600,000,000 and 900,000,000 are untouched.  Each pair has one 300-second shared
budget on CPU 6 with 3 GiB and zero swap.  Decode receives archive only and SHA-256
checks restoration.  The full FX2 reference is NOT_RUN for regional snippets because
it depends on global article order.

| region | offset | SHA-256 |
| --- | ---: | --- |
| development 0 | 0 | `de91bc4727fadadb7abfa3af752e8d7ac6cfb24c87b7cf4078858088dcd4e5c7` |
| development 1 | 100,000,000 | `1849c18fc7184a0499b8ea2150ce55c92c75013e2ee2b60070740872f9beaa9a` |
| development 2 | 400,000,000 | `c156aa97eb5de448bb2d7fefb56556f4e0db414bd2f3b44b2d7fb9b8bb8a3f78` |
| hold-out 0 | 600,000,000 | `d6397620623e371ad01e72ec183d8cb53e95a00eb8b9feb6d2e4439a00f44816` |
| hold-out 1 | 900,000,000 | `ac23e3a57742dc074fe93181d364e56a494644a0ffd9ee0651bb85bdd33d7ecc` |
