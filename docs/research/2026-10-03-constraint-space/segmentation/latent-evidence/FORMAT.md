# LLT1 bounded latent-layout experiment

`latent_layout.rs` is an isolated representation experiment.  It accepts a
regular input of at most 4096 bytes and writes an archive of at most 32768
bytes.  It does not alter the generic policy or production format.

For a nonempty input, a geometry is width `w` in `1..=8` and phase `p` in
`0..w`, subject to `w <= n-p`.  The first `p` source bytes are literal prefix
bytes.  The suffix is addressed row-major: position `p + row*w + lane`.

Each lane uses one paid operator. The first row is literal for every row
operator, including lane zero:

| id | operator |
|---:|---|
| 0 | literal |
| 1 | byte minus previous original row in the same lane |
| 2 | byte minus previous original lane in the row |
| 3 | byte XOR previous original lane in the row |
| 4 | byte XOR previous original row in the same lane |

Operators 2 and 3 are forbidden for lane zero. Decode reconstructs rows and lanes in row-major order, so all
predictors use already reconstructed original bytes.  Partial final rows are
defined by the same position formula.

LLT1 header is 18 bytes: `magic[4]`, `version`, `kind`, source length `u32`,
source CRC-32 `u32`, width `u8`, phase `u8`, lane count `u8`, and raw-prefix
length `u8`, followed by exactly that prefix.  Native-lane kind stores for each
lane `operator:u8, route:u8, decoded_len:u32, payload_len:u32, payload`.
Routes are raw, canonical Huffman, frozen adaptive order-0, legacy LZ effort
1, or native Zstd level 19. Global kind stores a paid operator vector (`w`
bytes) and one `payload_len:u32,payload` Zstd frame. It has no decoder
search.  Zstd requires exactly one frame; Huffman checks its embedded output
length before decoding.

All multi-byte integers are little-endian. CRC is reflected IEEE CRC-32 with
initial and final complement and polynomial `0xedb88320`. Kind `0` is native
lanes and kind `1` is global Zstd. Route IDs are `0=raw`, `1=Huffman`,
`2=adaptive order-0`, `3=legacy LZ effort 1`, and `4=Zstd level 19`.

Policies are deliberately finite:

* `whole`: width 1, phase 0, literal native and literal global-Zstd controls.
* `bss`: literal global-Zstd for each legal geometry.
* `uniform`: whole native literal control plus literal and four uniform
  residual/XOR global-Zstd controls for every legal geometry.
* `mask-control`: raw plus whole native literal controls, literal global-Zstd,
  and every `2^(w-1)` identity/previous-column-subtraction mask under global
  Zstd for each legal geometry. It is a frozen ordinary preprocessing control,
  not an automatic latent-layout selector.
* `auto`: each legal geometry, full five-route per-lane vector plus literal,
  four uniform, and its paid native-vector global-Zstd shortlist controls.
* `oracle`: only when `n<=12`; widths at most 3 and every legal operator
  vector under global Zstd: `3*5^(w-1)`, since lane zero permits 0, 1, or 4.

The tiny oracle is a practical same-family check, not an entropy result.  The
per-lane native vector is separable because every transformed lane is derived
from original source bytes.  Global Zstd is evaluated on a bounded shortlist;
the tiny exhaustive result exposes any shortlist regret.  All complete archive
bytes, selected geometry, operators, backend class, raw fallback, and inverse
verification are emitted as JSON by the encoder. Zstd decode requires one
complete frame with declared content size exactly matching the bounded output
and a frame window no larger than 4096 bytes.

Policy-admissible geometries are narrower than wire-valid geometries: all
policies cap width at3 when n<=12, and at8 otherwise. Whole remains width1
phase0. Auto/oracle have the identical tiny geometry family; exactness is
claimed only within this declared cap, not all wire-legal widths. Every
nonempty policy also admits the explicit raw-whole fallback.
