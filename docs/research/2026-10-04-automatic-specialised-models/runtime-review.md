# Runtime source review

Read-only review of runtime/cix_runtime/{engine,backends,heterogeneous,regions,specialized}.py and runtime/cix_runtime/legacy/executable.py. No candidate was run.

## Findings requiring repair

### P0 — Image and volume decoders expand before their admitted bounds

The dispatch registry exposes CIXI1, CIXV1 and CIXI2 through image_grid.DECODERS (image_grid.py:7) and specialized._decoder_maps (specialized.py:189-202). Their decoders accept max_output_bytes and memory_bytes, but expand untrusted members before applying a decompression/output bound:

- legacy/spatial_image_codec.py:33-45: lzma.decompress and imagecodecs.*_decode are called without a limit; memory_bytes is not used.
- legacy/volume_image_codec.py:40-48: same unrestricted LZMA and JXL decoding; memory_bytes is not used.
- legacy/multiscale_volume.py:33-60: same unrestricted LZMA and per-band JXL decoding; memory_bytes is not used.

The frame's claimed original size is checked first, but that does not bound an expanding compressed metadata or image member. Make expansion bounded before allocation, validate decoded array dimensions/byte size against the declared region and remaining memory, and reject a member before constructing the result. The same rule should be applied to any other directly dispatched legacy Brotli/LZMA frame before it is retained in the public registry.

### P0 — PAQ/native output limits are post-decode only

backends.decode_paq invokes PAQ at backends.py:98-105; it checks the restored file size only after the subprocess has written it. native_decode does the same at backends.py:132-138. The executable legacy path repeats the pattern in legacy/executable.py:35-57, including when called by decode_joint_discount (69-78) and decode_filtered (90-100).

This permits an adversarial archive to consume temporary storage before the declared output bound is observed. The PAQ decode path also does not pass or otherwise enforce memory_bytes; its 128 MiB check is an admission floor, not an actual process memory limit (backends.py:89-105). Run external decoders with a per-process temporary-output bound and an enforceable resource limit (or a backend streaming limit), then retain/read only an admitted output. Apply the same control to the legacy executable helper.

### P1 — Nested specialist cap drops reachable candidates by catalogue order

heterogeneous._specialist_choices admits only the first four candidate objects (heterogeneous.py:57-76). For a valid volumetric image region, image_grid.catalog first produces four spatial image candidates (image_grid.py:15-16) and then emits the volume modes, including the explicit historical volume mode-3/effort-10 entry and multiscale entry (image_grid.py:17-23). Consequently those volume candidates are always omitted in CIXH1, solely due to list order, before complete-archive comparison.

That conflicts with the intended automatic specialist consideration for recognised structure within heterogeneous input. Retain a frozen, content- and cost-derived admission policy that represents every candidate family (or remove the claim of full heterogeneous specialist coverage). Do not present the current cap as a full registry evaluation.

### P1 — Declared candidate resource limits are admission metadata, not runtime enforcement

engine.encode compares candidate declarations with the requested limits (engine.py:137-140), but the worker only applies RLIMIT_FSIZE (engine.py:82-86). It does not set a process memory/CPU limit, and Python specialists or their children can exceed the declared candidate memory. Native encode receives a backend --memory option, but that does not cover every candidate or subprocess. The selection report therefore currently describes admission, not enforced resource isolation. Enforce the declared limits at the candidate process boundary or label the values as estimates until an outer cgroup is mandatory and evidenced.

### P2 — Candidate-to-decoder coverage is conventional rather than enforced

The current candidate sources appear to use frame magics represented by specialized._decoder_maps (specialized.py:189-202), but neither specialized.catalog nor engine._worker validates that a completed specialist candidate begins with a registered magic. engine._worker accepts any returned bytes and records only a hash (engine.py:86-101). A future registry/candidate mismatch can therefore win size selection and produce an archive that engine.decode cannot dispatch.

Carry an explicit supported-frame declaration on each specialised candidate and check it against the decoder registry before trial/selection. This is a header-contract check, not a full per-candidate decode, so it does not reintroduce duplicated full verification.

## Verified source properties

- Cataloguing itself does not invoke candidate encode: engine builds closures (engine.py:35-68); heterogeneous cataloguing records admission and queries specialist catalogues (heterogeneous.py:110-137); specialised cataloguing runs recognizers and constructs candidates (specialized.py:143-186). This does not prove recognizers are cheap, only that they do not call the candidate encoder in these paths.
- There is no raw-backend substitution for a missing specialist: specialized._external_catalog records runtime-closure-unavailable (specialized.py:131-140), while a specialist failure is an explicit omission (heterogeneous.py:75-76).
- CIXH1 is not numeric-pattern-only. regions.boundaries partitions all bytes and uses numeric runs only as additional cut points (regions.py:7-35); each region receives raw, zlib and LZMA competition (heterogeneous.py:32-41,79-87). CIXH1's zlib/LZMA decoder uses a source_len + 1 expansion bound (heterogeneous.py:139-167).
- The reviewed runtime modules do not import benchmark/result/corpus/certificate paths. Backends resolve executables from the installed closure (backends.py:1-5,24-42), and recognizers document byte-only input (specialized.py:1-7, regions.py:7-12).

## Scope limitation

This review does not establish byte-for-byte algorithm parity with each historical backend. In particular, the executable filtered route uses v216 for encoding (legacy/executable.py:81-87) and the store-state fork for decoding (legacy/executable.py:90-100); that pairing needs its existing round-trip proof before release, rather than inference from source inspection.

