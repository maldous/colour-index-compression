# Direct CIXB1 source buffering

The direct external wrapper now grows a capped source buffer instead of
reserving 128 MiB before reading. This change affects only explicit
`--external` encoding, which retains its existing named-input requirement.
It does not change the normal selector or provide streaming for CIXB1.

Reading occurs before codec/model/output allocation. The allowance is
`min(128 MiB, (memory - 64 KiB) / 2)`; the two capacity reservations cover
overlapping old/new allocations during growth and the fixed stack chunk.
Budgets below 64 KiB reject. Actual capacity is charged to the existing
post-read codec admission. This is requested Vec capacity accounting,
not a proof about allocator-wide RSS. The format still caps input at 128 MiB.
A large source may reject sooner under a low budget; this is intentional
conservative resource admission. No codec, profile or archive format changed.

## Actual local verification

`raw/tests3.log` passed six reader tests and one CLI test covering six
complete archive cases: empty, 2,160-byte and 65,537-byte inputs through gzip
and bzip2 at 64 MiB. All match canonical complete archives; fresh CLI
decoders restore exactly and truncated archives exit 2. Complete sizes and
input/archive SHA-256 values are in that log. Reader checks include partial
reads, interrupted reads, injected errors, growth boundaries and overflow.

Actual runner readbacks were CPU/cpuset 8, 1 GiB memory and zero swap.
The reported peak includes compilation and is not per-codec memory.
The source assembly and binary hashes are retained; a final combined release
validation remains required. `tests.log` retains the first failed test setup:
it attempted an unsupported stdin external wrapper; `tests2.log` and the
final hashed run use named files. This was not a compression mismatch.

No throughput, RSS or production profile improvement is inferred from these
checks. Reader-only DHAT allocation measurements are recorded separately.
