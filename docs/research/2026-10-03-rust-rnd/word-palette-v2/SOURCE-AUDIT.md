# WPV2 source audit

Prepared at repository revision `2ee5251bf947c71da5056ecd306ca601d8bb0b48`.
No WPV2 build, test, benchmark, or measurement has run.

`rust/cix-native/src/numeric.rs` is relevant prior art: it implements CIXM6
word FOR, delta, delta2, and PFOR payload candidates, including checked word
width and extrema decoding. It does **not** contain an input-derived top-16
exact-word dictionary, five-bit palette indices, escaped raw words, or a WPV2
archive decoder. Its `usize::MAX` eligibility handling and regression fixtures
are not a palette representation.

`rust/cix-native/src/chain.rs` is a frozen mode-7 transform chain selector; it
does not route this experiment. `representation-search-v1/main.rs` supplies a
useful precedent for the stand-alone std-only command line, immutable native
pair, raw fallback, GNU-time child measurement, and archive-only restore.
WPV2 copies none of its candidate search or archive framing.

| Input | SHA-256 |
|---|---|
| `src/numeric.rs` | `fb72d63c238c630076cf5b789ef0c75561b21ea1ff57c529b712adca1b504343` |
| `src/chain.rs` | `1dfbbc8abdf7f257411817e05838559da3c412b1bb79001cd5085cf1d30df9c5` |
| `src/main.rs` | `a73c7c001db9d1c9c92ad5156fb56f31d502d57264b3a284c7b674f1f97e42cb` |
| `experiments/representation-search-v1/main.rs` | `d35d4812007adc32d37e0e691aa8a6d11c6a4c5caaba2270fb9aa094188dc27c` |
| fixed `final/cix` | `71bd7401a0be9a7289de72af3be94f7ca24b2e4ec3d9b38826aeab7f8e0e2b1c` |
| fixed `final/uncix` | `9fbf0a2c448e7f649c704b6827aa513792b9019bf6ed8216314c727f08edff0a` |

The fixture source is the `fixture` function in WPV2. Strong generates eight
deterministic xorshift64 words and emits 1024 words by cycling them 128 times,
for 8192 bytes. Weak generates 896 words
from a 16-word palette and 128 distinct continuing xorshift words. Absent
generates 1024 successive xorshift words. These are data-independent fixture
generators, not a detection policy. Their byte hashes and generator hash are
sealed in `freeze.json` before compilation.

The frozen WPV2 source SHA-256 is
`84a2a554d5fe4eac6d49892ba1361654d19585ce265bd3cacb02ca22bebf73c3`.
