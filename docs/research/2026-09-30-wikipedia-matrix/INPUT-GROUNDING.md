# Input and grammar grounding

Retrieved sources and their SHA-256 hashes are preserved in `references/manifest.json`; exact downloaded files are adjacent.

The local file is exactly 1,000,000,000 bytes. The read-only asset audit recomputed MD5 `e206c3450ac99950df65bf70ef61a12d`, SHA-1 `2996e86fb978f93cca8f566cc56998923e7fe581` and SHA-256 `159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc`. The first two agree with [Mahoney's canonical enwik9 definition](https://mattmahoney.net/dc/textdata.html). This is the first billion bytes of the historical March 2006 dump, not a modern entire-Wikipedia dataset.

The header declares the `http://www.mediawiki.org/xml/export-0.3/` namespace, version `0.3`, language `en` and the export-0.3 schema. Site metadata reports `MediaWiki 1.6alpha`. The byte prefix, including the truncated final record, is the compression input; no XML cleanup occurs.

[Export-0.3 XSD](https://www.mediawiki.org/xml/export-0.3.xsd) formally describes the XML envelope: page titles, optional IDs/restrictions, revision/upload alternatives, and revision timestamp/contributor/minor/comment/text fields. Its text value does not define a complete wikitext grammar. We use schema relationships as predictor hypotheses while preserving actual bytes and exceptional syntax.

[XML 1.0](https://www.w3.org/TR/xml/) defines parsing behavior including line-ending and attribute-value normalization. Semantic XML equivalence is therefore insufficient for byte-exact compression. Entity spelling, whitespace, attribute order, numeric formatting and incomplete fragments must remain reconstructible.

[MediaWiki Markup spec](https://www.mediawiki.org/wiki/Markup_spec) is a collection of grammar/parser-description efforts and explicitly describes them as incomplete. Its ambiguity and recovery discussion explains why this work uses conservative byte spans and literal fallbacks rather than assuming a reversible parse-tree rendering. The archived retrieved revision link is retained in the source HTML.

Mahoney discusses US town/census articles, long paragraph lines, redirect structure and repetition at large distances. These motivate structural profiling; they do not establish an advantage over PAQ. The v2 asset locator uses actual census-pattern lines and redirect syntax following `<text...>` to select discovery regions before compression. Generic table frequency is not labelled census evidence.

## Exposure correction

The first broad profiler tested only a window's starting offset against reserves. Four profiled windows intersected intended reserved strips. Its decimal 64M endpoints also differed from the intended 64 MiB. v1 source, plan and output are preserved under `asset-v1/`; `exposure-correction.json` records the error, and v1 is invalid for region selection.

v2 skips every window with any intersection with `[600000000,667108864)` or `[900000000,967108864)`. Historical exposure is not undone by that fix. New 4–16 MiB validation reservations begin at 620M and 920M, wholly inside the interiors excluded from both structural scans. They remain historically read as part of earlier whole-corpus work and are withheld specifically from current adaptive structural tuning. They have not been compressed in this programme.
