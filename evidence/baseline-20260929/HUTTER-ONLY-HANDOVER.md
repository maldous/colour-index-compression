# Hutter-only mission handover

User decision, 29 September 2026: only the Hutter Prize is now the goal;
previous Silesia optimisation and broad external evidence publication stop.
This baseline remains incomplete and must not be presented as a publication.

The finite boundary watcher `cix-stop-baseline-for-hutter-20260929.service`
waits for the current D1/xml PAQ8px measured repetition 1 encode/decode to
finalize and release the exclusive measurement lock. It then stops
`cix-evidence-baseline-20260929.service`; no measured atomic phase is killed.
The receipt is `raw/hutter-only-baseline-stop-20260929.json`. At this handover
it records WAITING FOR ATOMIC BENCHMARK. Read the live receipt/service to
establish completion; do not infer it from this document.

The frozen codec remains f26d32836c15cb1a5e37ebfddd5826c4b33ff8a6.
Preparation/evidence commits and raw logs remain preserved. No new publication
tag or separate evidence Site exists. No completed full Wikipedia, full NNLCB,
or 10 GiB comparison is claimed. Modern 20260901 XML and NNLCB inputs remain
available; none was deleted merely because priorities changed.

Hutter research uses canonical enwik9, not the modern full dump. The research
repository AGENTS and 2026-09-29 handover govern the new work. A complete CIX
enwik9 score is not yet measured. The existing research Site now foregrounds
Hutter status and retains Silesia as historical evidence.

The separate current goal explicitly authorizes local Hutter R&D and accurate
Site updates. GitHub Actions remains forbidden. Storage monitoring and verified
disposable-artifact cleanup remain in force. Do not resume this baseline queue
automatically on a later session.
