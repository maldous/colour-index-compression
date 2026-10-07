# Paid constant-model experiment RNC1 — pre-execution plan

Hypothesis: the qualified ERC intersection has smaller rank space than either
single-component model under equal description cost. The direct dictionary
already represents the same joint space, so equal-model-cost comparison with
that control must tie in rank payload. This experiment can falsify attribution
errors; it cannot establish a new entropy principle by padding archives.

Reuse all8 immutable input/qualified archive identities from ERC v1. No input
acquisition, new benchmark run, selector tuning or production changes. One
observation per cell; no repetitions for averages. Original sizes and controls
remain authoritative for compression rankings.

RNC1 is an isolated native framing adapter, not a production format. Every
archive pays10 outer header bytes,256 model bytes and4 CRC bytes. ERC uses
20 model bytes; RDIC uses15 header bytes plus the complete combinadic dictionary
rank. All unused model bytes are canonical zero padding. The largest admitted
RDIC model is188bytes, so no model information is discarded. Only the sequence
rank/literal payload remains outside that fixed area. Thus every model has
exact complete length270+payload_bytes. The artificial common fee is explicit.

Native uniform control encodes an arbitrary nonempty even-length two-symbol
input with paid sorted alphabet, nbit exact rank, no equality or count
restrictions. It uses the decoder-supported ERC E zero-mask model, with b2
partition; global cardinality is2^n. The alphabet restriction is common paid
information to all structural models. Raw byte rank8n is not an appropriate
universe for assessing their interaction.

For every applicable existing mode and dictionary control: pack; unpack to a
byte-identical original archive; fresh native decode; SHA-256 compare input.
Verify canonical fee, model boundary, every rank/literal byte, and inner archive
identity. For structured joint comparisons also independently verify equal
length, width, alphabet, vocabulary and identical EC/dictionary sequence ranks.
Uniform rank is independently verified by the integer oracle. None of these
Python calculations is a reference codec.

Report exact rank widths, padded payloads and complete bytes separately. Define:

    marginal_rank_gain = min(RE,RC) - REC
    rounded_bit_surplus = RE + RC - RU - REC
    rounded_byte_surplus = PE + PC - PU - PEC
    common_fee_control_gain = LD_normalised - LEC_normalised.

The first is ordinary intersection shrinkage. The surplus subtracts what an
additive reduction from the common uniform universe predicts; it is not PID or
mutual information. Unequal-description effects must not be mixed into it.
Positive surplus and a direct-control tie can occur together.

Test five malformed outer archives: truncation, CRC, and CRC-valid invalid
padding/codec/length. Nonzero status and no output required. RNC only validates
framing-relevant native metadata; the fresh native decoder is mandatory for
complete semantics. All outputs are new and measured under the bounded work
directory.

Use existing global WaveScheduler lock/one CPU8 lease, one-core quota,2GiB
memory, swap0,64MiB active temporary cap. Build and batch each120s, each child
10s. Aggregate phases pass input_bytes0 rather than inventing throughput.
Exact source/runner/baseline/binary/dependency hashes freeze before dispatch.
Record all losses/ties, command timings and raw receipts. Only root commits
and pushes; private repository and disabled Actions verified before push.
