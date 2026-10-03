# SMC1 composition wrapper format

`representation_m6_wrapper` is a bounded experiment wrapper. It accepts only
nonempty regular files of at most 4,096 bytes and writes an archive of at most
32,768 bytes. It has no filename, corpus, floating-point, format-detection, or
backend-selection policy.

## Header

All multi-byte fields are little endian. The fixed header is **25 bytes**;
the complete header is `25 + width` bytes.

| bytes | field |
| --- | --- |
| 4 | `SMC1` |
| 1 | version `1` |
| 1 | backend: `0` CIXM6, `1` Zstandard, `2` native lane proxy |
| 4 | source byte length `n` |
| 4 | transformed byte length (always `n`) |
| 4 | reflected IEEE CRC-32 of restored source bytes |
| 1 | width `w` |
| 1 | phase `p` |
| 1 | operator count (exactly `w`) |
| `w` | paid operator vector |
| 4 | payload length |
| payload length | complete backend payload/body |

There are no uncharged fields. Every geometry value, operation, route, and
payload length is stored in the archive.

## Geometry and transform

`1 <= w <= 8`, `0 <= p < w`, `p <= n`, and `w <= n-p`; these constraints make
each lane nonempty. Operators are `0` identity, `1` subtract original previous
row, `2` subtract original previous column, `3` XOR original previous column,
and `4` XOR original previous row. Lane zero must use operator `0`. Every
lane's first suffix row is literal regardless of its operator.

`T` begins with `source[0..p]`, then contains lane 0 through lane `w-1`; lane
`j` contains source positions `p+j+row*w`. Prediction reads original row-major
bytes. Partial final lanes follow from this position rule. The prefix lives
inside the compressed backend payload and is never duplicated outside it.

## Backends

`pack --backend m6` performs a complete bounded structural preflight:
canonical CIXM6 history varint no greater than 1 MiB, bounded frame varints and
recognized modes `0..20`, payload length at most `8*source_length+4096`,
cumulative frame source exactly `n`, footer marker `255`, footer
length exactly `n`, footer CRC-32 equal to `T`, and exact EOF. Decode repeats
framing checks before executing the caller-supplied sealed absolute CIX binary
with `-d --threads 1 --memory 1536MiB -c`. Its stdin is streamed in bounded
chunks; stdout is limited to `n+1` bytes and overrun/error kills and waits for
the child. The benchmark pins the frozen CIX executable separately.

`pack --backend zstd` and decode require exactly one Zstandard frame. Native
Zstandard frame header parsing requires content size `n` and a window no larger
than 4,096 before bounded decompression. Packing also verifies that decoded
Zstandard bytes equal `T`.

`native` writes backend `2`, a separate proxy body: raw prefix `p`, followed by
one lane record each: route byte, decoded lane length (`u32`), encoded length
(`u32`), and payload. Route IDs are raw, public Huffman, public adaptive
order-0 (`bits=8`, model limit 1), and public legacy LZ (effort 1). It chooses
the smallest payload with route ID as tie-break. Decode prevalidates lengths;
Huffman's embedded length, adaptive model limit, and legacy LZ context bound
are all fixed. This proxy must be reported as `native`, never as Zstandard.

```
transform --width W --phase P --ops csv SOURCE OUT
pack --backend m6|zstd --width W --phase P --ops csv SOURCE PAYLOAD OUT
decode --cix ABS_SEALED_CIX ARC OUT
native --width W --phase P --ops csv SOURCE OUT
```
