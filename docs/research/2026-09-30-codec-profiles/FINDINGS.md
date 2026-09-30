# Completed settings screening

90 settings cells completed; each retained three encode/decode repetitions,
one warmup per phase, GNU time logs, peak RSS, min/max/MAD and independent
archive-only decoding. All 270 measured restored streams passed SHA-256 and
full byte equality. Six PAQ absolute-maximum cells are explicitly resource-
limited and were not launched. Settings, binaries and commands are pinned.

All inputs are previously exposed 16 KiB slices. No whole-corpus performance,
steady-state throughput or global optimum follows from this screen. The
old current references retain their one-repetition measurements; new settings
results use three. Python wrapper startup and backend startup are included.
CIX fast/maximum, gzip 1/9, bzip2 1/9, XZ 0/9e, Brotli 0/11 and Zstd
--fast=131072/--ultra -22 were measured. PAQ v216 -1 and existing-policy -8
were measured; -12L with five LSTM layers exceeds the 12 GB aggregate cap.

Higher effort is not guaranteed to improve every input. CIX maximum returns
the same physical size as balanced on these six slices, while spending about
4.4–5.4 seconds encoding (a failed expensive mixture probe is included).
Fast CIX improves the measured time, but its MSG archive increases to
14,832 bytes versus balanced/maximum 12,746. XZ 9e achieves 12,684 bytes on
that slice. PAQ -8 achieves 11,348, so CIX no longer leads the fully covered
current-settings comparison. PT CIX remains 12,749 bytes and leads the six
measured size-preset codecs; the unmeasured PAQ absolute maximum prevents a
seven-method maximum-size claim. No settings search claims a universal optimum.

Private research source and all old evidence remain intact. Public disclosure
is limited to the explicitly requested benchmark Site and its result downloads.
No downloads, full corpus runs or Actions occurred.
