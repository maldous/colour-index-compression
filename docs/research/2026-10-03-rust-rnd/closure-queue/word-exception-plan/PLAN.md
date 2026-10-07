# R2 word dictionary and exception closure

Prepared and unexecuted. `WEC2` is a buffered experimental wrapper derived
from the hardened WPV2 archive-only path. It does not change a production CIX
format or selector.

For each existing deterministic strong, weak and absent 8 KiB control, run
the matched full-frame native identity once for widths 2 and 4, then palette
variants with input-derived dictionary cardinality 8 and 16. The dictionary
is deterministic: descending frequency, then unsigned little-endian word
value. Each word is a five-bit index or the escape code followed by its raw
word. The frame stores width, dictionary count, word/index/exception/tail
lengths, dictionary words, indices, raw escapes, backend tag, source/payload
lengths and CRC. All bytes are reconstructible from the archive alone.

Every representation is passed to the same frozen CIXG1 fast backend; raw
fallback is fully framed and retained. Report representation, dictionary,
exception, nested archive, complete native and raw bytes separately. A fresh
native decode and a fresh WEC2 archive-only process must restore exact bytes.
One encode/decode per configuration, no averages. Root leases one CPU, 768 MiB
RAM, no swap, 2 MiB retained temporary disk and 180 seconds per native child.

Promotion requires a complete framed WEC2 win over its matched identity and
exact restoration. A WEC2 result alone is not a production-format win.
