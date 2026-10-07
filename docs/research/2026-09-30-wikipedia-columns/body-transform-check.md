# Strict body-line transform check

This records a physical, self-contained reversible-transform check for
`benchmarks/hutter_wikipedia_body_lines.py`, SHA-256
`385236e51027e50d47e62f6154e496aeb57295c050a54d7aa137d0cd0fc6d57b`.
It is **not** a compression result: PAQ and every other backend were not run,
and no archive-size difference here may be interpreted as a compression gain.

The run used only the declared 4 MiB development regions of canonical local
`enwik9`, with affinity to CPU 18 and a 30-second budget. Each row is a fresh
encode followed by a frame-only decode. The input and decoded SHA-256 values
match exactly.

| Offset | Input SHA-256 | Frame bytes | Families / members | Selected source bytes | Encode + decode seconds |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | `5ba647fec2ba51b0383cbe7147e15a478d85613245b7131c41764dbdd5062f77` | 4,189,418 | 23 / 210 | 14,242 | 0.131085 |
| 100,000,000 | `fd30602741222df957545a821556c8428bb8c3e4ed45634367ae8470d901c6ec` | 4,152,657 | 320 / 2,190 | 161,285 | 0.197182 |
| 400,000,000 | `a07035d4de761fc30cee70f4528156e8128abf7430222cfd63c2311168ea7f17` | 4,114,833 | 29 / 679 | 122,377 | 0.144653 |

| Offset | Rules | Dictionary | Descriptor | Framing | Component sum | Literal payload | Hole payload |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 111 | 1,165 | 4,188,133 | 9 | 4,189,418 | 4,180,062 | 6,708 |
| 100,000,000 | 111 | 13,935 | 4,138,602 | 9 | 4,152,657 | 4,033,019 | 87,422 |
| 400,000,000 | 111 | 3,879 | 4,110,834 | 9 | 4,114,833 | 4,071,927 | 31,125 |

The four physical components sum exactly to each frame. Rules are embedded;
the dictionary is global per input and first-seen deterministic; descriptors
carry each selected member in original order; literal payload retains every
unselected byte; and hole payload retains every original link, URL and number
substitution. The selected policy admits only complete `<text...>...</text>`
bodies, newline-terminated lines whose core is 48–512 bytes, at least 24
literal bytes per skeleton, at least three members across two bodies, and at
least two distinct raw lines. Incomplete bodies and all unsupported material
remain literal.

The machine-readable raw evidence, including exact decoded hashes and every
accounting field, is in
[`body-transform-check.json`](body-transform-check.json). This check did not
read 600M/900M holdouts, run full `enwik9`, or establish Hutter eligibility.
