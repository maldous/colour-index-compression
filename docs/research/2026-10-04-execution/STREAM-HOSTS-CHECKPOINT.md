# Native streams and host qualification checkpoint

Implementation continues after `43090aba95429286daa9e8106a53df60fbd80c0b`. The release is not ready; RC51 has not been accepted and benchmarking/publication remain held. Every size or timing here describes engineering fixtures and qualification jobs, never a compression record.

| Job | Outcome | Actual scope |
| --- | --- | --- |
| `windows-jobs-mixed-v5` | passed | All-target compile and45 focused tests, including legacy v1 protocol, actual windowed encode/fresh-process restore, failed-cap atomic staging cleanup, mixed trial overlap and serial archive equivalence. |
| `window-v6` | passed | Full-engine independent CIXW1: all-target compile; window library, job protocol, seven transport and three ordinary CLI tests. |
| `concurrency-v1` | passed | Native CIXG/M6 trial scheduling: bounded overlap, canonical completion order, per-wave memory lifetime, cancellation and serial byte-equivalence; selection/mixed/window/job regressions. |
| `portable-wasm-v1` | passed | 16 portable library tests, locked wasm release, Node streaming, bidirectional native CIXG1 subset exact cross-decode. |
| `codec-hosts-v3` | partial | Blosc2 actual 3.3.2 SDK codec round trip/raw fallback/bounds passed; Squash contract failed, preserved. |
| `codec-hosts-v7` | partial | Actual WiredTiger11.3.1 database lifecycle/counters/fallback/bounds passed; Squash test lifecycle assertion failed, preserved. |
| `codec-hosts-v8` | passed | Actual Squash0.8 plugin buffer, stream and custom splice contracts passed; no CAN_FLUSH claim. |
| `consumer-hosts-v2` | partial | HTTP expanded standard coding and cap/negotiation contracts passed. 7Zip and browser fixture failures preserved. |
| `consumer-hosts-v3` | passed | 7Zip26.03 real host clean-stage create/fresh-process restore/exact SHA/no-codec rejection; adapter properties/partial IO/cap/cancel contracts. Chrome151 actual portable WASM stream checks. |
| `grpc-host-v2` | passed | Actual protoc27.3 and Go generators, gRPC1.67.1/Protobuf1.34.2; all gzip/Brotli/Zstd request-response coding pairs, transport/service limits, metadata, malformed input and cancellation. |
| `jvm-http-hosts-v3` | passed | Actual Hadoop Common3.4.1/JDK21 release17 JNI lifecycle and stream contracts; HTTP API tests. |
| `rocksdb-host-v2` | passed | RocksDB10.10.1 no-RTTI actual database flush/reopen/exact custom/raw blocks, callback counters, malformed/declared-size caps and missing-manager rejection. |
| `squashfs-host-v2` | partial | ASAN+UBSAN profile C contract, native C contract,1545 native Rust exact-choice cases and experimental tools build passed. Upstream unsquashfs -s status path failed before extraction; not proof of image corruption. |
| `squashfs-host-v3` | passed | Pinned experimental tools restored304 files/data/metadata/fragments/sparse+xattrs exactly; unknown method and malformed inode profile version rejected. |
| `stream-storage-hosts-v1` | partial | Storage C++ build with warnings-as-errors and operational chunk/manifest/sidecar/caps/corruption/no-overwrite fixture passed; GStreamer build passed but pipeline test failed. |
| `gstreamer-host-v2` | passed | Actual GStreamer1.24.2 plugin discovery and appsrc/appsink pipeline: fragmented/empty round trip, truncation, trailing data, linked flush/reset exact bytes; warnings-as-errors build. |

The [machine evidence](stream-hosts-evidence.json) binds the scoped outcomes to committed command receipts, source manifests where available, scheduler measurements and SDK identity. Sampled memory is a lower bound, not a measured exact peak. Earlier failures remain in their own immutable job directories.

The new stream transport uses independent CIXW1 windows, each holding a complete archive with its own reset model. It does not preserve cross-window codec history or perform whole-file competition. Native CIXG/M6 trials can overlap under bounded per-wave reservations; ordered selection and byte equivalence have focused tests. The window-job extension and mixed generic-pair scheduler passed their focused tests in `windows-jobs-mixed-v5`. Earlier invalid fixture assertions and the old-wire parser defect are preserved and corrected.

The experimental SquashFS profile passed sanitizers and 1,545 exact native-choice differential cases. Its userspace tools restored the complete generated fixture and xattrs. The earlier `unsquashfs -s` failure was in the pinned upstream status path before extraction; it was not evidence that the image was corrupt. The independent libsquashfs/Squashfuse readers and VM kernel mounting remain open.

The GStreamer first attempt failed its pipeline contract. The corrected adapter emits an output byte segment before empty-stream output and passes real appsrc/appsink round trips, error handling and flush/reset. The backup example passes bounded operational chunk and manifest checks and uses no Python runtime; Python is only the fixture harness.

Public distribution scaffolding is being prepared separately. Final provider closure, source allowlist/install tests, optimized binary identity, actual CXX/Sonar coverage, dead-code review and supported-platform execution still need acceptance. The SDK receipts do not certify every backend, host version or platform.

One agent ran a short kernel core-module compilation outside the required scheduler. That violated the scheduling instruction; it is recorded as unqualified and supplies no RC41 acceptance. The actual matching reader module and VM test must run under the root-owned lease.

Next action: finish and qualify the remaining native job, filesystem and distribution source, then submit the complete source/quality freeze for RC51 review.
