# Gipfeli decoder-copy-only diagnostic reference

This bundle reproduces the software used for the verified
`buffered-safe-copy-only` diagnostic. It intentionally contains no dataset,
testdata checkout, benchmark driver, archive or production CIX backend.

## Identity

- Upstream: `https://github.com/google/gipfeli.git`
- Pinned source revision: `65b9721308a357f6aa261c11d0af291d10d0b96c`
- Binary: `gipfeli-reference`
- API: `NewGipfeliCompressor`, buffered `Compress` and `Uncompress`
- Squash v0.7 difference: its Gipfeli plugin calls `CompressStream` and
  `UncompressStream` with no options. This diagnostic uses the buffered API
  to isolate decoder behaviour.

`decoder-copy-only.patch` changes only the two buffered decoder copy branches
in `decompress.cc`. It replaces the short unaligned 64-bit copy and
`IncrementalCopyFastPath` selection with bounds-checked `IncrementalCopy`.
The encoder, `ARCH_K8` match path, framing, entropy coder and model state are
unchanged. The patch establishes a local decoder behaviour; it does not prove
a historical cause or qualify Gipfeli as a production CIX backend.

## Software-only checkout

The recorded artifact was built from a local shared clone. The following
equivalent sparse checkout obtains only source software, not benchmark data:

```sh
git clone --filter=blob:none --no-checkout https://github.com/google/gipfeli.git gipfeli-safe-copy-only
git -C gipfeli-safe-copy-only sparse-checkout set --no-cone '/*.cc' '/*.h' '/COPYING'
git -C gipfeli-safe-copy-only checkout --detach 65b9721308a357f6aa261c11d0af291d10d0b96c
git -C gipfeli-safe-copy-only apply ../decoder-copy-only.patch
```

Place the exact `gipfeli_reference.cc` from this bundle next to the source
directory. It conditionally includes `gipfeli-safe-copy-only/gipfeli.h` when
`GIPFELI_SAFE_COPY_ONLY` is defined.

## Recorded build command

The verified diagnostic was compiled on CPU 16 using g++ 13.3.0:

```sh
taskset -c 16 g++ -O3 -DNDEBUG -fno-strict-aliasing -std=c++11 -Wall -Wextra -Wno-sign-compare -Wno-strict-aliasing -I . -DGIPFELI_SAFE_COPY_ONLY -DGIPFELI_BUFFER_API -o gipfeli-reference gipfeli_reference.cc gipfeli-safe-copy-only/decompress.cc gipfeli-safe-copy-only/entropy.cc gipfeli-safe-copy-only/entropy_code_builder.cc gipfeli-safe-copy-only/lz77.cc gipfeli-safe-copy-only/gipfeli-internal.cc
```

Compiled source files are the wrapper plus `decompress.cc`, `entropy.cc`,
`entropy_code_builder.cc`, `lz77.cc` and `gipfeli-internal.cc`; headers are
resolved from the same sparse source checkout. The wrapper exposes:

```text
gipfeli-reference encode INPUT OUTPUT
gipfeli-reference decode ARCHIVE RESTORED
```

An independently supplied input path may be used by a qualified runner. This
bundle does not prescribe, obtain or include an input.
