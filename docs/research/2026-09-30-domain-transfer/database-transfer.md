# Database-domain transfer: initial evidence

This transfer deliberately uses a real, external CSV dataset rather than OSDB
or a manufactured MyISAM record stream. The frozen input is the World Bank
World Development Indicators API download for USA and Canada total population.
Its exact acquisition URL, ZIP, extracted member, hashes, and byte-preserving
extraction procedure are in `database-provenance.json`.

The adapter in `benchmarks/domain_database_csv.py` preserves the source syntax:
raw field tokens, quoting, commas, headers, and `LF`/`CRLF` terminators are all
in the reversible frame. It neither parses numerical values semantically nor
rewrites CSV as a synthetic database format.

## What transfers from the OSDB result

The reusable component is a fully charged sequence representation: transmit a
field-token palette and its counts, then encode the row order with dynamic
remaining-count arithmetic (the former mode 3 mechanism). The decoder obtains
all palettes, counts, raw templates, and ordering from the frame alone.

The following winning-implementation assumptions do not transfer: MyISAM row
layout, field-width and null-map assumptions, date and numeric semantics,
four-byte row alignment, record packing, and OSDB-specific parser knowledge.

## First physical result

On the frozen 2,244-byte input, all direct frames decoded byte-for-byte:

| Complete self-contained frame | Bytes | Difference from literal |
| --- | ---: | ---: |
| Literal | 2,253 | 0 |
| Dictionary + remaining-count arithmetic | 3,036 | +783 |

There are seven records and three literal templates, but only eight repeated
field tokens among 221 field tokens. The charged palette/count/template
metadata therefore outweighs the small repetition. This is a negative
structural result, not a PAQ result.

No packing ablation is justified yet: the exact source has zero recoverable
alignment padding, and no redundant termination capacity was established. A
future packing comparison, if evidence motivates one, must compare the same
structural representation before and after packing, not structural bytes with
raw bytes.

## Next controlled comparison

The predeclared test is original CSV bytes through pinned PAQ v216 `-4` AVX2
against the complete structural frame through that identical PAQ invocation.
It must charge every frame byte and independently reconstruct the original
CSV. This evidence package has not run that compression job, so it makes no
claim about PAQ capacity sharing or compression gain.

## Stronger fixed relational sample

The World Bank prefix is retained because it shows where this mechanism does
not pay, but seven records cannot meaningfully test a dictionary/count model.
The second predeclared asset is the first 2,048 complete nonblank records, in
source order, from UCI's Adult `adult.data` member. It is a real mixed
categorical/integer relational table, selected by a fixed ordinal rule before
measurement. `database-uci-adult-predeclaration.json` pins the official ZIP,
member, sample, extraction rule, and hashes.

| Complete self-contained frame | Bytes | Difference from literal |
| --- | ---: | ---: |
| Literal | 249,665 | 0 |
| Dictionary + remaining-count arithmetic | 32,019 | -217,646 |

All frame bytes are charged and both variants round-trip exactly. The profile
has one 15-field raw record template across 2,048 rows and 28,408 repeated raw
field tokens among 30,720. That is a direct structural opportunity, not proof
of a PAQ gain: the same redundancy may already be represented by PAQ. The only
permitted next measurement is the frozen same-backend control/candidate pair.
