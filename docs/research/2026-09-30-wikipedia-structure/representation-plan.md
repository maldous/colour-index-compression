# Wikipedia structure representations C and D

This bounded Hutter research does not reuse the prior input-derived markup tag
dictionary/column transform.  It does not use FX2/CMIX's full-corpus article
reorder: that transform requires canonical enwik9 plus a supplied global article
order and is not valid for regional snippets.

Every representation produces one compact self-contained `HSTR1` frame before
entropy coding.  Frame descriptors, skeleton dictionaries, record order,
literal bytes, values, lengths and escapes all count.  Decoding needs only the
frame.  There are no files-per-field, external models or hidden XML parser
state.  Exact byte reconstruction includes whitespace, entities, numeric
spelling, ordering and malformed material.

* `control`: one literal stream in an `HSTR1` frame.
* `C`: a lexical typed-stream frame.  A compact ordered descriptor identifies
  raw XML-like tag tokens and every intervening raw text span; tag and text
  streams are concatenated.  Unmatched/malformed input remains text raw bytes.
* `D`: only complete byte spans from `<page>` through `</page>` participate.
  Their exact tag/placeholder skeletons are shared in an in-frame dictionary;
  every text value is length-prefixed in page order.  All data outside complete
  page spans, including leading/trailing truncated regions, is one literal
  stream.  This is distinct from a lexical tag dictionary because it shares a
  page/revision relationship skeleton and transmits only per-occurrence values.

The first test is one deterministic synthetic page pair and the fixed 32 KiB
development ranges at enwik9 offsets 0, 100,000,000 and 400,000,000.  The
strong-backend wrapper, owned separately, must feed the complete physical frame
to pinned PAQ v216 `-4` for all three modes and decode the PAQ payload before
calling this frame decoder.  It must charge the full frame and backend archive
with identical filenames/control treatment.  A test has a 300-second total
budget, single logical CPU chosen from an explicit four-CPU allocation, 3 GiB
RAM, swap disabled and 1 GiB temporary disk.  No offsets 600,000,000 or
900,000,000 may be read until a predeclared development gate is met.
