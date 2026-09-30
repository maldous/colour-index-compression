# Native Rust migration reference freeze

- Python reference commit: `80b95427725ecf59d626b2982d50f6349abd56e1` (branch `research/silesia-competitive` at isolation).
- Reference worktree: `/home/user/src/colour-index-compression` (left untouched, including its pre-existing modifications and untracked research evidence).
- Rust worktree/branch: `/home/user/src/cix-rust-native`, `feat/cix-rust-native`.
- Python remains the executable correctness oracle. No format version is changed by this migration.

## Formats in the frozen tree

1. `CIXF1`: file wrapper in `cix/fileformat.py`, wrapping the `CIXM6` stream in `cix/multinomial.py`, plus UTF-8 basename, little-endian u32 basename length and terminal `CIXF1` magic.
2. `CIXG1`: generic archive in `cix/pipeline.py`, fixed `<5sII>` header; repeated `<BII32s>` block descriptors and SHA-256 block hashes; final route-255 descriptor with whole-input SHA-256. Route/coder definitions and limits are frozen in `docs/research/2026-09-30-generic-pipeline/FORMAT.md` at the reference commit.

## Reference configurations

- Stream CLI default: level 6 (`cix/cli.py::config_for_level`). Levels 1–9 are existing Python profiles; `--extreme` is a separate profile. This is distinct from generic `CIXG1` efforts.
- Generic selector: `fast`, `balanced`, `maximum`; each block is selected from the frozen route shortlist and complete physical payload sizes. Stream backend defaults to `hybrid` (CIX composition and raw DEFLATE). See `pipeline.py::EFFORTS`, `shortlist`, and `streams`.
- Initial native milestone: CIXG1 canonical fixed routes raw (0), runs (1), and raw DEFLATE stream coder (3), preserving all frame/header/checksum semantics.
- Subsequent parity update: route IDs 2 (composition), 3 (LZ), 4 (predictor), 5 (BWT), 6 (stride), 7 (phrases), and 8 (PPM), plus exact-rank/range type-class substreams, adaptive-range coder 4 (order 0, bucket bits 8), and count-range coder 5 decoding are implemented. Arbitrary-precision integers and 1024-symbol tiles are used. Mixture route 9, count-range encoding, CIXB1 portfolio, and legacy CIXF1/CIXM6 remain unsupported and must be rejected explicitly; no silent fallback.

## Fixture policy

Deterministic fixtures are generated from short literal byte strings and a seeded PRNG, with exact source and archive SHA-256 recorded in `fixtures.json`. Every fixture is decoded independently by Python and Rust. Rust-produced archives are decoded by the frozen Python reference. Fixture files contain no research dataset bytes.
