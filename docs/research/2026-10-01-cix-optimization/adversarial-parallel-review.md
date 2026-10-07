# Adversarial review: parallel native CIX path

Date: 2026-10-01

Scope: the current Rust CIXG1/CIXG2 streaming encoder and its selector,
resource, cancellation, fixed-mix, and archive-decoder paths. This is a
source-and-test review. It does not report a throughput, memory, or
compression-size measurement.

## Review method

The review traced an owned block from `gstream.rs` through `parallel.rs`,
`resources.rs`, `limits.rs`, selector code in `main.rs`, and archive decoding.
It inspected `parallel_pipeline.rs`, `resource_admission.rs`, `codec_limits.rs`,
`streaming_pipe.rs`, `fixedmix_recurrence.rs`, `selection_overrides.rs`, and
`cli_archive_oracle.rs`. A cited test names a specific local test; it does not
claim unmeasured production performance.

## Findings and existing fixes

### Ordered bounded blocks

**Risk.** Parallel encodes finish out of order. Completion-order output changes
archive byte order, while uncharged reordered results can grow memory without a
bound.

**Fix.** `OrderedPipeline` assigns a sequence at submit, stores completions in
a `BTreeMap`, and releases only the next input-order item. Its `outstanding`
count includes queued work, active work, and completed out-of-order results
until the writer consumes them. `gstream::encode` writes only that ordered
receive path. A later fast block cannot pass an earlier block or make an
unbounded reorder queue.

**Evidence.** `completes_in_input_order_even_when_workers_finish_out_of_order`,
`completed_reordered_results_still_consume_capacity`, and
`capacity_one_keeps_a_completed_result_admitted_until_it_is_received`.

### Global memory permits and backpressure

**Risk.** Private `--memory` limits for each worker multiply the process budget.
A fast producer plus slow destination can also create unbounded read-ahead.

**Fix.** The streaming path charges retained source/result buffers and thread
allowance through `parallel_retained`, then shares a single `MemoryBudget` among
all candidate workers. Each candidate takes an RAII permit before encoding and
keeps it while its payload is live. The ledger rejects impossible requests,
tracks peak reservation, and releases during unwind. The reader drains ordered
results before reading again and blocks when every pipeline slot is occupied.
Complete frames are flushed as framed header plus payload.

The permit ledger is an admission bound from conservative route estimates. It
does not measure RSS from allocator internals, mappings, stacks outside the
reservation formula, or page cache.

**Evidence.** `concurrent_permits_never_exceed_budget_and_record_peak`,
`oversized_request_fails_without_waiting_or_charging`, and
`permit_is_released_during_unwind`; plus
`slow_downstream_consumer_preserves_bytes_without_deadlock`,
`nonseekable_irregular_producer_emits_a_frame_before_eof_and_round_trips`,
`idle_input_flushes_a_partial_frame_before_eof`, and
`parallel_stream_can_exceed_its_working_memory_budget`.

### Cancellation and finite candidate work

**Risk.** A failed worker can leave queued jobs, active siblings, or blocked
senders waiting. A trial can outlive its block search budget, and an admission
waiter can miss cancellation without a permit release.

**Fix.** Worker calls are inside `catch_unwind`. Worker error or panic stores
the first failure, raises a shared cancellation token, clears queued jobs and
completed results, wakes waiters, and joins workers through `finish`, `cancel`,
or drop. `CancellationGuard` installs that token for the worker's codec loops.
`DeadlineGuard` uses the shorter of the remaining search budget and trial
budget; it is thread-local, cannot extend an outer deadline, and restores the
prior deadline on drop. `MemoryBudget::acquire` checks cancellation at least
every 50 ms. Rank, adaptive, PPM, and fixed-mix contain cooperative checks.

Cancellation remains cooperative. A future route or native-library call needs
a finite cancellation-aware boundary before it can join this pipeline.

**Evidence.** `worker_error_and_panic_cancel_pending_work_without_deadlock`,
`worker_failure_signals_a_running_sibling_through_the_shared_token`,
`cancellation_drops_queued_jobs_and_joins_workers`,
`expired_deadline_stops_costly_encoders`,
`deadline_guard_restores_the_outer_scope`,
`nested_guard_cannot_extend_outer_deadline`,
`pipeline_cancellation_is_thread_local_and_restored`,
`waiting_admission_observes_cancellation_without_notification`, and
`deadline_expires_when_capacity_stays_held`.

### Circular fixed-mix history

**Risk.** Front deletion from a byte vector copies data per eviction. A rewrite
can also alter the logical index relationships used by frozen v1/v2 paths.

**Fix.** `fixedmix::History` is a fixed-capacity circular store. `get(logical)`
maps through its start offset; after filling, `push` overwrites the oldest byte
and advances that offset. The legacy logical ordering is retained and eviction
is O(1).

**Evidence.** `v1_canonical_fixture_is_unchanged` and
`legacy_v2_fixture_retains_its_decoder_semantics` compare canonical bytes and
decode results.

### Recurrence v3 and legacy decode

**Risk found and fixed.** The old experimental recurrence interpretation looked
up a distance feature after observing its byte. That can differ from decoder
causal state. Changing that meaning under v2 would corrupt historic archives.

**Fix.** Corrected emission uses fixed-mix version 3 and a serialized saturated
recurrence configuration. It saves the feature produced while observing the
previous byte and consumes that saved feature for the next prediction. Decoder
dispatch preserves v2's legacy configuration and semantics, and uses corrected
semantics for v3. It checks version, learning-rate ID, configuration, bit
length, and exact payload length before decode.

**Evidence.** `recurrence_v3_round_trips_with_prefix_history`,
`v3_uses_saved_causal_distance_features_not_legacy_distance_one_lookup`,
`legacy_v2_fixture_retains_its_decoder_semantics`, and
`recurrence_v3_rejects_malformed_truncated_and_corrupted_payloads`.

### Format gates and stream integrity

**Risk.** A CIXG1 decoder accepting extended context-range or Huffman coder IDs
makes the legacy format ambiguous. Incremental output could also be mistaken
for whole-stream integrity before footer verification.

**Fix.** `native_magic` selects CIXG2 for explicit CIXG2, maximum-effort auto,
or explicit extended backend. Explicit CIXG1 rejects those backends. Decode
derives `allow_extended_coders` from magic; coders 6 and 7 reject in CIXG1 and
validate headers and decoded length in CIXG2. Substream parsing validates
descriptor boundaries, total decoded length, raw lengths, and trailing bytes.
CIXG frames contain source/payload lengths and SHA-256; the END frame has a
rolling whole-stream SHA-256. CIXM6 validates terminal total length and CRC32.
Bytes can be emitted before EOF, but whole-stream integrity completes only when
the final footer is verified.

**Evidence.** Targeted extended-coder coverage is in `tests/huffman.rs`.
`tests/cli_archive_oracle.rs` fresh-decodes each archive in its documented
CIXG1-only universe. `decoder_reconstructs_a_complete_frame_before_archive_eof`
and `empty_truncated_and_corrupt_streams_have_defined_pipe_behaviour` exercise
early decoded bytes and terminal rejection.

### Route and backend override truthfulness

**Risk found and fixed.** An explicit route could retain the requested route ID
when raw fallback won, so the decoder would parse raw bytes as route payload.
An explicit backend could also silently evaluate a different backend and report
the wrong attribution.

**Fix.** `select_cixg_fixed_route` starts with raw incumbent and route ID 0.
It filters non-raw candidates to the requested route and compatible backend;
only a strictly smaller non-raw candidate replaces raw, so ties stay raw.
`selection::generate_candidates` validates route IDs, backend names, and
compatibility before generation. Raw is the only raw candidate; intrinsic
overrides select compatible intrinsic routes, and nested backends apply only to
routes 2 through 7. Explicit context-range and Huffman compare only themselves
with raw fallback.

**Evidence.** `tests/selection_overrides.rs` covers labels, incompatible pairs,
global overrides, raw retention, and invalid values. `tests/cli_archive_oracle.rs`
enumerates 35 bounded CIXG1 route/backend candidates for two tiny inputs,
fresh-decodes each complete archive, and compares automatic BEST with the
complete-archive minimum in that stated finite universe.

## Open gaps and required queue

1. Automatic CIXM6 packaging selection is absent. Ordinary CIXG effort
   selection does not materialize and compare CIXM6 against CIXG1/CIXG2 using
   complete archive cost.
2. Native `--best` is bounded. It has finite sampling, shortlist, candidate
   limit, search deadline, trial deadline, and active block policy. The tiny
   oracle is complete only for its documented one-frame, 35-candidate CIXG1
   universe; it does not establish global optimality across transforms,
   parameters, segmentation, history, packages, or external codecs.
3. Parallel streaming applies to independent CIXG blocks. Stateful CIXM6
   history and persistent-model routes remain sequential. Their size and
   throughput tradeoff needs matched measurement.
4. The permit ledger needs peak RSS qualification. Focused tests do not replace
   the Canterbury/Calgary/Artificial gate, fresh-process differential checks,
   malformed-input fuzzing, or held-out replicated records.

The follow-up queue is: add archive-level CIXG1/CIXG2/M6 package comparison;
expand finite oracles one dimension at a time; measure one through four
independent-block workers under identical build/input/budget while recording
wall time, CPU time, peak RSS, size, and first-output latency; and require
cancellation qualification before each future native route enters DEFAULT or
BEST.

## Additional fixes from final review

- Unix stdout uses nonblocking partial writes and 50 ms writable polling. Its explicit `write_all` implementation propagates cooperative interruption instead of retrying `Interrupted` forever. The output thread observes the same cancellation token as workers, and returns the original worker error. The non-Unix fallback is source-reviewed only.
- Decode admission sums serialized payload, reconstructed output, route temporaries and the largest sequential substream coder workspace. The descriptor-only scan includes bounded context-range models and native DEFLATE state before any model table is allocated.
- CIXM6 checks its retained history/source/winner/candidate reserve before writing a header, caps its reference queue to the remaining budget, and charges causal priming when admitting PPM/mixture. History is pruned before append so its capacity does not grow past the reserved window; references use `VecDeque`.
- Public library codecs and CLI selection now share one deadline/cancellation module. This avoids separate thread-local deadlines when the CLI is embedded through the Rust C ABI/Squash path.
- Stride substreams borrow slices from the transformed block rather than copying every lane. Additional phrase/LZ/substream loops poll cooperative limits.

Focused process regressions include stalled-stdout SIGINT, peer-token cancellation, 64 KiB BWT admission at 128 KiB, and context-range admission at 1 MiB. Performance evidence and final aggregate test counts are recorded separately after execution.
