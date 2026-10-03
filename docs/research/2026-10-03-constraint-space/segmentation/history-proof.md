# Decoded-prefix history: exactness proof and control boundary

Status: theory and control specification only, 2026-10-03. This document does
not report a build, run, or compression result. Shared decoded-prefix history
is standard compressor state; no theoretical novelty is claimed.

## Conclusion

A retained history window does **not** by itself make segmentation cost path
dependent. For the proposed `H = 1024` control, the last `H` original bytes at
source position `i` are determined by the source prefix `x[0..i)`. If every
route reconstructs exactly the same segment bytes, the outer encoder and
decoder update history from those reconstructed bytes, and no other state
crosses the boundary, then every path reaching `i` has the same history.

Under those conditions, raw, Huffman, reset-per-segment adaptive coding, and
legacy LZ form path-independent edges. Legacy LZ may read the last 1,024 source
bytes, but its choice in an earlier segment cannot alter those bytes. The exact
position/segment-count dynamic program remains valid.

This proof does not cover a selected-template cache, recent-block queue, or
persistent adaptive model. Those can differ between two paths reaching the
same byte position and require explicit dynamic-program state unless a separate
source-only state equivalence is proved.

## 1. Frozen control

Let `x = x[0..n)` be the original byte string and fix

```text
H = 1024 bytes.
h(i) = x[max(0, i-H) .. i].
```

The declared route bank is:

| Route | Boundary behavior | Use of `h(i)` |
|---|---|---|
| raw | Copies `x[i..j)` verbatim. | Ignored for coding; reconstructed bytes still advance the outer history. |
| Huffman | Builds a complete self-contained Huffman payload for `x[i..j)`. | Ignored for coding; reconstructed bytes advance the outer history. |
| adaptive | Creates fresh adaptive tables for the segment. A causal context tail may be seeded from `h(i)`, but learned counts do not survive the segment. | Read-only seed, if the chosen frozen adaptive parameters use it. |
| legacy LZ | Parses `x[i..j)` with an immutable prefix dictionary equal to the last at most `H` original bytes. The parser may also match bytes already produced inside the segment. | Read-only prefix dictionary; no parser or substream state survives the segment. |

The current stage-2 control uses order-zero
`adaptive::encode_general(..., [], ...)`, so adaptive history is presently
irrelevant. Permitting a fixed higher-order adaptive candidate remains within
this proof only when its models are recreated per edge and `h(i)` is its sole
cross-boundary input.

The stage-2 executable deliberately reuses the qualified native raw, Huffman,
adaptive, and legacy-LZ implementations as matched controls. It materializes
all four routes for each admitted edge and records the least complete edge
cost, with route-ID tie breaking. This is not an independently reimplemented
route-codec oracle. Its independent exhaustive check enumerates partitions over
that shared measured minimum-edge matrix; it checks the segmentation DP and
accounting, while route correctness continues to rely on the frozen native
implementations and fresh archive round trips.

Every candidate evaluation must be pure with respect to shared state. It
receives immutable `x[i..j)` and `h(i)`, returns a complete payload, and
discards its local parser/models. After a selected segment decodes completely,
the outer layer appends the decoded original bytes to the history ring and
retains its last `H` bytes. Candidate trial order and the selected route must
not update that ring.

## 2. History invariant

Define the history update

```text
U_H(h, y) = suffix_H(h || y),
```

where `suffix_H` returns the final at most `H` bytes. For any `0 <= i < j <= n`,

```text
U_H(h(i), x[i..j)) = h(j).                    (1)
```

This follows because `h(i)` contains exactly the part of `x[0..i)` that can
remain in the final `H` bytes after appending `x[i..j)`. Older prefix bytes
cannot re-enter the window.

### Lemma 1: route-independent state

Assume each legal route decodes its segment to exactly `x[i..j)`, and the outer
state update is `U_H` applied once to those decoded bytes. Every legal encoded
path from position zero to position `j` ends in state `h(j)`.

**Proof.** At position zero the history is empty, which equals `h(0)`. Suppose
every path to `i` has history `h(i)`. Whichever legal route encodes the next
segment, exact decoding produces `x[i..j)`. Equation (1) makes the new state
`h(j)`. Induction over selected segments proves the claim. `QED`

The proof depends on original bytes, not compressed bytes. Huffman codewords,
adaptive intervals, LZ tokenization, route IDs, and candidate order cannot
affect future history.

### Lemma 2: edge cost is path independent

For route `r`, define

```text
E_r(i,j) = Encode_r(x[i..j), h(i))
c_r(i,j) = 9 + |E_r(i,j)| bytes.
```

The nine bytes are the frozen route ID, decoded length, and payload length.
By Lemma 1, all paths reaching `i` supply the same `h(i)`. With frozen route
parameters and deterministic tie behavior, `E_r(i,j)` and its physical length
therefore depend only on `(i,j,r)`. The best edge

```text
c(i,j) = min_r c_r(i,j)
```

is likewise path independent. A route-length tie is resolved by the frozen
numeric route ID; the tie rule affects canonical bytes, not the cost proof.

Legacy LZ remains in this lemma even though it consumes history. Its encoder
internally truncates the supplied prefix to its configured window; supplying
only `h(i)` therefore caps usable external history at `min(H, lz_window)`. Its
decoder receives the identical `h(i)` and rejects a distance beyond the
available prefix plus bytes already produced in the current segment.

## 3. Exact dynamic program

Let `p_0=0 < p_1 < ... < p_m=n` be a frozen boundary bank and let `K` be the
maximum segment count. Because `c(p_a,p_b)` is path independent, exact
selection is

```text
D[0,0] = 0
D[b,k] = min_{0 <= a < b} D[a,k-1] + c(p_a,p_b)
```

for `1 <= k <= K`. The selected complete size is

```text
19 + min_k D[m,k].                            (2)
```

The segment-count dimension is still required when `K` is a hard limit. A
cheaper prefix that already used `K` segments cannot dominate a more expensive
prefix with capacity left. On equal total bytes, the frozen policy may prefer
fewer segments and then the stable first predecessor, exactly as in the
independent control.

Theorem: this recurrence selects the smallest complete archive among the
declared boundary bank, four-route portfolio, `H=1024`, and segment limit.

**Proof.** Every legal archive ending at `p_b` with `k` segments has one final
edge `(p_a,p_b,r)`. By Lemma 2 its cost is independent of the earlier path.
Removing that edge leaves a legal `(k-1)`-segment prefix represented by
`D[a,k-1]`. Conversely, appending any legal edge to such a prefix is legal,
because Lemma 1 supplies the exact history required at `p_a`. Induction over
`k` and `b` establishes optimal substructure. Adding the common header once
gives (2). `QED`

The theorem is deliberately scoped. A content-derived boundary shortlist
certifies only that shortlist. An all-cut reference certifies all byte-aligned
partitions within its source and segment-count bounds. Neither establishes an
optimum over omitted routes or parameters.

## 4. Paid wire cost: 19 bytes versus 17

The existing independent NativeCSC1 research envelope pays a 17-byte global
header:

```text
magic 4 | version 1 | source length 4 | segment count 4 | source CRC-32 4
```

The history-aware NSCH control uses a distinct version and pays a two-byte
little-endian history-limit field, producing this actual 19-byte field order:

```text
magic 4 | version 1 | history limit 2 | source length 4 |
segment count 4 | source CRC-32 4
```

For the frozen control the field value is exactly 1024. Values above the
decoder's declared bound are rejected before allocation. Versioning is
mandatory: emitting the extra field under the old version would shift the
first segment and allow incompatible interpretations.

Complete physical accounting is therefore

```text
independent: 17 + sum_segments (9 + payload_bytes)
history:     19 + sum_segments (9 + payload_bytes).
```

No history bytes are serialized per segment. The decoder derives them from its
already reconstructed output. The history candidate must beat the independent
control after the common two-byte increment is included. Reporting only the
legacy-LZ payload saving would overstate its gain.

The source length, segment count, whole-source CRC, route ID, decoded length,
payload length, route-internal metadata, padding, and coder termination remain
paid. If any of these fields changes in the implementation, equation (2) must
be changed before evidence is generated.

## 5. Encoder, decoder, and budget obligations

### Encoder

- Obtain `h(i)` as a bounded immutable slice or ring snapshot. Candidate
  encoders must not mutate it.
- Materialize every member of the declared exact route bank for an edge; route
  scores are complete payload lengths rather than entropy estimates.
- Re-encode the selected edges or retain their exact payloads. If re-encoding,
  require byte determinism and verify that the measured and emitted lengths
  agree.
- Include the 19-byte header and every nine-byte segment record in the final
  comparison. Cache keys must include `(i,j,H,route,parameters)`.
- Keep the reference bounds explicit. With `m+1` boundary points and four
  routes, an all-edge reference evaluates `4*m*(m+1)/2` route trials. That is a
  small-reference cost, not a production streaming claim.

The proof removes history from the DP state; it does not remove history from
codec scratch memory. A cost-only edge matrix needs `O(m^2)` bounded integers
and the DP needs `O(mK)` costs/predecessors. Payload caching can be much larger;
re-encoding winners avoids retaining every payload. All codec scratch,
candidate payloads, source/boundary storage, the 1,024-byte ring, and queued
work must be charged to the experiment memory cap.

### Decoder

- Read and validate the version, 19-byte header, `H=1024`, source length,
  segment count, route, decoded length, and payload length before allocating or
  slicing.
- Decode a segment against the current immutable history. Do not commit partial
  output to shared history after a route error.
- Require exact route payload consumption and exact decoded length, then append
  the complete decoded segment to the rolling source CRC and history ring.
- For legacy LZ, reject zero or unavailable distances, decoded-length overflow,
  trailing substreams, and references older than the available `h(i)` plus
  current-segment output.
- At EOF, require exact archive consumption, exact total source length and
  segment count, and the whole-source CRC.

For a maximum decoded segment size `B` and maximum admitted payload `P`, a
straightforward streaming decoder uses `O(H+B+P)` bytes plus bounded
route-specific tables. The exact implementation must state those constants;
the path-independence theorem is not by itself a memory qualification.

## 6. State that does require a larger DP

### Paid template or block cache

Suppose a selected segment may install a paid template or complete block in a
cache, and later edges may reference it. Two paths can reconstruct the same
`x[0..i)` while installing different entries or eviction order. A future
payload can then have different cost at the same position:

```text
c(i,j, cache_A) != c(i,j, cache_B).
```

The exact recurrence must carry the full future-relevant cache state, including
identity/order and any paid availability metadata. A cache hash is only an
index unless collisions are resolved by exact equality. If a cache is instead
rebuilt canonically from `h(i)` alone, it can collapse to position state, but
that source-only equivalence and all reconstruction costs must be proved.

### Persistent adaptive state

Persistent counts are not covered merely because every selected route observes
the reconstructed bytes. Boundary-sensitive rescaling, aging, reset, model
selection, or admission can produce different count tables at the same source
position. The current native persistent model is a concrete example: its
`observe` operation accumulates a complete block and then halves each touched
bucket when its total exceeds the state limit. Different segment boundaries can
therefore change the timing and number of halvings even for identical original
bytes.

Such a candidate needs state like

```text
D[position, segment_count, model_counts, cache, ...]
```

or must be explicitly reset on every edge. A persistent model could collapse
to source position only after proving that initialization and every update,
rescale, and eviction are a deterministic symbol-by-symbol function of
`x[0..i)` independent of route and segmentation. The history invariant alone
does not prove that stronger property.

### Boundary-defined objects

A recent-block reference queue also remains path dependent even when it stores
original bytes. Different partitions turn the same prefix into different
block objects. Storing only the last 1,024 flat bytes does not identify which
substrings are legal reference objects or their IDs.

## 7. Evidence boundary and further hardening

### Current bounded protocol

The present evidence claim is narrower than exhaustive route-assignment
enumeration:

1. The independent stage-2 oracle enumerates every admitted partition over a
   shared edge matrix whose cell is the measured minimum of the four reused
   native route implementations. Because Lemma 2 makes route minimization local
   to an edge, minimizing routes first and then enumerating partitions is exact
   for that matrix. The partition enumerator is independent of the DP; the
   route codecs are shared controls rather than an independent codec oracle.
2. The revised history screen has 16 `H=0` compatibility and dependency probes
   across the frozen medium cases. Each admitted result is required to restore
   exactly in the fresh decoder; an encode/decode failure remains a recorded
   failure and cannot become a selected success.
3. The stage-4 exactness statement is limited to the runtime-bounded protocol:
   its frozen boundary bank, completed route trials, `H` values, segment cap,
   framing, and deterministic tie rules. A route trial excluded or failed under
   the runtime/resource bound is an omission, not proof that the route loses.
4. The 17-byte `H=0` and 19-byte `H=1024` envelopes must report payload,
   segment metadata, and header separately. Fresh decoding must verify exact
   original bytes, source length, full archive consumption, and CRC.

### Proposed future hardening

The following controls are useful additions, but are not claims about the
current checkpoint and are not mandatory prerequisites for freezing it:

- Independently enumerate both partition and route assignment on very small
  cases, instead of consuming the shared four-route minimum-edge matrix.
- Construct dedicated external-prefix legacy-LZ fixtures with a useful match
  at exactly 1,024 bytes and a deliberately unavailable match at 1,025 bytes.
- Expand malformed coverage for unsupported history limits, unavailable LZ
  distances, truncation, trailing bytes, contradictory lengths, and CRC
  failure.
- Record peak memory including route scratch and cached or re-emitted edge
  payloads. Do not infer production streaming bounds from a whole-input small
  oracle.

## Source boundary

This proof is grounded in the current native APIs without changing them:

- [`adaptive.rs`](../../../../rust/cix-native/src/adaptive.rs) creates fresh
  general adaptive model tables per call and uses prefix history only for its
  initial context tail.
- [`legacy_lz.rs`](../../../../rust/cix-native/src/legacy_lz.rs) truncates the
  supplied prefix to the configured window, parses against prefix plus current
  data, and checks decoder match distances against prefix plus produced output.
- [`stateful.rs`](../../../../rust/cix-native/src/stateful.rs) illustrates the
  excluded case: persistent counts survive calls and rescaling occurs after a
  complete observed block.
- [`segmentation_reference.rs`](../../../../rust/cix-native/experiments/constraint-space/segmentation_reference.rs)
  defines the existing 17-byte, no-shared-state control and its exact
  position/segment-count recurrence.

No production format, selector, route, or archive was modified for this proof.
