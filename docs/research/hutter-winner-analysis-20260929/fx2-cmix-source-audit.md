# fx2-cmix source audit and CIX experiment priorities

Retrieval and static analysis: 2026-09-29.  This note is research input, not a
claim that CIX has reproduced the winner or is Prize-qualified.

## Verified reference

The live Hutter Prize page lists Kaido Orav and Byron Knoll's `fx2-cmix` as the
current Prize record: 110,793,128 counted bytes, dated 3 September 2024.  The
next one-percent submission total must be at most 109,685,196 bytes.  The
historical text-compression table separately reports the archive payload at
110,351,665 bytes; it must not be confused with the Prize's counted total.

The authors' archived public repository is:

* URL: `https://github.com/kaitz/fx2-cmix`
* pinned commit: `04c5806f99b9b0fa8572be8c8063b4324ec405de`
  (2024-10-11, `Update README.md`)
* repository content digest (sorted `sha256sum` records):
  `c77ff8adf8d6430d9631b5cbab72d695d0df57d9dd41d4c544cee0155455b28c`
* root `LICENSE`: GPL-3.0, SHA-256
  `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`
* `README.md`: SHA-256
  `d5459e04dca6a07283d32b0be6ec0bae0c9041a9e152c01396b3c8f0d3b490a3`
* `dictionary/english.dic`: 411,996 bytes, SHA-256
  `4c8568cca9343b9a6212477880f56f8efd162f8784224a25edd043097d36215a`
* `src/readalike_prepr/data/new_article_order`: SHA-256
  `4d0fa5313c753c1ecf71e91a83e285894cdde20049711456e6514c07eb85c581`

The local, read-only reference copy is
`/home/user/src/cix-hutter-reference-sources/fx2-cmix`.  No source or binary
from it has been copied into CIX.

The winner's README gives its exact self-extracting form: compressor `cmix` is
441,463 bytes; `archive9` is 110,351,665 bytes; together they are 110,793,128
bytes.  It reports a 461-model predictor, a 65-hour decompression measurement,
9,523,660 KiB peak RAM, and about 21 GB disk on its stated evaluation setup.
Those are author-reported figures, not local reproductions.

## What the winning package actually does

This is not generic cmix with a different preset.  The `-e` enwik9 path in
`src/runner.cpp` performs a reversible enwik9-specific pipeline before bitwise
context mixing:

1. split the XML dump into intro, article region, and coda;
2. reorder the articles using an embedded order payload;
3. apply the phda9/Wikipedia reversible transform;
4. concatenate the transformed streams;
5. apply an online reverse dictionary transform and a 461-model PAQ/cmix-family
   bit predictor;
6. append compressed dictionary, compressed article-order payload, compressed
   transformed stream, and a header to one self-extracting `archive9`.

The order was generated offline using embeddings, t-SNE, clustering and manual
sorting, but the order itself is embedded in the archive.  The decoder uses no
network or outside dictionary.  The runtime model is specifically enriched with
stemming, word-type contexts, paragraph/sentence word streams, sparse match
contexts, XML/Wikipedia parsing, and a reverse dictionary transform.  Its
source also uses `mmap_to_disk = true` by default to meet RAM limits.  The build
uses clang 17, PGO, LTO, UPX-UCL, and native/selected CPU tuning.

Any CIX work that copies or adapts this implementation must preserve GPL-3.0
terms, notices, attribution, and corresponding-source obligations.  The current
CIX repository has no project license, so it cannot presently package a
derivative submission honestly.  This is a packaging blocker independent of
compression performance.

## Rules that determine design choices

The currently live detailed rules allow enwik9-specific code and explicitly
allow failure on other inputs.  They require canonical 1,000,000,000-byte
enwik9, a self-contained Linux/Windows executable or accepted source-plus-
makefile package, no outside files/network/dictionaries/additional installs,
one CPU core, no GPU, at most 10 GB RAM and 100 GB temporary disk, and time
below 70,000 / Geekbench-5-single-core-score hours for each program.  Required
command/compile option bytes count.  Public documented source under an
OSI-approved licence and a 30-day public review are required for an award.

The detailed rules' phrase "about 116MB" is stale; score calculations must use
the main Prize page's live 110,793,128-byte record.  Official acceptance remains
for the Prize reviewers.

## Implication for CIX

The current CIX Hutter profile is a Python, generic, small-block portfolio with
bounded PPM/context/mixer models.  It has no enwik9 measurement.  It cannot be
treated as a competitive baseline against fx2-cmix: CIX stores per-block framing
and selection metadata and does not have an enwik9 XML/article transform, an
online reverse dictionary, a long-lived 461-model predictor, or a native
single-core decoder.  A full generic CIX run would be evidence, but is not a
plausible route to a 109.7 MB package without a predictor/transform step change.

The concrete target is therefore a Hutter-specific, GPL-compliant native profile
whose primary coder is PAQ-class prediction.  CIX should compete only where it
can reduce *conditional residual* bytes after exactly the same transform and
predictive state.  Applying a second compressor to an already arithmetic-coded
payload is not a candidate: it cannot add information and normally expands it.

## Bounded experiment ladder

All experiments must use the shared heavy-work lock and produce exact
restoration.  Raw canonical prefixes are suitable only for a generic-control
experiment.  An experiment claiming to exercise the winner-style transform
must use a transform-derived fixture described below.  No full entropy-coded run
follows from a promising probe without a recorded stop boundary and resource
plan.

1. **Reference-path reproducibility audit.** Build the pinned fx2 source in an
   isolated checkout only after toolchain approval.  First exercise `-c`/`-n`
   only as a generic small-input smoke control.  Exercise `-e` only after a
   separately bounded full transform path is available; record transformed-stream
   size, archive size, wall time, RSS and scratch.  This establishes a strong
   factual control; it does not become a CIX result.
2. **Reversible XML/article transform harness.** Implement a clean-room,
   separately versioned transform interface: split/restore XML, article boundary
   table, reversible article permutation, and token/word stream extraction.
   First candidate permutation must be wholly derivable from enwik9 during
   compression or serialized in the archive.  Measure transform bytes and
   reversibility before trying a coder.  Do not claim the external embedding
   pipeline is recreated merely by matching a description.
3. **Identical-information residual tournament.** Feed one transformed stream
   and one causal predictor state to (a) arithmetic/range coding and (b) a CIX
   conditional-composition coder.  Account for every composition, candidate-set
   and selector byte.  Accept CIX only when full physical bytes improve over the
   arithmetic control after metadata; otherwise retain the arithmetic stream.
4. **High-value CIX locations.** Test CIX first on structured side streams where
   a known composition can genuinely reduce the state space: article-order
   deltas, dictionary token identifiers, XML field/tag classes, capitalization
   masks, punctuation masks, and prediction exception masks.  Do not begin with
   raw natural-language bytes or post-compressed PAQ output.
5. **Conditional candidate-set coding.** For each position/region, derive a
   candidate alphabet solely from causal model state; encode in-set choice plus
   explicit exceptions.  Benchmark it against the same predictor's range code.
   The required result is measured residual bits lower than the control,
   including candidate-set/model-selection metadata, not a lower entropy estimate.
6. **Only then run a full encode.** Freeze the selected native profile and
   package accounting before one canonical full encode/decode.  The first full
   score is a baseline, not an eligibility claim; follow with resource and
   self-contained-package proof.

## Reference-build and fixture decision

The pinned winner's build is deliberately reproducible only in an environment
with `clang++-17`, `llvm-profdata-17`, `upx-ucl`, and GNU make.  Its prescribed
script first does PGO from `prof_input/input`, then LTO, then UPX compression;
it embeds compressed dictionary and article-order files in `run/cmix`.  On the
current host, `clang++-17`, `llvm-profdata-17`, and `upx`/`upx-ucl` were not
found.  Do not run the upstream installation scripts: they download a toolchain,
use `sudo`, and mutate the host.  No build has been attempted.

When a bounded build is authorized, use a disposable copy outside both CIX and
the pinned reference tree, verify the listed source hashes before and after, and
record compiler, PGO inputs, command line, binary hash, and every produced
payload.  The minimum build sequence is the upstream
`build_and_construct_comp.sh`; its PGO and packaging path must be treated as
part of the experiment, not hidden setup.  A generic `-c`/`-n` Cmix run is not
the winning `-e` profile.

A simple 1 MiB raw prefix is not a representative `-e` transform fixture.  The
winning code hard-codes the complete enwik9 line boundaries (main region ends
at line 13,146,932) and a 243,425-article order.  It first reads and reorders
the complete article region.  Therefore a direct `-e` invocation on a prefix
does not test the actual winner pipeline and could fail or silently measure a
different transform.  The smallest useful same-prediction fixture is instead a
recorded window of the *fully generated* `.ready4cmix` transformed stream,
along with a deterministic causal-state warmup prefix or a serialized model
checkpoint.  A window alone is insufficient for a stateful PAQ predictor.

The practical staged route is: (a) a bounded complete transform-only run, with
no entropy coding, to generate and hash the transformed stream and its side
streams; (b) select a 1--16 MiB window after a documented warmup point; (c)
trace predictor probabilities and actual bits for that exact window; and (d)
run a CIX-versus-range residual tournament from the same predictor state.  The
transform-only stage needs roughly the winner's stated 7 GB of temporary disk,
not a full 110 MB entropy-coded archive, but it still requires the shared lock
and resource receipt.

### Smallest worthwhile CIX feedback experiment

Do not try a block histogram around predicted raw bytes.  A strong byte
predictor is position-specific: an unordered block composition discards the
very ordering information that produces its gain, while transmitting the counts
costs metadata.  The likely viable CIX experiment is a *prediction partition*
on a trace:

1. Partition positions causally by a compact, decoder-reproducible predictor
   state such as predicted byte class, XML/text mode, current word-token state,
   and probability/entropy bucket.
2. Within each partition, encode only the observed exception/symbol composition
   and enumerative rank, with the partition sequence itself derived from the
   same predictor state.
3. Compare the exact payload plus composition metadata against the original
   range-coded bits on the identical trace and state.  Retain only a physical
   byte improvement after framing.

This is the smallest route that can exploit remaining-count deficits as feedback
without erasing context order.  It is still unlikely by itself to save the
required 1,107,932 bytes; a successful result must be amplified across a large,
well-identified transformed substream or paired with a materially stronger
predictor/transform.  The experiment is valuable because a negative result
will rule out the current CIX claim under a strong PAQ information control.

The expected major gains, if any, come from better reversible structure and
prediction.  CIX has a defensible role only when prediction makes the residual
alphabet/composition sharply constrained and the physical enumerative stream
beats range coding under that identical information.  This turns the CIX
hypothesis into a falsifiable test rather than adding metadata to a PAQ model.

## Primary sources

* https://www.hutter1.net/prize/
* https://www.hutter1.net/prize/hrules.htm
* https://www.hutter1.net/prize/hfaq.htm
* https://github.com/kaitz/fx2-cmix/tree/04c5806f99b9b0fa8572be8c8063b4324ec405de
* https://mattmahoney.net/dc/text.html
