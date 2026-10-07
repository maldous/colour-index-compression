# RSL1 exact transformed-byte deduplication

Status: prepared, not executed. This is an implementation-only follow-up to
the verified single RSL1 screen. It retains the original twelve programs, their
order, RSL1-v2 frame format, complete-size comparison, first-candidate tie
rule and final fresh archive-only restoration.

The existing baseline proved that `mod-delta-1` and
`previous-stride-residual-1` have exactly equal transformed bytes; the same is
true for lag four. The native CIXG1 archive and decoded plaintext are therefore
reusable only after direct full-byte equality of the transformed streams.
There is no digest lookup and thus no hash collision acceptance.

The raw literal fallback remains separate. For each nonliteral cache hit, the
driver writes the reused native payload and decoded plaintext into that
candidate's retained paths, builds that candidate's own RSL1 frame, and runs
its inverse proof. Its result row has `native_trial_performed:false` and a
`reused_from` candidate index; encode/decode timings and child-RSS fields are
`null`, rather than fabricated zero measurements. Misses retain one native
encode and decode. The expected screen has nine actual native trials from
eleven nonliteral candidates, rather than eleven.

The cache has at most 307 entries and reserves the entry-vector metadata in
its accounting. Each entry uses exact-size boxed buffers for transformed key,
native payload and decoded plaintext. The accounted entry storage plus all
three buffers is capped at 4 MiB. A 64 MiB full-mode transform cannot enter
that cache, so it safely falls back to independent native trials.

This experiment reuses the prior baseline evidence; it must not rerun that
baseline. It binds the same 8,192-byte Kennedy development prefix and immutable
`benchmark-work/ptt5-fixed-8439/final/{cix,uncix}` pair. It makes no selector,
format, profile or production change. The dedup source is a copy of the
canonical RSL1 driver with only cache mechanics and reporting changed.

The frozen external validation harness, rather than the generic driver,
compares the new selected archive and every complete candidate size to the
existing baseline evidence. The driver has no corpus or baseline-file branch.
Promotion requires byte-identical selected archives, matching candidate sizes,
and fresh archive-only exact restoration. A cache mismatch, integrity failure
or budget breach stops the experiment.


## Qualified screen

The single optimized screen passed; see REPORT.md/results.json. No production promotion follows automatically.
