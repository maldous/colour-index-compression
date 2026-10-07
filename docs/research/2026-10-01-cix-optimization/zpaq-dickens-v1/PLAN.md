# ZPAQ Dickens reproduction and CIX screening — frozen plan

Status: frozen before local compression trials. This is a targeted lead
reproduction and mechanism screen, not Silesia qualification or a ranking.

## Input identity

- Existing official Silesia Dickens file: `/home/user/src/colour-index-compression/benchmark-work/silesia/dickens`
- Length: 10,192,446 bytes
- SHA-256: `b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a`
- No new corpus bytes are fetched or added to the repository.

## Claim under investigation

The imported Squash/peltast result reports 2,142,935 compressed bytes for
`plugin=zpaq, codec=zpaq, level=5`. It is a ZPAQ stream, not a CIX archive.
Squash 0.7.0's ZPAQ plugin passes its `level` option as the method string to
`libzpaq::compress()`. That Squash commit pins libzpaq 7.05 (submodule
`8cf5f8891b6e35f993fd30cc263e1470636627ba`), so the published figure is not
assumed to be a ZPAQ 7.15 result. The local trials include both pinned 7.05
and requested 7.15, each with method `5`, the same input, and a fresh decoder.

## Frozen trial cells

1. Input bytes directly through libzpaq 7.05 `compress(..., "5")` and its
   archive-only decoder. This checks reproduction of the Squash result and
   its plugin stream semantics.
2. Input bytes directly through libzpaq 7.15 `compress(..., "5")` and its
   archive-only decoder. This is the requested version-specific control.
3. Current release Rust CIXG1 `cix --best --route auto` on the same input,
   followed by a fresh `uncix` process. Charge the complete CIX archive.
4. ZPAQ 7.15 method 5 applied to the complete CIX archive from cell 3, then
   archive-only ZPAQ decode followed by a fresh CIX decode. This is explicitly
   a ZPAQ-wrapped CIX backend experiment, not a native CIX model result.

Each process is single-core, CPU-affined, capped at 300 seconds, 2 GiB address
space, 2 GiB cgroup memory, zero cgroup swap, and 100 MB output-file size.
Encoding and decoding are timed separately with GNU `time`; RSS is recorded.
The encoder sees only the source path; the decoder sees only the archive and
output path. Every result records archive bytes, input/output hashes, exact
restoration, tool/source hashes, settings, and complete command lines.

The host is Linux x86_64, Intel Core i9-13900K, GCC 13.3.0, Rust 1.98.1.
This does not make historical Squash CPU times comparable to local timings.

## Frozen software identities

- Squash plugin source: tag v0.7.0, commit `fa5fd7d496ab2210c0a03e4eb07ebd5f0644cfad`.
- Squash ZPAQ plugin passes level text to `libzpaq::compress()` and defaults
  to level 1; level 5 is an explicit benchmark setting.
- Squash's pinned libzpaq: ZPAQ tag 7.05, commit
  `8cf5f8891b6e35f993fd30cc263e1470636627ba`.
- Requested libzpaq: ZPAQ tag 7.15, commit
  `9ab539f644e364f0d92e2918b90ce2534c75653f`.
- Both harnesses call the same libzpaq stream APIs used by the Squash plugin;
  method is exactly the string `5`; default filename/comment/SHA-1 options
  are retained. Harness and source hashes are included in `source-hashes.txt`.
- Rust reference binary SHA-256: `4598ba4b72dad860f1f9f77ade68f023f5b7821e33da784a7a828384edecdfb0`.
- Rust source state: branch `feat/cix-rust-silesia-v3`, HEAD
  `986bbe80eee1daff7ff77739be821a2ede109c37`, plus dirty diff SHA-256
  `bf47e40613a91ba2a3e407bbf8e12ddd278546291fea9b8aa4991d2bf09e6a0c`.

## Interpretation limits

Cell 1 can confirm whether the Squash plugin's compression algorithm and
framing reproduce the published byte count. Cell 2 isolates the ZPAQ version
change. Cell 3 measures the Rust implementation. Cell 4 measures the benefit
or loss from wrapping the complete CIX archive with ZPAQ. It cannot be called
a native CIX modeling improvement. No historical CPU-time comparison is made.

Native adaptive-model and representation trials are separate follow-up cells;
their input, transform metadata, complete framing, selector work, decode path,
and bounded-memory behaviour must be charged before selector promotion.
