# Ubuntu codec source provenance v1

The selected Linux x86_64 runtime packages identify their source packages in
their retained Debian control metadata: `libcharls2` identifies `charls`, and
`libopenjp2-7` identifies `openjpeg2`. The official Ubuntu source descriptors
provide the exact source version, descriptor URL and SHA-256, plus the original
and Debian packaging archive URL, byte size and SHA-256. The corresponding
machine-readable freeze is
[`ubuntu-codec-source-provenance-v1.json`](ubuntu-codec-source-provenance-v1.json).

The relation to the selected runtime libraries is now direct rather than
inferred. The following data members were streamed from the already retained
`.deb` archives without extracting them to a tree:

| Source package | Retained binary package member | SHA-256 | Selected provider |
| --- | --- | --- | --- |
| `charls` 2.4.2-2build2 | `usr/lib/x86_64-linux-gnu/libcharls.so.2.4.2` | `6fc5859988357c676d874fa98509445b8a8c8eee4eac533b5ae3eb884e0b858c` | `CIX_RUNTIME_CHARLS_LIBRARY` |
| `openjpeg2` 2.5.0-2ubuntu0.5 | `usr/lib/x86_64-linux-gnu/libopenjp2.so.2.5.0` | `19906c0334e8db2137912f83cceed5a03d954a9c12d9781901a9a27f92ce1c4d` | `CIX_RUNTIME_OPENJPEG_LIBRARY` |

Both values equal the selected-provider closure. The companion development
archives remain separately pinned in the existing codec package receipt.

The next bounded operation is source retention, not a rebuild: retrieve the
two `.dsc` files and four named source archives, verify every recorded SHA-256
before unpacking, and make a tree receipt. That source acquisition is necessary
before the prepared non-PAQ source staging gate can become complete.

This records package provenance and content identity only. It makes no claim
about a fresh reproducible build, licence obligations, redistribution, or
release acceptance.
