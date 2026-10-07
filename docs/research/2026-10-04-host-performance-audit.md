# Read-only host performance and BEST decoder audit

Observed on 2026-10-04, ending around 02:45 UTC, while the frozen Silesia confirmation was running. No host settings, product sources, third-party sources, builds, benchmarks or firmware were changed by this audit. These are passive observations, not a controlled speedup experiment.

## Findings

The host is already configured to request high CPU performance, but maximum sustained performance is not established. There is direct evidence of intermittent thermal throttling and a changing sustained package power limit. The main tuning opportunity is cooling and coherent power management, followed by workload isolation, not simply selecting a performance governor again.

| Item | Observed state | Interpretation |
| --- | --- | --- |
| Platform | Intel NUC13SBBi9, Core i9-13900K, 8 P cores plus 16 E cores, 32 logical CPUs | Hybrid topology matters for placement. |
| Frequency policy | All 32 policies: active intel_pstate, performance governor, performance EPP; no_turbo=0; max_perf_pct=100 | Turbo and maximum-performance requests are already enabled. Idle 800 MHz readings are not a loaded-frequency problem. |
| CIX placement | CPUs 8,10,12,14: four distinct P cores; 8/10 have reported 5.8 GHz caps | Correct physical-core placement, including both favored cores. Four-core budget is intentional, not a server-wide limit. |
| Actual busy frequency | turbostat CPU10 at approximately 99.77% busy: 5257,5257,5225,5308,5235 MHz over five 2-second intervals | Actual busy clock was about 5.23–5.31 GHz in this sample, not the earlier approximate 4.3 GHz sysfs snapshot. This later sample was during Mozilla BEST native encoding, not Dickens PAQ decoding. |
| Temperature and throttling | CPU10/CoreTmp and PkgTmp reached 100 C; CoreThr increased from 133325 to 133422, then 133423 | New throttle events prove intermittent thermal limitation during observation. A separate later 10-second sample had zero new events; throttling was not continuous. Counts do not quantify total lost time. |
| Package power limits | PL1 first 58.5 W; later 55.375 to 56.875 W within 10 seconds, then 60.625 W. PL1 time window 999424 us. PL2 250 W | Sustained limit is dynamic. Package energy delta over the separate 10-second sample averaged 56.52 W. The earlier turbostat intervals averaged about 63–73 W. |
| Policy owners | thermald active with --adaptive. Existing ollama-tuning.service ran at boot, requests PL1=90 W and tau=28 s. ollama-pl1-enforcer.timer disabled/inactive | Runtime limits differ from boot settings. Firmware/thermal management may be adjusting them; this audit did not establish the exact writer. Do not force an enforcer to fight thermal controls. |
| Background placement | ClickHouse and desktop processes sampled on CIX P cores; their reported lifetime CPU averages are not interval interference measurements | CIX affinity does not reserve cores from other host work or their SMT siblings. Isolation could improve consistency; benefit is unmeasured. |
| Memory | 64 GB installed, two 32 GB DDR5 modules rated and configured at 4800 MT/s; ample available host memory | No demonstrated free XMP speed increase: modules already run at their reported rating. Single NUMA node. |
| Memory policy | THP=madvise, swappiness=10, MGLRU=0x0007, KSM scanning off; benchmark MemorySwapMax=0 | No evidence here that changing these would help. Do not blindly enable global huge pages or change allocator policy. |
| Firmware | SBRPL579.0058.2023.0817.1457; CPU microcode 0x133 | BIOS review is justified: ASUS lists SBRPL579.0068 for this board family. This is not a finding that the loaded microcode is outdated. |

## Recommended order after the frozen pass

1. Inspect cooling and supported fan/performance profiles, airflow and fan operation. Thermal throttling at the observed package power warrants checking the actual cooling state. Fan-state sysfs entries are not RPM or proof of maximum effective cooling.
2. Review the board-specific current BIOS and release notes and plan any supported update for maintenance. Do not flash or reboot during confirmation.
3. Reconcile the existing Ollama boot tuning with firmware/thermald under one documented policy. Establish a sustainable thermal envelope before increasing sustained power. CPU nominal 125 W base / 253 W maximum turbo specifications are not a command to force this NUC to those limits.
4. Reserve benchmark physical cores and their SMT siblings from unrelated workloads where practical, and route background work/eligible interrupts elsewhere. Preserve the explicit four-physical-core CIX budget.
5. Capture busy MHz, package watts, temperatures and throttle deltas with future qualification metadata. Demonstrate any performance gain with bounded evidence before advertising it. No uncontrolled source changes or repeated full benchmark tournament are implied.

The advertised 5.8 GHz is an opportunistic maximum, not a guaranteed sustained all-core clock. Kernel and manufacturer references:

- [Intel i9-13900K specifications](https://www.intel.com/content/www/us/en/products/sku/230496/intel-core-i913900k-processor-36m-cache-up-to-5-80-ghz/specifications.html)
- [Intel Thermal Velocity Boost conditions](https://www.intel.com/content/www/us/en/support/articles/000097061/processors.html)
- [Linux intel_pstate performance policy](https://www.kernel.org/doc/html/latest/admin-guide/pm/intel_pstate.html)
- [ASUS board-family BIOS downloads](https://www.asus.com/us/displays-desktops/nucs/nuc-kits/nuc-13-extreme-kit/helpdesk_bios?model2Name=NUC-13-Extreme-Kit)

## BEST decode and single-executable clarification

Dickens BEST is VERIFIED. Original size 10,192,446 bytes; archive 1,862,182 bytes. Independent decode took 1965.579 seconds, consumed 1965.398 CPU seconds and peaked at 3,917,266,944 bytes aggregate cgroup memory. Its cgroup recorded zero CPU-quota throttling. This does not establish absence of hardware thermal throttling during that entire historical decode.

The selected candidate was PAQ v215 -9L. Its individual encode took 1940.344 seconds; the full CIX candidate search took 3656.663 seconds. The decoder only executes the selected codec, not a repeated selection tournament. PAQ's decoder predicts and updates adaptive state for every bit and replays online LSTM learning. The sequential model state explains roughly one-core execution and similar encode/decode costs. No detailed profiler measured the percentage attributable specifically to LSTM.

The staged bin/cix is currently a shell launcher into bundled Python cix_runtime.cli. CIX's engine selects among native CIX, generic PAQ, specialized and mixed-region candidates. backends.py wraps the PAQ stream using CIXP framing and launches libexec/cix/paq8px-v215 to decode it. Therefore this winner is PAQ compression selected/framed by CIX, not a CIX-native coding gain. Candidate native-best produced 2,142,982 bytes on this file; removing PAQ would sacrifice the demonstrated smaller output.

User clarification, communicated to the implementation agent: **one CIX executable is required; integrated codec libraries are acceptable**. Keep successful third-party algorithms with honest attribution, but remove the separate-executable packaging dependency through CIX-owned integration. Renaming or hiding PAQ is not integration. Existing frozen evidence remains about the existing build; future executable packaging needs appropriate equivalence/correctness verification. External/vendor source edits remain prohibited.

Evidence: `2026-10-04-automatic-specialised-models/qualification/silesia-confirmation-v1/results/confirm-best-dickens/result.json` and `selection-report.json`; maintained `runtime/cix_runtime/backends.py` lines 113–160; `engine.py` lines 46–57,349–361,410–411; upstream PAQ v215 `src/Encoder.cpp` lines 39–67 and LSTM implementation. No changes were made to those files.
