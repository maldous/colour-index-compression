# RC21 incremental source review

**Snapshot reviewed:** the replacement `src/incremental.rs` captured by the
running `execution-foundation-v11` qualification.

**Method:** read-only static inspection. No build, test, codec, benchmark, C
consumer, deadline, cancellation, or memory measurement was run by this
reviewer.

## Current source result

The prior state-machine defects are addressed in the inspected replacement.
The implementation is a deliberately narrow **Rust-only independent CIXG1
block API**, not a complete RC21 closure.

- Public encoder/decoder calls pass every result through
  `Control::finish_call`, which poisons the object on error
  ([incremental.rs:93-98](../../../../rust/cix-native/src/incremental.rs),
  [193-200](../../../../rust/cix-native/src/incremental.rs),
  [413-420](../../../../rust/cix-native/src/incremental.rs)). `reset` clears
  that state and reconstructs stream state ([365-375](../../../../rust/cix-native/src/incremental.rs),
  [587-600](../../../../rust/cix-native/src/incremental.rs)). This corrects
  the former consumed-input/hash continuation hazard.
- `Control` captures one absolute deadline at construction or reset and derives
  only the remaining duration for delegated codec work
  ([45-119](../../../../rust/cix-native/src/incremental.rs),
  [310-320](../../../../rust/cix-native/src/incremental.rs),
  [538-548](../../../../rust/cix-native/src/incremental.rs)). Public calls
  check caller cancellation and expiry before intake
  ([76-91](../../../../rust/cix-native/src/incremental.rs),
  [206](../../../../rust/cix-native/src/incremental.rs),
  [426](../../../../rust/cix-native/src/incremental.rs)). It no longer renews a
  configured duration per block.
- The decoder validates the paid source length and output limit before it
  allocates payload storage ([491-529](../../../../rust/cix-native/src/incremental.rs)). It validates the SHA-256 end frame before setting finished
  ([495-501](../../../../rust/cix-native/src/incremental.rs)) and rejects
  supplied bytes after the end frame, including bytes remaining in the same
  call ([431-435](../../../../rust/cix-native/src/incremental.rs),
  [483-485](../../../../rust/cix-native/src/incremental.rs)).
- Pending output owns a moved `Vec` and drains by position instead of retaining
  duplicate whole-frame copies ([121-161](../../../../rust/cix-native/src/incremental.rs)). The encoder reserves its input/archive buffers before
  passing only remaining budget to the codec ([305-363](../../../../rust/cix-native/src/incremental.rs)); decoder similarly charges its synthetic member and
  restored plaintext before delegation ([517-570](../../../../rust/cix-native/src/incremental.rs)). This is a coherent source-level accounting model for
  CIX-owned buffers. The module explicitly does not claim a process RSS cap or
  account caller-owned input/output buffers ([1-8](../../../../rust/cix-native/src/incremental.rs)).
- Wire scope is explicit: CIXG1, flags zero, independent source blocks of at
  most 64 KiB. Other native wire versions and history-bearing streams use
  `core::decode` ([378-379](../../../../rust/cix-native/src/incremental.rs)).
  The encoder's header/frame/end construction and decoder's synthesized one
  frame member preserve this ordinary independent CIXG1 form.

I found no new demonstrable state, framing, or arithmetic defect in this
replacement from static inspection. `try_reserve_exact` and checked arithmetic
are used for owned variable-sized buffers before the relevant copy/decode
paths. Actual route workspace, allocator behavior, and third-party runtime
allocations remain qualification questions, not a hard-RSS guarantee.

## Evidence still required

The five focused contract cases in
[tests/incremental_contract.rs](../../../../rust/cix-native/tests/incremental_contract.rs)
cover fragmented I/O, ordinary-core cross-decode, pre-finish output, checksum
and trailing input, reset/terminal behavior, cancellation/deadline entry, and
paid limits. They are source evidence only until the running qualification
reports results. Additional qualification should retain irregular backpressure,
incompressible block, malformed header/frame/end, and multi-block absolute
deadline coverage.

## RC21 remains partial

The public C ABI deliberately says its operations are complete-buffer and that
v1 has **no incremental API** ([cix.h:51-78](../../../../rust/cix-native/include/cix.h)).
There is no C stream/chunk handle or independently compiled C streaming
consumer in this snapshot. Therefore this implementation may qualify a bounded
Rust independent-block API, but it cannot satisfy the broader RC21 SDK
incremental-I/O/chunk requirement by itself. The reconciliation ledger should
remain open until that C ABI scope is delivered or RC21 is explicitly narrowed
by an approved requirement decision.
