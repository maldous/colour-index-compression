# Silesia v3 review checkpoint

Snapshot time: 2026-09-30 22:02:59 UTC. This is an in-progress checkpoint, not a completed benchmark.

The frozen comparison covers the 12 complete official Silesia members, seven methods (CIX plus gzip, bzip2, Zstandard, XZ/LZMA2, Brotli and paq8px), and separate speed, current and size profiles. CIX is configured as an adaptive portfolio containing the six reference backends. Each qualified row requires an archive-only decode and exact SHA-256 restoration. Only complete verified rows may be ranked.

At snapshot time the 252 declared cells were: 98 `VERIFIED_SCREENING`, 26 `FAILED` (including attempts later normalized as time/resource limits in the Site export), 12 prelaunch `RESOURCE_LIMIT` exclusions (paq8px size profile), and 116 `PENDING`. The experiment remains active; later checkpoints will supersede this snapshot without altering it.

`results.json` is the raw scheduler readback. `results.csv` is the Site-facing table export with incomplete cells kept explicit. `cells.json`, `coverage.json`, `environment.json` and the per-cell manifests preserve the declared inputs, settings, hashes and budgets. The individual runner work directories and compressed outputs remain in local research storage and are not included here; their receipts are addressed by the raw result records. Do not treat pending, failed, timed-out or resource-excluded cells as compression measurements.

The matching public progress view is https://cix-compression-benchmarks.matthewaldous.chatgpt.site. The Site selector is limited to the 12 official Silesia files, each labeled by its data type, and its profile rankings remain separate.
