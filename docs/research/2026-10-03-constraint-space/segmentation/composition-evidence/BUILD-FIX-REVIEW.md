# SMC1 build-fix-1 review

Date: 2026-10-04. This is a static review of the compile-only repair. No build,
transform, codec process, input extraction, archive or benchmark was run by the
reviewer.

## Bound identities and decision

| Artifact | SHA-256 | Decision |
|---|---|---|
| preserved failed source | `2e785367f9dbea9fb94f6b6aeea4885da4cdac89f9008a222302cecd5aef72c0` | first controlled build failed before any input or archive existed |
| build-fix-1 source | `6bfe34a88e8622281a95e0a67830826f5c7cb6cbca4ab9ad6f066a706c39e2ce` | suitable for the resumed bounded controlled build and qualification |
| immutable preflight review | `f1fe9c0c3ef4d4fe8d3e8d00a1c8e91124a415f632378a8efa4fe811851cce57` | remains the semantic and wire-format review of the preserved source |

The replacement experiment identity is
`composition-m6-citytemp-v1-buildfix1`. Its `freeze.json` binds the current
source hash above. This review extends the immutable preflight review only to
the three compile repairs below; it does not rewrite that frozen evidence.

## Exact repair review

The failed and current source differ in exactly three places:

1. `Read::by_ref(&mut f)` disambiguates the intended `Read` trait method;
2. `try_fold` sums preceding decoded lane lengths and propagates `count`
   failures, producing the intended lane start; and
3. the unused `c_int` import is removed.

The first scheduled build reported the ambiguous `f.by_ref()` call and the
impossible `collect::<Result<usize, _>>()` over per-lane lengths. The repaired
fold implements the intended sum. That sum cannot exceed the admitted source
length of 4,096 bytes, so its plain `usize` addition cannot overflow under the
existing source and geometry guards.

These edits do not alter the wire format, transform, candidate family, route
choice, backend configuration, bounds or accounting. No new correctness or
resource blocker is present in the repair. This is approval to resume the
already bounded build and qualification; it is not evidence that either
passed.
