# CIX spatial-image bridge

This CIX-owned bridge exposes lossless single-component JPEG-LS (CharLS 2.4.2)
and reversible JPEG 2000 (OpenJPEG 2.5.0) for legacy CIXI1 spatial payloads.
It accepts only canonical little-endian u16 samples and validates paid width,
height, unsigned precision, one component, and no subsampling before CIX gives
it an output buffer. JPEG-LS uses NEAR=0 and non-interleaved grayscale; JPEG
2000 uses a reversible transform and one lossless layer. JPEG-LS accepts
precision 2–16; one-bit JPEG-LS is explicitly unsupported because CharLS has
no faithful one-bit frame representation for this canonical u16 contract.

Configure only against the receipt-backed SDK prefix:

```sh
cmake -S rust/cix-native/codecs/spatial -B <build> \
  -DCIX_SPATIAL_ROOT=/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/codec-sdk-v1/prefix
```

`SpatialProvider` loads an explicitly supplied absolute package bridge path,
requires CharLS 2.4.2 and OpenJPEG 2.5.0, and does no host-library or Python
fallback. Decode admission charges retained input, sixteen times the CIX output
size for codec-side working state, and a 64 MiB bridge-working estimate before
allocating; encode uses the corresponding sixteen-times-input working estimate
plus both simultaneously live native/Rust output copies. These are conservative
CIX-side estimates, not a hard RSS limit for CharLS or OpenJPEG internals.

The bridges reject a valid member followed by trailing bytes before Rust
allocates its decode output. Their bounded structural scans account for the
entropy byte-stuffing rules: [CharLS 2.4.2 decoder strategy]
(https://raw.githubusercontent.com/team-charls/charls/2.4.2/src/decoder_strategy.h)
treats an `FF` followed by any byte below `80` as JPEG-LS entropy data, and
[OpenJPEG's MQ input logic](https://www.openjpeg.org/doxygen/mqc__inl_8h_source.html)
treats `FF 00` through `FF 8F` as JPEG 2000 packet data. JPEG 2000 tile parts
use declared `Psot` bounds; the scan also skips legal SOP and EPH packet
markers and all length-delimited header payloads before accepting the terminal
EOC.
