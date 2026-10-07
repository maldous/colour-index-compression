# Bounded reader allocation audit

Lineage: `013af2243` introduced the audit-only tool; `41d397b15` retained an
initial cgroup run; `ccb7544e6` added child self-readbacks and direct binary
execution. This packet supersedes earlier diagnostic observations.
It compares only source buffering: the legacy exact `Vec::with_capacity(128 MiB)`
plus `read_to_end` and the new bounded reader. Input generation occurs before
DHAT starts. It invokes no native compression library and reports no RSS or
throughput result.

The actual command was the retained `run-cgroup.sh`, invoked as:

```sh
sudo -n systemd-run --wait --pipe --property=User=user --property=MemoryMax=1G \
  --property=MemorySwapMax=0 --property=CPUAffinity=10 --property=AllowedCPUs=10 \
  --property=RuntimeMaxSec=180 /bin/bash /ABS/run-cgroup.sh
```

Final tool source SHA-256: `8b9b95f3fc729ec61e4ac7f53dfbb9a82a4ddc090fa0de55b9bc2cea82938f1f`.
Final built binary SHA-256: `6df6fa7df445433f28ec1ad6212862beaee2519e4dbe364068f6257b031d3b48`.
Rust was 1.98.1 (`48a229cea`), LLVM 22.1.8; Cargo was 1.98.1.

## Status

Qualified allocation run: systemd unit `run-u20337.service`, invocation
`aa8b141164b64aba9baf82cf31e5f784`, had `MemoryMax=1G`,
`MemorySwapMax=0`, CPU 10 affinity, and a 180 second limit. In-cgroup
readbacks and all eight raw DHAT JSON/log pairs are in `raw/`. Every child log
starts with its own cgroup, memory, swap, and CPU-affinity readback before
DHAT starts; it reports `/system.slice/run-u20337.service`, 1 GiB, swap 0,
and CPU 10. Host swap is irrelevant to this cgroup-scoped result.

The child resource line is plain text, not JSON, and is emitted before DHAT
starts. Returned-capacity/equality JSON and DHAT output follow. Source bytes
and pre-profiler initialization are outside the DHAT scope.

## Reader-only measurements

| Source bytes | Old returned capacity | New returned capacity | New total allocated bytes | New allocation events |
|---:|---:|---:|---:|---:|
| 0 | 134,217,728 | 65,536 | 65,536 | 1 |
| 2,048 | 134,217,728 | 65,536 | 65,536 | 1 |
| 65,537 | 134,217,728 | 131,072 | 196,608 | 2 |
| 1,048,576 | 134,217,728 | 1,048,576 | 2,031,616 | 5 |

Old total allocated bytes are 134,217,728 in one event in every case.
Growth increases event count; the final source capacity and total requested
allocation both fall on these inputs. This is not an end-to-end codec result.
Only the final child-bound run is qualified; earlier parent-only or
host-swap-based diagnostic observations are superseded by this run.
