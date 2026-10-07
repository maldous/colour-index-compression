# Native interfaces and selection checkpoint

This checkpoint qualifies bounded native interfaces on Linux x86-64. It does not complete the release candidate, reopen research, or authorize the stopped benchmark. Authoritative RC acceptance remains coordinator-owned.

## Delivered source

- Nine genuine standard byte-stream formats: gzip, zlib, raw DEFLATE, bzip2, XZ, Zstd, Brotli, LZ4 frame and Snappy framed. Explicit CLI `--output-format` and decoder `--input-format` avoid guessing raw formats. These are complete-buffer operations with a 128 MiB input/output ceiling, not incremental standard-format streaming.
- Stateless caller-buffer C format API, installed `cix_formats.h`, and corresponding Rust API. Independent calls do not launch a process. The C dictionary API is still pending; the passing dictionary interface is Rust.
- Owned Zstd dictionaries with training/import, SHA-256 identity plus native dictionary ID, exact single-frame decoding, RAII native handles and checked memory estimates. The installed libzstd must export its documented estimator symbols; these are a pinned ABI dependency.
- A rolling, resource-admitted whole-input native selector. Raw runs first; ties preserve declared priority; workers overlap when reservations fit. Panic and cancellation tests pass. The selector includes the complete CIXH1 candidate for DEFAULT/BEST and remains a library surface pending ordinary CLI binding.
- Automatic CIXH1 region selection with complete input coverage, paid framing and parameters, bounded family-round-robin specialist trials, explicit omissions and raw fallback. The actual native DEFAULT interleaved-region archive restores exactly. This regional implementation remains serial; whole-input candidate overlap is distinct from region parallelism.
- All six SGFB1 feedback mode/model combinations and distinct CIXY1 envelope code. Exact raw encodings match frozen Python reference fixtures. Shared archive dispatch registration remains pending.
- Native CharLS 2.4.2 and OpenJPEG 2.5.0 bridge/provider. Fourteen generated grayscale round trips cover 8/12/16-bit tiny images plus larger constant, ones, wave and pseudorandom patterns; malformed shape, truncation and trailing data are rejected. Historical CIX image-envelope integration and reference cross-decoding remain pending.
- Nonzero ECRD1 pointer-delta mode-5 reference parity. ECRP1 and ECBR2 are helper identities, not missing standalone production wire formats; see the address-helper audit.

## Passing evidence

The frozen source is `jobs/interfaces-v7/source.json`. All-target compilation and library/executable build completed; 29 focused tests passed. The same job was stopped when temporary space reached 4,007,783,035 bytes near the end of SDK qualification. Its SDK completion is not credited. This is a real budget interruption preserved in the evidence, not a successful overall job.

Only disposable incremental compiler cache was removed (958,628,920 bytes; `cache-cleanup-v3.json`). The narrow `interfaces-v8` rerun bound the same source and compiled library identities and reran SDK installation only. Shared and static relocation, C buffer/stream/standard-format consumers and the C++ consumer all passed. The rerun used 3,426,506,217 tracked temporary bytes and 2.97 seconds wall time. These are engineering check costs, not compression throughput measurements.

`interfaces-evidence.json` records the exact test groups and prior failed attempts. Spatial DSO source/build is bound to `interfaces-v6`; its source hashes match v7. Dependency package identities are in `jobs/codec-sdk-provision-v1`. Third-party source was not modified.

The strict marker scans were checked against [CharLS 2.4.2 decoder bit stuffing](https://raw.githubusercontent.com/team-charls/charls/2.4.2/src/decoder_strategy.h) and [OpenJPEG MQ decoding](https://www.openjpeg.org/doxygen/mqc__inl_8h_source.html). Workspace figures are admission estimates, not hard RSS enforcement inside an embedding process.

## Remaining work

Bind the native selector into ordinary CLI operation, complete the remaining legacy decoders and image envelopes, finish the full-engine job/SDK surfaces and adapters, then run final quality, packaging and platform qualification. No required source row is silently deferred. Cross-platform execution, native SquashFS qualification, final Sonar/dead-code closure, RC51 readiness and the later 36-cell Silesia confirmation remain open. Public repository creation, publication, corpus acquisition and old automation resumption remain held.
