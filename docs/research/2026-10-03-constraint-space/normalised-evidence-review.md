# Independent evidence review: RNC1 shared model fee

**Reviewed:** 2026-10-03  
**Scope:** frozen source and runner bindings, 45 normalized frames, native
fresh-process restoration, common-space assertions, surplus arithmetic, five
malformed cases, retained artifact hashes and resource receipts. No build,
codec or benchmark was rerun for this review.

## Verdict

No result-correctness blocker was found. The executed packet supports the
predicted distinction:

1. EC has a real rank/state-space reduction against its individual E and C
   components on the frozen strong inputs.
2. EC and RDIC use the identical vocabulary and identical sequence-rank bytes
   on those inputs. Once both receive the same 256-byte model allowance and
   common outer framing, they tie exactly.
3. The original 12-byte `dev-eight` and 59-byte `held-ten` advantages over
   RDIC are therefore entirely model-description savings. They are not a rank
   advantage over a direct code for the same set.

The result is a diagnostic over an artificial fixed model fee. It is not a new
compressor, a new theory, or a replacement size ranking for the original
archives.

## Frozen identity and execution

The executed source snapshot is byte-identical to the current RNC1 source:

| Item | SHA-256 |
|---|---|
| RNC1 source and executed source | `a7d60f029853c19eceabd8f28627088f54cb2e22de3307d10d9f9eea34807fdf` |
| Corrected runner | `0f9a3dea36dff91518bef95a5756803ee8d4c2273650cadd318cee22ac98f61b` |
| Scheduler | `3b0aa2829fa18a652c6e644f9c2a8773354317d0b6f3bfe4395b34faef6efb33` |
| Built RNC1 binary | `6895c43b6f778b72a85b26bf2b24615104fb5f1c1bd264ee5ef8b05d8c4b2936` |
| Results | `a8dc215fb711bbe9495c39fcccb0404553c86e9acbc024ac54a69d78b554a5eb` |
| Artifact binding | `9ed1b00f442d1ac7698d3b334d04c348043694ed881791b93830004da6ba3d4a` |
| Malformed results | `00253c09d0de1d61f1e087f708768a0f113005d9671b015e21ff0abb0167f7db` |

The freeze also binds the prior record results and artifact map, the exact ERC1
and RDIC decoder binaries, and the two BigUint dependency artifacts. The main
runner rehashes each original inner archive against that prior binding before
using it.

The build and comparison phases both exited zero in actual child cgroups. Both
record CPU8, `cpu.max=100000 100000`, a 2 GiB memory limit and zero swap. The
comparison took 0.487 seconds elapsed and 0.289 cgroup CPU seconds, with
22,876,160 bytes sampled memory high-water and 5,473,042 bytes peak monitored
temporary footprint. These measurements only qualify the bounded adapter
check; they are not codec performance comparisons.

## Physical archive and restoration read-back

The result contains 45 successful complete frames:

* 35 across the five strong fixtures: Raw, E, C, EC, Auto, RDIC and Uniform;
* four on `weak-six`: Raw, Auto, RDIC and Uniform;
* three each on `absent` and `empty`: Raw, Auto and RDIC.

Every frame was unpacked in a separate RNC1 process. The 39 frames wrapping an
existing inner archive reproduce that frozen archive byte-for-byte. Every
reconstructed or newly generated inner archive was then decoded in a separate
native ERC1 or RDIC process, and all 45 restored digests equal the frozen input
digest.

A read-only rehash of all 140 retained artifact-binding entries found no
missing file, byte-length mismatch or digest mismatch. These entries comprise
45 RNC1 frames, 45 inner archives, 45 restorations and five malformed frames.
Independent read-back also confirmed every successful frame has a valid outer
CRC and exact length `270 + payload_bytes`.

## Exact same-space control

For every strong input, the runner verifies that EC and RDIC have the same
source length, record width and alphabet. It reconstructs EC's admissible local
vocabulary, independently derives the observed RDIC vocabulary from the
source, and requires the two ascending lists to be equal. It then compares the
physical sequence-rank bytes in the two RNC1 frames and requires exact byte
identity.

The common frame moves all ERC metadata or the RDIC header plus combinadic
dictionary rank into the same 256-byte area. Both then pay 14 bytes of outer
header/CRC. Because their sequence payloads are identical, all five strong
pairs tie:

| Input | EC normalized bytes | RDIC normalized bytes | Difference |
|---|---:|---:|---:|
| dev-six | 1,038 | 1,038 | 0 |
| dev-eight | 1,213 | 1,213 | 0 |
| dev-four | 654 | 654 | 0 |
| held-six | 942 | 942 | 0 |
| held-ten | 1,360 | 1,360 | 0 |

This is the predicted same-space equality. The fixed 256-byte area is a
control variable and deliberately inefficient padding; these normalized sizes
must not replace the original complete archive results.

## Intersection proof and uniform control

The corrected runner resolves the preflight cross-width concern. It parses the
selected E, C and EC headers, requires common length and alphabet, and requires
the E and C record widths to divide EC's common block. It enumerates E and C
over that common block, intersects those tables, and requires exact equality
with EC's admissible table. It also verifies that each lifted component
cardinality produces the component archive's whole-sequence rank width.

This proves all five reported EC rows are the actual intersections of the
selected component models. In particular, on `dev-four`, repeating E's
width-2 mask 1 across a width-4 block yields mask 5, so the differing selected
width is handled rather than assumed.

The native Uniform route stores the sorted two-symbol alphabet and a dense
`n`-bit rank over all `2^n` source sequences. The runner independently folds
the source symbols into the stored integer, verifies physical payload length,
unpacks the frame and fresh-decodes it with ERC1. This supplies the correct
uniform-universe term; ERC Raw's literal-byte payload would not.

For the two original strict-win rows, the exact integer and byte-rounded
surpluses are:

| Input | E bits | C bits | U bits | EC bits | Surplus bits | Surplus bytes |
|---|---:|---:|---:|---:|---:|---:|
| dev-eight | 10,752 | 9,415 | 12,288 | 7,537 | 342 | 42 |
| held-ten | 11,520 | 10,211 | 12,800 | 8,714 | 217 | 27 |

Here surplus is `E + C - U - EC`. Its positive value establishes interaction
relative to the same binary universe after exact bit-width and physical-byte
rounding. Separately, EC saves 1,878 rank bits over the better component on
`dev-eight` and 1,497 bits on `held-ten`. These facts coexist with the zero-byte
normalized difference against RDIC because RDIC represents the same joint set.

The other strong rows are retained: `dev-six` and `held-six` also have positive
surplus while tying RDIC in their original formats; `dev-four` has negative
surplus and originally loses four bytes to RDIC. No selection or theory claim
may retain only the positive rows.

## Malformed cases and limits

Five malformed frames reject with nonzero status and no output: truncation,
outer CRC corruption, nonzero canonical model padding, invalid codec, and a
CRC-resealed false payload length. These directly cover the outer format's key
boundaries. They do not amount to fuzzing or exhaustive hostile-input coverage.
The native decoders' earlier semantic malformed controls remain separate; RNC1
unpack still relies on the downstream native decoder for full inner semantic
validation.

Uniform is deliberately unavailable for empty, odd-length or non-binary input.
The measured positive rows are small synthetic binary-record fixtures from one
generator family. The experiment does not establish real-data effectiveness,
large-scale behavior, streaming, or a production integration case.

Subject to final packet manifest sealing, the evidence supports the stated
rank-versus-model-cost distinction without a new compression-win claim.
