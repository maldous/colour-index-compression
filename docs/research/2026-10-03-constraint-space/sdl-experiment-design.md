# SDL bounded native model-description experiment

Status: design after the prior-art gate. Likely novelty is level 0 or 1:
measurement and integration of established representation methods, rather than
a new counting theorem.

## Fixed model universe

For each block, enumerate a finite ordered set of state-set models with
`b <= 12`. The candidate universe contains models derived automatically from
existing ERC inputs and unrelated generic structural families: equality chains,
bounded periods, runs, binary component weights, and small Boolean relations.
No corpus name, semantic parser or manually selected family dispatch is used.
Candidate ordering, state alphabet, and detector limits are versioned.

Every accepted logical truth set is serialized in each of these exact same
representations:

1. direct combinadic dictionary;
2. bitset truth set;
3. RLE truth set;
4. serialized ROBDD under a canonical variable order;
5. flat constraints; and
6. DAG components with shared canonical subtrees and parameters.

The detector interns repeated canonical subtree hashes and parameter tuples.
It does not reuse a component because a fixture has a particular name. DAG
sharing bytes, references, topological order and canonicalization version are
part of the archive.

## Equal accounting

Each candidate archive contains: format version; model representation bytes;
variable/state ordering;
count/rank convention; exact rank; source length; residual/literal bytes;
CRC; and raw fallback. Generic shared decoder software is excluded consistently with standard
reference archives; its exact source/build identity is recorded in provenance.
Any per-model/source-specific assets or pretrained dictionaries must be paid
in the archive. This instrument is not a self-extracting-program comparison. A control additionally
stores flat constraint metadata compressed by pinned zstd, including zstd
version/options and compressed plus uncompressed byte counts. It is a metadata
control, not an external-codec portfolio result.

No representation is credited for a model description it did not store. A
decoder needs only the selected result model, ordering, semantics and rank; it
does not need both input models and their intersection result.

## Exact oracles and fixtures

The first fixtures are small enough for exhaustive truth-set oracles:

| Family | Development | Held-out after freeze | Oracle |
| --- | --- | --- | --- |
| Two-way | equality plus period; period plus run | new parameters and state labels | enumerate all `2^b` assignments |
| Three-way | equality, period and local relation | new independent parameter tuple | enumerate all `2^b` assignments |
| Absent sharing | unrelated small relations | independent seed/relations | exact bitset count |

For every model representation, the oracle verifies truth-set equality, exact
count, rank and unrank against the canonical bitset. Count/rank/unrank timing,
peak memory and model bytes are distinct measurements. Development determines
only finite detector parameters. Root freezes new held-out families and truth
sets before selection; it does not pick a winner fixture.

## Smallest honest implementation

After prior-art review, root may implement a stand-alone experimental driver:
`sdl encode INPUT ARCHIVE` and `sdl decode ARCHIVE OUTPUT`. It must use raw
fallback for arbitrary bytes; cap `b` at 12; emit all candidate model costs;
and call an independent process for archive-only restoration. One 4–16 KiB
block per configuration, one measurement, one CPU, 768 MiB RAM, no swap,
64 MiB temporary storage and 120 seconds are sufficient for the first screen.

Promotion requires a complete archive win over bitset, flat and zstd-flat
controls on development, exact oracle agreement, and replication on the frozen
held-out two-way and three-way families. It authorizes no production selection.
