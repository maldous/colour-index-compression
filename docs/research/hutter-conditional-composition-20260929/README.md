# Conditional composition against an identical fx2 predictor

Status: source implementation prepared; not built or measured.  This note is
not a Hutter Prize score or an assertion of an advantage over arithmetic
coding.

## Implementable route

An isolated GPL-3.0 derivative is at
`/home/user/src/cix-hutter-rd/conditional-composition/fx2-cmix-pinned`, copied
from the pinned `fx2-cmix` source revision
`04c5806f99b9b0fa8572be8c8063b4324ec405de`.  Its upstream GPL-3.0 licence is
retained.  The experiment adds a raw-stream `conditional_cmix` interface and
does not alter the pinned source checkout or the current CIX repository.

For each block, the encoder calls the unmodified `Predictor::Predict()` once
per real bit, discretizes the result in the same way as fx2's range coder, and
then calls `Predictor::Perceive(actual_bit)`.  It records the exact bit and a
causal probability bin derived before the perceive call.  There are two
contenders from that one trace:

1. the framed range control uses the exact discretized fx2 probability at each
   bit;
2. conditional composition emits, for every probability bin, its visit count
   and one count, then encodes the sequence using the exact remaining-one
   probability for that bin.

The decoder independently instantiates the same predictor from the archive's
counted vocabulary bitmap, predicts each next bit, derives the bin, decodes a
bit, and immediately calls `Perceive(decoded_bit)`.  It retains predictor state
between blocks.  It never reads an encoder trace, predictor checkpoint,
dictionary, or sidecar.

The complete experimental archive contains magic/version, bin count, block
size, original byte count, 32-byte vocabulary bitmap, and length-delimited
blocks.  Each block contains its mode, bit count, payload length and, for
composition mode, bin count plus every `(visits, ones)` pair as canonical
varints.  Decoder checks reject malformed varints, impossible counts, a
predictor/bin trajectory not matching transmitted visits, truncated payloads,
trailing bytes, and output-length contradictions.  The selection compares the
complete framed range and composition byte sequences for that block, including
all metadata.  Ties retain range.

## Interpretation guardrail

Given a fixed count vector, the composition payload is simply a range-coded
uniform ordering among sequences with those counts.  It cannot beat a
count-informed arithmetic coder that is given the same counts: the two are
alternative implementations of the same conditional state space, up to finite
precision/framing overhead.  It can only beat the ordinary fx2 range control
if the transmitted count metadata buys enough mismatch correction to outweigh
its cost.  That is the actual controlled question; no result may be described
as an advantage over arithmetic coding merely because it used counts the
control did not receive.

## First finite experiment after the boundary clears

Use the complete `.ready4cmix` stream created by the separately queued fx2
transform-only run, rather than a raw enwik9 prefix.  The first comparison is
a fixed 16 MiB transformed-stream window preceded by a deterministic causal
warmup from the same stream, with bins 4, 8 and 16 and blocks 16 KiB and 64
KiB.  Each setting needs:

* separate fresh predictor encode and decode runs;
* byte-for-byte output hash verification;
* range-only, composition-only, and selected physical byte counts;
* per-mode selected block counts, exact command, source revision, compiler,
  peak memory and elapsed time;
* proof that both contenders consumed exactly the same p1/bit trace during
  their encode-side comparison.

This is six settings, not an open-ended tournament.  Build or run it only once
the prior measurement service has stopped and while holding
`evidence/baseline-20260929/raw/measurement.lock`.  Use the fixed P-core CPU 8
for paired measurements. A local clang-18 build is
explicitly not bit-identical to the winner's clang-17 PGO/LTO/UPX executable.

## Complexity and expected value

Encoder trace storage is O(block bits): about 256 KiB at a 64 KiB-byte block
using the current compact trace fields.  Composition state is O(bin count).
The predictor remains the dominant time and memory cost.  The decoder needs no
trace.  This makes a bounded experiment practical under the Prize memory rule,
but it does not make an improvement likely: calibrated PAQ probabilities carry
more positional information than coarse bins, and count-vector metadata is
usually costly on natural language.  The design is retained because it is an
exact, falsifiable test of the CIX residual hypothesis on the winner's actual
predictive state.
