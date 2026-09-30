# Track A frozen feedback scale check

The paid composition-feedback codec validated on 64 KiB development and holdout
regions is frozen. The first scale check is the contiguous 1,048,576-byte
enwik9 development interval at offset 0. It compares the unchanged causal range
control with the unchanged paid-count feedback range codec. No warm-up, source
adaptation or setting change is permitted.

The run has a 300-second hard tree limit on logical CPU 2, 2 GiB RAM, zero swap
and 1 GiB temporary disk. Both complete physical streams must independently
decode and SHA-match. If feedback is smaller and the observed 1 MiB runtime
makes an 8 MiB run feasible in a separately bounded 300-second run, the next
trial is contiguous 8 MiB at the same offset under the same frozen configuration.
No previously consumed holdout data participates in this decision.
