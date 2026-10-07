# Projected matrix pipeline audit

## Selected existing path

Use the existing **`benchmarks.volume_image_codec` CIXV1 mode 5** path with
lossless JPEG XL at effort 9. It is the frozen choice because it is already
decoded by `benchmarks.competitive_codec.decode`, has a self-contained frame,
and models local matrix relationships rather than only a global composition.

The fixed invocation is conceptually:

```python
frame = volume_image_codec.encode(
    source_bytes,
    region={"offset": 0, "length": 2 * z * h * w,
            "slice_height": h, "width": w},
    mode=5,
    effort=9,
)
```

The fixed adapter maps each projected byte value to one little-endian `uint16`
sample of the same value; it does not pair-pack adjacent bytes. It sets `z=1`,
`width=256`, and `height=ceil(projected_bytes/256)`, then appends zero samples
to complete the final row. The outer projection frame records the original
projected-byte length and the complete CIXV1 frame. Those length bytes and
zero padding are paid representation bytes; decoding crops widened samples to
that recorded length before converting each sample back to one byte. The
adapter must reject any decoded sample above 255 and any extent whose length is
not exactly `2*z*h*w`. It must not infer a layout from a filename, magic, or
corpus identity.

Mode 5 applies reversible first differences over axes 0, 1 and 2, followed by
zig-zag mapping and lossless JXL. Decoding reverses cumulative sums in the
opposite order. Thus the model retains adjacent-row and adjacent-column
relationships (and adjacent slices when `z > 1`); it is not a
permutation-invariant histogram or global-composition codec.

## Fixed experiment policy

| Item | Frozen choice |
|---|---|
| Implementation | `benchmarks.volume_image_codec` |
| Outer framing | projection adapter version + original projected-byte length + complete `CIXV\x01` frame; inner CIXV1 records mode 5, declared widened extent/dimensions, metadata and payload lengths, CRC32 |
| Transform/reset | mode-5 local differences; each frame starts from zero boundary state as implemented; no state or dictionary crosses frames |
| Backend | `imagecodecs.jpegxl_encode(..., lossless=True, effort=9, numthreads=1, photometric='GRAY')` |
| Selection | none: mode 5 is emitted unconditionally for this trial; raw bytes are a separate matched control |
| PAQ fallback | none; PAQ is neither invoked nor silently selected |
| Verification | independent `volume_image_codec.decode(frame)` with only the frame, exact source SHA-256 comparison |

The codec's frame exposes the actual coding path: magic `CIXV\x01`, mode 5,
all dimensional fields, metadata size and image payload size are decoded and
validated before JXL reconstruction. A harness should record frame SHA-256,
total bytes, the parsed mode, metadata bytes, JXL payload bytes, and decoder
SHA-256. It should not label a result as a PAQ result or as portfolio-selected:
the ordinary portfolio evaluates several volume modes by complete physical
size, while this proposal deliberately fixes one mode to test its local
prediction mechanism.

## Resource envelope

`volume_image_codec` requests one JXL thread. Pin each trial to one physical
CPU. Under the requested shared ceiling, schedule at most four independent
trials, each with `MemoryMax=3,000,000,000` bytes, `MemorySwapMax=0`,
`TemporaryMax=1,000,000,000` bytes, and a 300-second wall limit; this gives a
4-CPU / 12,000,000,000-byte RAM / 4,000,000,000-byte temporary-storage
aggregate envelope. Do not claim that the single-thread JXL backend uses all
four CPUs.

## Rejected audited paths

`spatial_image_codec.encode_region` can accept an explicit region and is not
being rejected as incapable of this work. It is simply not selected: freezing
one backend path avoids a selector tournament in this experiment.
`oriented_image_codec` and its surrounding probe are tied to the prior x-ray
workflow. `multiscale_volume` has useful interpolation but is not wired into
the ordinary competitive codec selector; it would require a separate
integration decision. `cix.bitplanes` records per-plane global counts and
enumerates arrangements, so by itself it does not preserve the local neighbour
relationship this experiment is meant to test.

This audit makes no size or speed prediction. A result is promotable only after
the fixed raw control and CIXV1 mode-5 frame both complete exact independent
decode under the same explicit dimensions and resource policy.
