# Applied Node binding style cleanup v1

The Node-only Sonar probe removed all three parser recoveries and reported 37
remaining issues. This cleanup is deliberately limited to the 26
`cxx:TooManyStatementsPerLine` locations: 41, 65, 75, 76, 79, 81, 84, 107,
118, 137, 138, 149, 152, 175, 189, 203, 218, 251, 256, 262, 275, 284, 320,
331, 341, and 343. It expands compact error paths into braces and separate
statements, preserving return values, N-API calls, and every ABI symbol.

It does **not** rename `cix_context`, `uint64_t`, or Node's generated
`node_api_module_get_api_version_v1`; those are external ABI/upstream names.
It does not add a file header merely for the analyzer. Complexity findings for
`options`, `buffer_op`, `stream_new`, and `stream_call` need a separately
reviewed behavioral decomposition, so they are outside this formatting patch.

Validation after applying the patch: run the retained Node contract build and
`node test/contract.js` using the current qualified Node SDK/header closure,
then rerun the one-TU Node analyzer probe with the same captured
`__attribute__(...)=` normalization. Verify the public `Context`, `Encoder`,
`Decoder`, `encode`, `decode`, stream methods, type-tag rejection, disposal,
and cancellation behavior remain unchanged.

## Applied-source identity

The reviewed patch was applied without modification. The canonical source
changed from `2556b1c33b93ce7bc4d15ac95b1449c6e35dfae56158f909172af33d1adff35b`
to `879490bd7b3918121d678b4bb637b8246a6b19a501bc1a43e7de9b45558a1372`.
The diff is 69 insertions and 23 deletions, all control-flow layout only.
