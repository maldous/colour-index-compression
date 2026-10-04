# SquashFS profile alignment-probe cleanup

`MODEL_ALIGNMENT` was computed as the offset of `model value` after a leading
`char` in an anonymous structure. Replacing that anonymous type with the named,
translation-unit-private `model_alignment_probe` preserves the member sequence,
member types, and `offsetof` expression. Thus it preserves the required
alignment value for `model`; it changes no public declaration, serialized data,
or object layout used by the codec.

The change is limited to
`rust/cix-native/adapters/squashfs/profile/src/cix_squashfs_profile.c`.
The prior qualified source snapshot is
`192e40b06d410cb689b581d5f8fc8128d83b8fdd0e5f16cba981f189756ac080`; the
current cleanup source is
`597a97bcd3ed91b0d1cfa2bd26cf48a70fe1f3b15ed14b65655f4abebf04e663`.

The job requires the root-dispatched `CIX_RELEASE_LEASE` marker; its specification does not set it. It hashes both before/after headers, the complete portable crate tree, and resolved compiler/archive/disassembler/Cargo tools.

The new job `squashfs-profile-alignment-v1` must compile those exact before and
after sources with the same optimized C flags, require byte-identical objects
and compare raw address-free disassembly only after replacing objdump's explicit object-path preamble, run the existing C profile contract, then reuse
the prior `native_differential.rs` harness for its 1,545 exact-choice cases and
both stack/caller-workspace decode paths. It is a focused qualification; it
neither rebuilds the kernel module nor reruns the VM.
