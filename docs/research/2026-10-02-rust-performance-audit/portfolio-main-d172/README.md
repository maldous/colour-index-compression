# Portfolio encoder complexity refactor — d172ce8b4

## Scope

This isolated patch changes only `rust/cix-native/src/main.rs`, plus this
evidence packet.  It decomposes `encode_portfolio` into private helpers for:

- retaining and replacing a verified winner;
- ordered external descriptor evaluation; and
- native adaptive and size-route evaluation.

The original candidate order, strict smaller-only replacement rule, complete
archive comparison, source/incumbent/candidate/restored-output memory
accounting, descriptor decoder admission, BSC/ZPAQ rejection treatment,
deadline checks, route order, diagnostic labels, and final write/flush remain
unchanged.  The refactor neither changes route selection nor candidate breadth.

## Local qualification

The runner declared CPU 18, a 1 GiB cgroup and zero swap. The raw
unit output records result, runtime, peak memory and reported swap use;
independent successful-run cgroup readbacks were not retained, so this
packet qualifies byte/restoration parity, not resource enforcement.

| Check | Result | Receipt |
| --- | --- | --- |
| `cargo check --bin cix` | pass | `raw/check.raw` |
| portfolio, heavy-backend, and backend-registry tests | 17 passed | `raw/targeted-tests.raw` |
| `cargo clippy --bin cix --all-features` | pass; no new portfolio warning | `raw/clippy.raw` |

The test set includes named BEST complete-archive selection and fresh CLI
decoding, canonical direct bzip2 archive checks, empty-input BSC rejection,
stream framing, direct-backend corruption/resource checks, and heavy Brotli/XZ
complete archive restoration.

## Parent/candidate parity

Separate parent and candidate binaries were built from `d172ce8b4` and the
candidate patch.  On the same 9,632-byte deterministic generic input:

- `cix --best --explain -c` produced byte-identical parent/candidate archives.
- `cix --portfolio size --memory 512MiB -c` produced byte-identical
  parent/candidate archives.
- Fresh reciprocal parent/candidate decoders restored each other’s archive
  exactly in both modes.

Archive hashes and all binary/input/output hashes are in
`raw/parent-candidate-parity.raw` and `raw/artifact-sha256.txt`.  The parity
unit completed successfully in 3m38s, with 96.4 MiB peak memory and no swap.

No throughput or compression-ratio improvement is claimed for this
maintainability refactor.
