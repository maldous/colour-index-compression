# RC07 review: native override scope versus automatic discovery

## Current behavior

`NativePortfolioConstraints::constrains_wire()` returns true when *any* of
`formats`, `blocks`, or `backend` is set. `selection::plans()` uses that one
predicate twice: it removes raw, then records every PAQ and specialist/mixed
candidate as `ProfileOmitted` and returns before `catalogue::catalog()`.

That is correct only for `formats`: `--format cixg1|cixg2|cixm6` asks for a
specific whole-container wire format. A catalogue recipe, PAQ frame, raw
carrier, or CIXH1 mixed carrier cannot satisfy such a request.

`--block-size` and `--backend` are native portfolio tuning dimensions. The
native portfolio already applies both: `block_list()` uses the supplied block
list and `allows()` excludes CIXM6 or CIXG1 routes that cannot carry the
requested nested backend. They do not make a specialist recipe, PAQ archive,
raw carrier, or mixed carrier falsely claim that it used a requested native
nested backend; those candidates simply have no such parameter. Treating them
as a global wire constraint silently suppresses otherwise automatic dimensions.

The CLI help describes the controls as constraining their specified dimensions,
and its existing explicit-format checks already distinguish a container choice
from backend/block tuning. The historical LSTM route is already `paq-v215-9L`;
no separate transform is missing here.

## Smallest patch

1. Replace `constrains_wire()` with `forces_native_container()` returning only
   `self.formats.is_some()`.
2. In `selection::plans()`, use that predicate for the raw exclusion and the
   early native-only return. Do not change native portfolio validation,
   `block_list()`, or `allows()`.
3. Keep the existing forced-format omissions, but make their reason specific:
   `explicit --format native container constraint excludes incompatible wire`.
   No omission is produced merely because a block or backend tuning constraint
   is present.
4. Continue to attach the full native constraints only to `PlanKind::Native`.
   Other plans must not report a native backend/block setting as having been
   applied. Their normal diagnostic/selection record remains the evidence that
   they are independent automatic candidates.

This changes no encoder wire bytes and does not admit a specialist when a
container is explicitly forced. It only restores discovery where the override
does not name a whole-container wire.

## Focused tests

Add selection tests using a catalogue-recognized fixture and providers that
allow the generic mixed carrier:

* `formats = Some(["cixg1"])`: no catalogue/mixed plan is admitted; each
  incompatible candidate has the explicit-format `ProfileOmitted` reason.
* `blocks = Some([16384])`: the native plan receives that block list, while
  catalogue diagnostics are populated and the compatible specialist/mixed
  candidate is still considered. No `ProfileOmitted` reason may say an
  explicit native container constraint.
* `backend = Some("deflate")`: native CIXG candidates using that backend are
  considered; CIXM6 reports its existing supported/unsupported backend reason;
  catalogue/mixed discovery still occurs and retained candidates do not claim
  to use deflate.
* `backend = Some("huffman")`: verify CIXG1/CIXM6 incompatibility is reported
  by the native portfolio while an unrelated automatic candidate remains
  discoverable.

The last two cases distinguish a **supported native candidate** from an
**unsupported native route** without treating an unrelated candidate as either
silently configured or globally forbidden.
