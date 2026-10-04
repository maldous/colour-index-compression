# Native compatibility vectors

These tiny generated fixtures exercise fixed-field graph residuals and object
address relations. They contain no evaluation-dataset bytes.

The graph input includes one canonical atom record and literal unsupported
records. Six historical frames cover prediction modes 0–2 and representations
0–1. The pointer input contains a constructed object with two relocated fields;
six historical frames cover pointer-delta modes 0–5. Tests compare complete
encoded bytes and decode independently generated reference frames.

The reference generator and SHA-256 provenance are retained privately under
`docs/research/2026-10-04-native-rc/make_port_vectors.py` and `port-vectors.json`.
The checked-in bytes make the Rust tests self-contained; Python is not needed
to build or run CIX or these tests.
