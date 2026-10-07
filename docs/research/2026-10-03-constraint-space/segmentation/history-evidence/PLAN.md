# Stage 4: position-determined decoded-prefix history

Stage2/3 completed before this stage. Freeze H=0/1024, same four routes and
boundary policy; no persistent adaptive state, paid template caches or tuning.
NSCHv1 charges 19 bytes global header (including H) plus 9 bytes each segment
and actual payload. HUF/raw/reset order0 adaptive unchanged; legacy LZ receives
last H original prefix bytes. Decoder consumes its exact reconstructed suffix,
including raw regions. The history-proof.md explains why costs remain additive.

Reuse 25 frozen stage2/3 inputs and archived controls with rehashed bindings.
Small nine: both histories adaptive and all-cut reference (tiny exhaustive when
<=12). Medium16: H0adaptive; H1024whole/adaptive/fixed256/fixed1024. Prior held
inputs are already exposed by the preceding stage; this is a controlled
mechanism comparison, not a newly untouched holdout or broad generalisation.
Fresh-process decode SHA and independent measured-edge partition DP; test
history limit, lengths, route, CRC and truncation. Altered-H compatibility
probes are run on all fixed256 medium archives: accept exact restoration or
reject a genuinely dependent payload; do not assume every LZ uses history.
No new production or acquisition. Root scheduler CPU8quota1/2GiB/no swap/
64MiB, build120/batch240, each child120. One observation, no averages.
