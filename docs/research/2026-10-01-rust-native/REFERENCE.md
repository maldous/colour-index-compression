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
- Initial native milestone: CIXG1 canonical fixed routes raw (0), runs (1), and raw DEFLATE stream coder (3), preserving all frame/header/checksum semantics. Selector and unimplemented routes must be explicitly reported unsupported; no silent fallback.

## Fixture policy

Deterministic fixtures are generated from short literal byte strings and a seeded PRNG, with exact source and archive SHA-256 recorded in `fixtures.json`. Every fixture is decoded independently by Python and Rust. Rust-produced archives are decoded by the frozen Python reference. Fixture files contain no research dataset bytes.
