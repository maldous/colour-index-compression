# Evidence challenge log

Status: preparation review, not the final publication approval.

## Controls already exercised

- All eight compressor interfaces completed a small physical encode/decode in
  the isolated harness and restored the expected SHA-256. These are plumbing
  checks, explicitly excluded from benchmark results. The newest scratch policy
  uses NVMe-backed temporary files for every tool.
- A decoder namespace probe could see the archive, an empty private temporary
  directory and the initially empty GNU time output file. It could not see the
  original corpus/research paths and had no external network route.
- The frozen source rebuilt all seven native dependencies with identical binary
  hashes. Python libraries were copied to an independent environment and compared
  byte-for-byte, including symlinks and the interpreter identity.
- `competitive_cli` passes input **bytes** to `codec.encode` and supplies no cache
  arguments. The ordinary portfolio additions compute candidates from those
  bytes. Separate research qualification helpers can read prior frames; they are
  not invoked by this CLI. Their existence is disclosed rather than removed from
  the frozen source. The CLI's complete internal decode is included in CT.
- The base PAQ wrapper identifies the backend version and counts the actual
  wrapped payload. PAQ prediction is attributed as reused code, not represented
  as a newly invented CIX predictor.
- Unit checks reject mismatched hashes and incomplete repetition schedules.
  A killed resource logger cannot change TIMEOUT into a nominal successful run.
  Failed warm-ups and explicitly skipped later repetitions remain visible.
- Independent arithmetic checks reconcile all 481 published CS/CR pairs with
  binary MiB within a rounding-or-truncation interval. Original reference values
  have not been changed. The published CRP/aggregate discrepancies remain open.

These checks do not yet establish performance, full-input correctness or complete
NNLCB qualification. Static import inspection is conservative; it includes
research-only branches and is not a formal proof of every execution path.

## Disclosures required in the eventual report

CIX was developed with knowledge of Silesia. It contains existing format and
structural detectors, size thresholds and PAQ-backed alternatives. This baseline
freezes that implementation; it is not evidence of blind development or of a
format-agnostic universal advantage. No new source-specific code may be added
during the benchmark. Modern Wikipedia, synthetic inputs and other NNLCB classes
must be reported even if they regress or cannot complete.

NNLCB's published results belong to its authors and experimental platform. Our
imports preserve those claims; they are not our independent hash verification.
The authors' archived issue #2 discusses reproduction fixes for TRACE and PAC.
That discussion is relevant to any later local reproduction of those tools; it
does not justify changing their published reference numbers or claiming that
all their reported results failed.

## Gates still open

- Finish and preserve the remaining atomic research runs before controlled timing.
- Complete and hash the full Wikipedia input.
- Resolve the remaining exact NNLCB byte representations where public evidence
  permits; keep all unresolved cases explicitly unqualified.
- Run the frozen full-data schedule, including actual 10 GiB scaling runs.
- Check every reported restoration, repetition, total, unit and throughput from
  raw files. Check incompressible input overhead and all sidecar/accounting paths.
- Separate published-hardware reference tables from same-machine measurements.
- Generate and challenge the final report, raw downloads and all 532 NNLCB cells.
- Commit, tag, archive and publish the separate evidence Site. Until then the
  baseline is incomplete. The user subsequently authorized a separate parallel
  R&D agent; the frozen baseline remains unchanged and shared heavy compute is
  serialized. This supersedes the earlier pause-until-publication condition only
  for that research lane.
