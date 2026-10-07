CIX-135 native relocated-pointer source candidate (ECRP1 / CIXB binary 0a)

SOURCE ONLY: Rust syntax parses passed. Rust type/link compilation, nine new
native test groups and physical Brotli/PAQ archive tests have NOT RUN.
The 12 immutable raw reference fixtures were independently accepted in CIX134;
that acceptance does not transfer to this newly written native implementation.

Exactly three existing modules plus one new test file are changed. Preimages,
postimages and exact unified patch are retained here. Candidate values still
come only from the input's symbol tables. The relocated-pointer model now keeps
the undefined-symbol context, all six representations and local/shared flag.
The nested GOT parent intentionally always uses its original shared-symbol
mode. Existing GOT choice coders are reused; ECRD1 remains a distinct route.

CIXB binary0a is recognized and dispatched through actual native backend paths.
A PAQ/Brotli pair for mode5/sharedtrue is appended after existing address
candidates; previous relative order and generic fallback are retained. This is
retained-route coverage, not a current compression improvement or record.

The shared trailer parser additionally rejects metadata below its required
minimum and checks addition of the13-byte trailer. This narrow malformed-input
repair is needed before ECRP1 can safely inspect model bytes; valid historical
trailer formats remain unchanged. All existing test functions remain present.

Nine authored test groups cover12 raw goldens, shared rescue/literal escapes,
empty input/admission, malformed lengths/tags/membership/choices/exceptions,
nonzero skeleton/invalid index,24 callback framing cases, resource/CRC checks,
and deterministic filename-independent catalogue admission/order. Synthetic
fixture offsets occur only in tests. Callback payloads are UNIT framing proof
only, not physical archive streams. The existing installed-provider smoke test
also includes the added PAQ route, but it has NOT RUN for this source.

32 read-only input/fixture/reference bindings remain unchanged. Cargo/service,
policy, dependency lock and unrelated peer files are outside this change.
Claim f335fd78-59db-4ebc-b91a-9fa1b965e000, exact source contract64d4a96d,
childCIX135. Root releases the source lease after freezing this candidate;
Quinn independently reviews the exact patch. Native/source/provider-qualified
execution and archive-only crossdecode need a separate bounded admission.
