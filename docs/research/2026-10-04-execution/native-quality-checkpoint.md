# Native release-source quality checkpoint

The benchmark remains held until RC51. These are source and correctness checks, not compression records or a release-ready declaration.

The current source uses a shared explicit-path dynamic-library loader for Unix and Windows interfaces, bounded non-Unix stdin handling, and a default 6 GiB accounted-memory budget for BEST and decoding. Explicit memory limits retain priority. The memory budget is not a universal process RSS guarantee. Native Windows/macOS execution remains unqualified.

Clippy remediation adds API safety documentation and simplifies checked arithmetic, array handling, borrowed parameter groups and test imports. Proven unused helpers were removed while historical decoder tables and paths were retained. The independent semantic review is in [native-quality-semantics-v1](reviews/native-quality-semantics-v1.md).

[native-quality-v10](jobs/native-quality-v10/receipt.json) passed formatting and all-target Clippy with Rust warnings denied. The unchanged external C/C++ compiler warnings are recorded separately and are not represented as clean.

[native-regression-v2](jobs/native-regression-v2/receipt.json) ran all 288 library tests: 286 passed and two failed. One failure identified filtered address encoding requesting PAQ v216 level zero, which the isolated worker correctly rejects. The retained reference contract uses level eight, now restored while preserving store-state decoding. Worker failures now include their bounded captured stderr. The other failure was a test race: overlap and completion order are now checked with a bounded two-party readiness condition. Neither vendor source nor production scheduler semantics changed.

[native-regression-v3](jobs/native-regression-v3/receipt.json) passed fresh formatting, all-target Clippy, binary builds, both corrected library tests, six PAQ supervisor tests, and 87 previously pending integration tests. The installed dispatch test exercised actual PAQ/JXL providers including filtered modes 0, 1 and 2. Earlier v2 passed library results remain scoped predecessor evidence; the whole 288-test suite was not repeated after the two fixes. Source and provider hashes are retained in each receipt.

The v3 job used four physical CPUs, a 12 GB memory ceiling, no swap, and a total 4 GB temporary allocation: 3,936,000,000 bytes monitored by the scheduler plus 64,000,000 bytes reserved and independently monitored for the private PAQ test root. Temporary-cap figures and memory samples are not precision benchmark measurements.

Next: complete current-source CXX analysis, remaining shipping-language analysis, final distribution build/package qualification and platform evidence before the release gate.
