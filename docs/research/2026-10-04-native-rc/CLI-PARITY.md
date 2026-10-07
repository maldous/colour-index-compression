# CLI parity contract

Reference: `rust/cix-native/src/cli.rs`, native manuals, and
`runtime/cix_runtime/cli.py`. The future one-executable RC has a hard
native/no-Python runtime gate.

| Contract | Native reference | Python reference | RC acceptance |
| --- | --- | --- | --- |
| commands | `cix`, `uncix`, `cixcat` | launcher program name | one native executable dispatches all three without shell/Python |
| stream/file | stdin/stdout, named file | native delegation above 128 MiB | read once, preserve input, atomic output, large archive support |
| decode inspect | `uncix -t`, `-l` | absent | exact test/list semantics |
| overwrite/keep | `-f`, `-k` | `-f`; no `-k` | explicit preserve/overwrite compatibility |
| effort/level | `--fast`, default, `--best`, numeric levels | fast/default/best only | documented level compatibility |
| output | `-c`, `-o`/`--output`, output-format semantics | `-c`, `-o` | exact output/atomic/multifile behavior |
| resources | memory, threads, parallelism | memory, threads 1..4, max-output | bounded resource behavior without Linux-only Python RLIMIT |
| advanced | format, route, backend, block/history, stream/flush, profile, portfolio/external | absent | either implement or reject with documented stable error before RC |

No parity is inferred from route names. Acceptance requires native command and
manual tests for empty, stdin, large input/archive, multi-file, overwrite,
listing/testing, malformed input, and every retained archive identifier.
