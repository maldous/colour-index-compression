# Native CIXH1 automatic mixed selection

`full_engine/mixed_selection.rs` applies the historical CIXH1 policy to the
existing native CIXH1 carrier.  `regions::regions` partitions every input byte;
generic gaps are stored or competed with zlib level 6 and XZ preset 3.  Each
recognised span is independently catalogued and may try at most eight
specialists, ordered round-robin by family.  It does not invoke whole-input
selection recursively.

The complete CIXH1 region frame cost participates in every choice.  Ties keep
the earlier backend, so stored data wins equal-cost generic ties.  Specialist
IDs are paid parameters, and source bytes, region headers, payloads, and
parameters are retained only within the carrier's declared output and memory
limits.

Before a provider runs, the selector reserves the incumbent payload capacity
and the next candidate's paid parameters.  The provider receives only the
remaining workspace and a strict payload cap: enough to beat the incumbent
after charging its own region header and parameters, and no more than the
remaining archive space.  Region/range planning and the capped diagnostic
buffer are admitted before input-derived partitions are allocated and are
deducted from the carrier workspace.

FAST admits generic backends only. DEFAULT observes every PAQ-specialist
omission. BEST admits eligible specialist attempts subject to the five-GiB
nested per-candidate limit, ten-GiB aggregate limit, a single-worker policy,
and the caller's current operation workspace.  Diagnostics are capped at 4096
records, retain selected backend and region plus every retained failure or
omission, and count records omitted from the report cap.

The policy preserves the operation deadline and cancellation token in every
provider request and checks both before each region and before returning an
archive.  It relies on `mixed::encode_with` for CIXH1 framing, source digests,
complete partition validation, and simultaneous carrier-buffer accounting.
Catalogue and specialist failures retain the generic incumbent and appear in
the bounded diagnostic report; they cannot discard a region's bytes.

The selector requests native `BackendVariant::Xz { preset: 3 }` and writes the
historical paid parameter `preset=3`.  The provider now passes explicit liblzma
easy presets through 0 through 9, so this uses the same level as the reference
generic candidate.
