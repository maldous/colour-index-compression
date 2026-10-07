# Qualification receipt

The original command output remains at `/tmp/cix-small-codecs-qualification/` outside Git. This receipt retains sanitized selection lines, command forms, exit status, and hashes; it contains no input bytes or binaries.

## Build and limits

All commands exited `0` in a transient user service with these readbacks:

```text
MemoryMax=1073741824
MemorySwapMax=0
TasksMax=16
CPUAffinity=16
```

The candidate was rebuilt with:

```text
cd rust/cix-native
RUSTC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc \
RUSTDOC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustdoc \
CARGO_TARGET_DIR=/tmp/cix-small-codecs-candidate-target \
/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo build --release --bin cix --bin uncix
```

Source artifacts, `base 9214e2f8 -> candidate 88715941e`:

```text
combinatorics.rs de1e5894f62aed63b249356ba960b55f1ef77b31 -> a16b0168ccc55e79c0e0e86f4a7919c2473ea812
histogram.rs     72817614c6ec2adbef3589198954ce268467a1a2 -> 11620c83d31227d9ef1be664d1572c3741bc5249
huffman.rs       e4c0e9e6940a610d74cf7fa695219fdab76543ad -> a12ea41d80de7c811e301155ccfaab6b8f77672f
rank.rs          a6ce9b7d93c75c06c60315bfff912ea79b390b38 -> a61362ce71382baad805daf8b94159e775864e66
candidate cix    603a9d304fe3c158b2ecc89d67a2873f0836aad9c582fd219cf86a7a60ff6214
candidate uncix  899bb902f561a4ae073c0769f193ff4293c2dff060d8441815741a3d35f70dc4
frozen cix       7ead367731b7a97035392473e54c59f55a937de7abc32b871c3028cec126a535
frozen uncix     1a166665722c8f896e73ea0770b8ebd8a06d910f1501cad0474771debdd5e1f7
```

## Archive receipts

The input SHA-256 was `0cd7cffd342ea8475e51fcd337b30829dc7a6b5d9b51541295fc14945273c181`. For each CIXG2 case, frozen and candidate ran the shown command, archives were compared with `cmp`, and each decoder restored the other archive followed by `cmp input.bin output`.

```text
cix --format cixg2 --route composition --backend huffman --block-size 4KiB --memory 128MiB --threads 1 --explain -o ARCHIVE input.bin
archive SHA-256: 138fd582360a3bcb4e9622e1495fded2954e81aaaec5e2404648f539e0f315c1
trace: selected composition backend=huffman for regions 1 and 2 (8192 bytes); regions 3 and 4 selected raw.

cix --format cixg2 --route composition --backend context-range-o2-b8 --block-size 4KiB --memory 128MiB --threads 1 --explain -o ARCHIVE input.bin
archive SHA-256: ababaf0fcb1b027b000686292ccab0eb0bbbca2a01523266afb5762f4749cede
trace: selected composition backend=context-range-o2-b8 for all four regions (13312 bytes).
frozen-decodes-candidate SHA-256: 0cd7cffd342ea8475e51fcd337b30829dc7a6b5d9b51541295fc14945273c181
candidate-decodes-frozen SHA-256: 0cd7cffd342ea8475e51fcd337b30829dc7a6b5d9b51541295fc14945273c181
```

CIXM6 does not emit `--explain`; mode bytes were read from the completed frame after the fixed `CIXM6` header. Frozen/candidate archives were byte-identical and reciprocal decodes matched their input hashes.

```text
cix --format cixm6 --fast --block-size 4KiB --memory 128MiB --threads 1 -o ARCHIVE INPUT
mode 2 context input SHA-256 24982223c7851090ae20c9e4627d54a08c56bbf91462a8d8b4032f938a449416
mode 2 archive SHA-256 03888bc0cc16028adb0fe70b4d41d2e19701e92a7e8c1084ac68826610f90a0c
mode 20 histogram input SHA-256 f8f7e97c55c46d14bc7fe6e7af47f5974cb7dc6444dfbe7f6d3a4273daae51d2
mode 20 archive SHA-256 66bbfbccbd73414b654004cb3f37b8ae6e5cc2e5f81909dbf17255128c63dfcc
```

The earlier forced CIXG1 archive routes were repeated under the same limits and retain the selection evidence instead of being treated as codec-path proof:

```text
cix --format cixg1 --fast --stream --route composition --block-size 4KiB --memory 128MiB --threads 1 --explain -o ARCHIVE input.bin
archive SHA-256 161e6a4ab24a56dc3fcf13ce2b06e3ea473d9edc6fbeb2f4eeee56faaa87859f
trace: composition:deflate selected for all 13312 bytes.

cix --format cixg1 --fast --stream --route runs --block-size 4KiB --memory 128MiB --threads 1 --explain -o ARCHIVE input.bin
archive SHA-256 6d242351ac45e2334f5a19bde7fcae911b3709387c3a1d004194be0a3ecf5c35
trace: runs candidate was evaluated but raw selected for all 13312 bytes.
```

Candidate `uncix` rejected the one-byte-truncated mode-20 archive (`truncated archive`) and mode-2 archive with one byte appended (`trailing bytes after CIXM6 stream`).
