# Mixed-region implementation: CIXH1

`CIXH1` is a complete, self-identifying candidate for heterogeneous inputs. It
is returned beside whole-input candidates, so its archive bytes compete with
the whole-input portfolio rather than receiving a preference.

The splitter uses only the supplied bytes. It has bounded scanners for canonical
SDF V2000 members, the retained WCSTools seven-int/28-byte layout, implicit-VR
DICOM pixel ranges with validated dimensions, and ELF files with table and
load-segment extents. Each known span may be arbitrarily larger than 64 KiB;
only unknown gaps are cut into 64 KiB generic regions. The regions are
contiguous and cover every input byte once, so a late recognised span preserves
its opaque prefix and suffix as separate generic regions. This is a finite
scanner set, not a claim to recognise every format or arbitrary nested syntax.

Each region pays a backend ID, uncompressed and payload lengths, parameter
bytes, and a SHA-256 checksum. The outer frame also pays the original size,
region count, and complete-input checksum. Region alternatives are raw, zlib
level 6, lzma preset 3, plus at most eight complete specialised frames from the
bounded specialist registry. Nested candidates must declare one thread and no
more than 5 GiB. The selector admits families round-robin before extra variants,
so a geometry variant cannot mechanically prevent the chemical hydrogen or
volume family from competing. The enclosing worker's 12-hour candidate timeout
bounds the whole local contest. `encode_with_report` retains selection,
omission, and paid-choice evidence. Registry omission or failure never loses
coverage because raw always remains available.

The CIXH1 catalogue accepts `fast`, `default`, and `best` profiles. `fast`
keeps only raw/zlib/lzma regional choices; `default` retains bounded non-PAQ
specialists; `best` admits the complete stated specialist budget. The format is
unchanged across profiles because every selected backend is paid in its frame.

The decoder verifies all declared bounds, frame lengths, every region checksum,
total length, and the complete checksum. Nested specialist decoding receives the
exact region output cap and the caller's memory budget. Inputs are handled as
bytes, which preserves numeric lexical forms including `NaN` spelling and
negative zero without claiming a semantic numeric transform.

The deterministic tests cover opaque text with late SDF, DICOM, WCSTools, and
ELF spans, plus malformed archives. They also show that a
whole-input zlib candidate can legitimately beat CIXH1 once its framing is
paid. These tests establish consideration and reversibility; they do not claim
universal semantic detection or a specialist win.
