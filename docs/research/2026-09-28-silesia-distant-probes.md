# Eight-MiB history diagnostic

The same 12 fixed Silesia midpoint blocks were tested at 1 MiB and 8 MiB history
limits. All 24 candidate payloads decoded exactly; the native parser's 1 MiB
physical sizes also match the previous Python-parser trial on all 12 probes.

Exact block selection totals change from 62,484 to 62,313 bytes: only 171 extra
bytes saved. Prior history and full stream headers are excluded, so these are
conditional diagnostics, not corpus totals or ranks. This does not justify
prioritizing an expensive full 8 MiB experiment over stronger modelling work.
No filenames, formats, corpus identity or ISA features drive selection.
