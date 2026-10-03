# Finite R&D closure queue: method and evidence coverage

Status: audit only; no acquisition, build, benchmark, or production change is
authorized by this document. It is a closure queue for the existing private
evidence, not a claim that source presence proves compression quality.

The primary Squash table in
[`coverage-matrix.md`](../../2026-10-01-cix-optimization/coverage-matrix.md)
contains 29 requested plugin/codec rows. Its own supplementary inventory adds
Doboz and zling, while its method-principles audit splits several rows into raw
and framed forms. This audit enumerates the actual names and their distinct
principles; it does not claim a count of 30. Parsers, dictionaries, predictors,
transforms, entropy coders, framing and resource choices remain distinct even
when a plugin shares an LZ label.

An **absent**, **partial**, **backend-only**, or **unqualified** row is open,
not closed. Packaging may close it only after its listed bounded controlled
test is completed or root records an explicit scope/resource blocker. The
blocker must name why the smallest test cannot be run under the frozen source,
available local tools, 4-core/12-GB/4-GB/no-swap envelope, and no-acquisition
rule. Source presence is never a closure outcome.

## Squash and supplementary method coverage

| Principle family and named Squash methods | Existing state | Evidence | Smallest missing local experiment |
|---|---|---|---|
| Raw storage: copy | Tested/implemented | `coverage-matrix.md` raw-route row; constrained complete-archive oracle in `experiment-queue.md` row 36. | None for mechanism; retain raw in each matched control. |
| Generic LZ parser family: BriefLZ, Crush, FastLZ, Gipfeli, LZ4/LZ4F, LZF, LZG, LZJB, LZO variants, Pithy, QuickLZ, Snappy/framed, wfLZ/chunked, YALZ77, Doboz, zling | Partial or absent; no codec-wire equivalence claimed. Gipfeli buffered diagnostic is explicitly not deployed. | `coverage-matrix.md` rows for each; `six-capability-audit.md` capabilities 5/6; `coverage-matrix.md` resolved-method update notes CIX's bounded hash-chain grammar. | One ≤64 KiB generated repeat/distance fixture, held CIX LZ token grammar and coder fixed, compare current bounded hash-chain against one lazy parse. Archive and fresh decode once each. This tests a parser principle, not 16 library clones. |
| BWT family: BSC and bzip2 | Partial native BWT/MTF/zero runs; bzip2 is separately backend-only. | `method-principles.md` BWT and bzip2 rows; `six-capability-audit.md` capability 2. | One ≤64 KiB BWT→MTF control with current local streams versus a paid run/literal split; same CIX coder and primary index. Stop if exact restore fails. |
| Dictionary/filter family: Brotli static dictionary; CSC filters; Density double dictionaries; LZMA dictionaries/filters; Zstd dictionaries | Brotli/XZ/Zstd are backend-only; CSC absent; Density partial components only. No filename/type filter is generic policy. | `coverage-matrix.md` rows; `method-principles.md` dictionaries and generic-policy guardrails. | One synthetic byte fixture with a serialized input-derived 16-entry word dictionary and literal escapes versus raw identity, under one fixed native backend. No static corpus dictionary, filter classifier, or source identity dispatch. |
| LZW: ncompress | Absent and **open**. | `coverage-matrix.md` ncompress row. | Implement one bounded resettable LZW experiment behind an experimental frame; use one ≤16 KiB generated dictionary-reset fixture, raw control, complete bytes and fresh decode. If that implementation exceeds the remaining closure budget, root must record that explicit scope blocker. |
| Arithmetic/context coupling: FARI and LZHAM | Partial components only; CIX has independent range coding but not their coupled parser/model. | `method-principles.md` adaptive-range and LZHAM rows; `coverage-matrix.md` entropy-coding gap. | One existing frozen literal stream coded once by current adaptive range and once by count-range, with identical stream bytes and paid headers. Do not infer FARI/LZHAM compatibility. |
| Microsoft methods: LZNT1, XPRESS, XPRESS-Huffman | Partial concepts only and **open**. | `coverage-matrix.md` MS-compress row. | Test one distinctive method, XPRESS-Huffman: implement a bounded experimental token/table frame on one ≤16 KiB synthetic token fixture, then compare raw and canonical-Huffman control. If no local implementation is accepted, root must record a scope blocker for this new wire family. |
| DEFLATE family: zlib and zlib-ng | Raw DEFLATE is native inner coding; gzip/zlib wrappers are CIXB1 only; zlib-ng itself is absent. | `coverage-matrix.md` rows; generic `FORMAT.md` coder ID 3. | One existing 16 KiB frozen stream: materialize current raw-DEFLATE inner payload and compare its complete CIX framing to raw. No zlib-ng speed claim or binary substitution. |
| External complete backends: Brotli, bzip2, XZ/LZMA, Zstd | Backend-only, with version/settings boundary already recorded. | `rust/cix-native/README.md`; `FORMAT-CIXB1.md`; `method-principles.md` deliberate non-equivalences. | No new backend trial before package closure. The smallest valid work is evidence read-back of existing exact binary/settings and archive-only decode receipts. |
| ZPAQ 7.05/7.15 method 5 | Controlled comparison complete. Direct raw streams matched exactly at 2,142,935 B; wrapping the frozen CIXG1 archive expanded it by 431 B and was exactly decoded. Neither result is a native CIX model gain. | `results.md`, “ZPAQ lead reproduction” and “ZPAQ on a frozen Rust representation”; `zpaq-dickens-v1/PLAN.md`. | One matched reversible-representation cell only if closure requires it: fixed raw vs one already-stored native representation through pinned ZPAQ 7.15 method 5; charge representation metadata and both decode steps. |
| PAQ8px / PAQ v216 inventory | Unqualified external comparator, not a native route. Size profile `-12L` is resource-limited under the shared 12 GB cap. | `coverage-matrix.md` supplementary rows; `docs/research/2026-09-30-codec-profiles/blocked.json`. | Explicit resource blocker already exists for `-12L`; no lower-preset substitution is permitted. This blocks that declared setting, rather than closing its method. |

## Native versus backend evidence

| Claim boundary | Evidence state | Closure action |
|---|---|---|
| Native CIXG1 mechanisms | Exact rank, raw, RLE, DEFLATE inner coding, bounded LZ, BWT/MTF, transforms and phrases have route/oracle restoration evidence. | Preserve the bounded complete-archive oracle; do not label a backend win native. |
| Native research mechanisms | Fixed/expert mixing, recurrence, periodic, higher CIXG2 contexts and word-palette are unqualified or experimental. Native rANS/FSE and a neural predictor are pending implementation. Word-palette-v2 measured a strong synthetic savings under its wrapper but no plain CIXG1 production win. | Open finite experiments are listed below. Keep excluded from automatic selector/package promotion until their complete-archive controls and fresh decodes exist. |
| Compact online neural predictor | **Absent and pending implementation.** Source inspection found deterministic fixed-point mixer weights in `src/fixedmix.rs`, but no `neural`, LSTM/GRU, embedding, pretrained-weight, or neural-model module under `rust/cix-native/src/`; `rg --files` also finds no native rANS/FSE source. Fixedmix is not relabelled as neural. | `fixedmix.rs` is the nearest bounded online update mechanism; `method-principles.md` calls current mixing partial rather than a neural model. | N7 below: a compact online byte predictor starts from frozen zero/constant weights, has integer-only deterministic updates, serializes any needed model state, and never reads pretrained weights. It remains pending until this exact cell runs or root records an implementation-scope blocker. |
| CIXB1 external backends | gzip, bzip2, XZ, Zstd and Brotli are complete payload backends. | Attribute any size change to the named backend and charge its CIXB1 envelope. |
| ZPAQ | Raw ZPAQ is a measured external reference; outer wrapping is rejected for the Dickens CIX archive only. | Do not call the raw ZPAQ lead a CIX modeling result. |
| Squash ABI | Native callback smoke passed, but an SDK-loaded Squash plugin is unverified because the host lacks the SDK. | Smallest closure cell is SDK build/load plus one ≤64 KiB encode/decode callback fixture, only if the SDK is already present; no download. |

## Six-capability audit disposition

The six requested capabilities are audited in
[`six-capability-audit.md`](../../2026-10-01-cix-optimization/six-capability-audit.md).

| Capability | Disposition | Smallest closure evidence still missing |
|---|---|---|
| Context mixing, recurrence, periodic models | Partial/experimental and **open** | Three one-step cells on the same ≤16 KiB frozen synthetic fixture: base fixed mixer; base plus saved recurrence-distance feature; base plus saved periodic feature. Use the same final coder and frame, then fresh-decode each. This separates recurrence/periodic effects from mixer presence. |
| BWT/sort with local coding | Partial/production | The one paid BWT local-stream cell above. |
| Stride/lane delta/XOR | Partial/production | Existing route/oracle evidence is sufficient for mechanism; no new width search is needed for closure. |
| Word dictionary with exceptions | Previously absent in production; WPV2 is experimental and measured only as an outer representation | Open: WPV2 already supplies the strong/weak/absent control pattern. Run its complete plain-CIX identity control and palette trial on the same frozen input under the same backend, then record an explicit no-promotion result if wrapper cost loses. |
| Separate literal/token models, repeat offsets, rANS/FSE | LZ stream separation exists; canonical Huffman exists; native rANS/FSE are absent and **open** | Implement bounded native rANS and FSE experiment frames, then measure both against existing canonical Huffman on identical four structural streams. Family absence does not waive the measurement; an implementation-scope blocker must be explicit. |
| Learned phrases and universal integers | Two-byte phrases and varints production; broader dictionary/universal-code comparison open | Run one fixed phrase payload with current varints versus one bounded Elias or Rice implementation in an experimental frame, complete bytes and fresh decode. An absent alternate coder is an open implementation task, not a pass. |

## Required finite native experiments

These are the minimum method-specific experiments required before package
closure. They are deliberately small and use only existing local/generated
bytes. Each has one raw/identity control, one changed mechanism, complete
archive accounting, one fresh archive-only decode, source/settings hashes, and
one core under the shared scheduler. A failure, size loss, malformed rejection,
or explicit resource/scope blocker is a result; an unrun cell is not.

| ID | Opportunity | Exact bounded cell | Completion condition |
|---|---|---|---|
| N1 | Recurrence/mixing | The three fixed-mixer cells stated above, ≤16 KiB. | All three archives fresh-decode; compare complete bytes only. |
| N2 | Periodic model | Same N1 fixture and frame; periodic feature bytes are serialized. | Fresh decode proves decoder needs no encoder state. |
| N3 | Substream coding | One frozen LZ payload split into tags/literals/lengths/distances; existing canonical Huffman, new bounded native rANS and new bounded native FSE each receive exactly those streams. | Every table/header/padding byte, normalization state and termination byte is charged. All three restore each stream exactly; rANS/FSE may close only by result or an explicit root implementation blocker. |
| N4 | LZW/reset dictionary | One generated ≤16 KiB reset-boundary fixture versus raw. | Experimental archive fresh-decodes or root records the scoped implementation blocker. |
| N5 | XPRESS-Huffman distinction | One generated ≤16 KiB command/literal fixture versus canonical-Huffman control. | The distinct token/table model is tested or root records the scoped implementation blocker. |
| N6 | Universal integer coding | One existing phrase/LZ length stream: current varints versus bounded Elias or Rice. | Complete bytes and fresh decode show the integer-code effect independently of parsing. |
| N7 | Compact online neural prediction | Three ≤16 KiB generated fixtures: strong predictable bytes, weak mixed bytes, and absent deterministic random bytes. Compare raw/identity against one compact online integer predictor with frozen topology, zero/constant initialization, fixed update order/rate, no pretrained weights, saved reset/model state and a raw fallback. | Every model/state/update descriptor and peak memory byte is charged; decoder reconstructs without encoder input; all three fresh-decode. Record size, encode/decode time, peak RSS and model-state bytes. |

## Generic-policy closure checks

The generic pipeline is frozen in
[`FORMAT.md`](../../2026-09-30-generic-pipeline/FORMAT.md),
[`PLAN.md`](../../2026-09-30-generic-pipeline/PLAN.md), and
[`selector-freeze.json`](../../2026-09-30-generic-pipeline/selector-freeze.json).
It prohibits filename, corpus/hash, semantic-parser and specialized-backend
routing. Existing external backends and historical PAQ evidence remain
separate. Therefore every local closure experiment above must freeze source
bytes, settings, implementation hash, resource receipt, complete archive
bytes, and fresh archive-only restoration, while using only byte-derived,
decoder-reconstructable state.

## Stop conditions

No experiment in this queue may add a download, dataset, full corpus run,
GitHub Action, public release, production selector edit, or unbounded codec
tournament. A negative result closes its declared cell. A resource or scope
blocker closes a cell only when root records why its named smallest experiment
cannot run. Absent and unqualified rows remain open until one of those events.
