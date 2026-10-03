# MDC1 model-metadata control: static review

**Reviewed source:** `rust/cix-native/experiments/constraint-space/model_metadata_control.rs`  
**Scope:** source and format arithmetic only. No build, execution, external
codec invocation, or archive was produced for this review.

## Purpose and claim boundary

MDC1 is an archive framing adapter for the established external `zstd` and
`bzip2` controls. It compresses only the stored MSL1 model description. It
leaves the MSL1 sequence-rank body byte-for-byte unchanged, preserves the
original MSL1 CRC byte-for-byte, and adds an MDC1 CRC over the new complete
outer archive.

It is therefore a metadata-only control. A result from MDC1 attributes a size
difference to compression of the stored model bytes by the named standard
codec, including every MDC1 framing byte and both CRCs. It does not establish
a new native model, a new rank coder, or a change in the underlying MSL1
member-set or sequence-rank semantics.

The codec IDs are fixed: `1` is `zstd` and `2` is `bzip2`. The native helper
does not contain either codec implementation; the root-leased experiment must
record the actual external command, program/version, options, and input/output
hashes for each control.

## Exact MDC1 wire accounting

The fixed MDC1 header is 27 bytes. Its fields and offsets are:

| Offset | Length | Field |
|---:|---:|---|
| 0 | 4 | magic `MDC1` |
| 4 | 1 | MDC1 version `1` |
| 5 | 1 | external codec ID (`1` or `2`) |
| 6 | 15 | copied MSL1 base header: `MSL1`, MSL version/kind, source length, record width, alphabet, original uncompressed model length |
| 21 | 2 | compressed-model length, little-endian `u16` |
| 23 | 4 | copied original MSL1 CRC-32 |

The variable body is then:

| Offset | Length | Field |
|---:|---:|---|
| 27 | `compressed_model_length` | externally compressed MSL1 model bytes |
| `27 + compressed_model_length` | remaining bytes before final CRC | copied original MSL1 rank body |
| final 4 bytes | 4 | MDC1 outer CRC-32 over all earlier MDC1 bytes |

Consequently the complete physical size is

```text
31 + compressed_model_bytes + original_rank_bytes
```

where 31 charges the 27-byte MDC1 header and the 4-byte outer CRC. The copied
original CRC is already included in the 27-byte header. The original 15-byte
MSL1 header is copied inside that header and is not an omitted shared asset.

## Native helper pipeline

The helper has four deliberately small operations:

1. `model BASE OUT` validates the original MSL1 envelope/CRC and writes exactly
   `BASE[15 .. 15 + original_model_length]`.
2. The root-leased external control compresses that file with the codec named
   by the later MDC1 codec ID.
3. `pack CODEC BASE COMPRESSED OUT` validates the original MSL1 envelope/CRC,
   writes the fixed MDC1 fields above, copies the compressed model, copies the
   original MSL1 rank body unchanged, copies the original MSL1 CRC unchanged,
   then calculates the MDC1 outer CRC.
4. `unpack FRAME DECOMPRESSED_MODEL BASE_OUT` validates MDC1 framing/outer CRC,
   requires a decompressed model whose byte length equals the stored original
   model length, reconstructs MSL1 from the copied header, supplied model,
   copied rank body, and copied inner CRC, then validates that reconstructed
   MSL1 envelope/inner CRC.

Neither `pack` nor `unpack` recomputes the MSL1 inner CRC. This is required for
the control to demonstrate that the rank and original base framing survived
unchanged. It also means MDC1 framing validation alone is insufficient to
establish MSL1 semantics.

## Required semantic validation

For each completed control archive, the experiment must perform this exact
round trip:

```text
MSL1 base archive
  -> native model extraction
  -> named external compressor
  -> native MDC1 pack
  -> native MDC1 unpack after named external decompressor
  -> fresh archive-only MSL1 decoder process
  -> restored bytes and SHA-256 comparison with the original source
```

The final MSL1 decoder must be a fresh process given only the reconstructed
archive and output path. It must execute the normal MSL1 parser and model
semantics, including model-kind parsing, exact local member reconstruction,
rank-width/range checks, and output reconstruction. The MDC1 helper's
`base_model` preflight intentionally checks only the MSL1 magic/version, inner
CRC, model length, and fixed resource limits; it is not a replacement for that
semantic decode.

The retained result should include the two codec commands and versions, source,
base, extracted-model, compressed-model, MDC1, decompressed-model,
reconstructed-MSL1, and restored-output hashes. A successful fresh-decoder
record is the evidence that the external codec output, native framing, and
MSL1 semantics agree.

## Bounds and malformed-input behavior

All helper file reads use `Read::take(40_001)` and reject input above 40,000
bytes. This applies to base MSL1 archives, MDC1 frames, and supplied model
files. The helper checks the original uncompressed MSL1 model length against
21,000 bytes; `unpack` also rejects a decompressed model exceeding that bound
or differing from the stored original length. The final reconstructed MSL1
archive is capped at 40,000 bytes before its inner envelope/CRC preflight.

MDC1 parsing checks the 31-byte minimum, magic, version, codec ID, copied MSL1
magic/version, outer CRC, compressed-model offset, and the exact stored
compressed model slice. It accepts the remainder before the outer CRC as the
copied rank body because rank length depends on full MSL1 model semantics.
That remainder is subsequently checked by the required fresh MSL1 decoder.

The external runner must reject an unexpected codec ID, decompression failure,
oversized decompressed output, or any byte-count mismatch before invoking
`unpack`. It must also treat a failed fresh MSL1 decode or source hash mismatch
as a failed archive, never as a size-only candidate.

## Review conclusion

The source implements the intended MDC1 accounting: fixed metadata, compressed
model, original rank, copied original CRC, and charged outer CRC are all
physical bytes. Its narrow preflight is appropriate only with the mandatory
fresh archive-only MSL1 semantic decoder after reconstruction. No production
integration or native replacement for `zstd`/`bzip2` is implied by this
control.
