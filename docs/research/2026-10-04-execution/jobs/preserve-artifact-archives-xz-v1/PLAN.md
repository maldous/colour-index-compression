# Exact-byte archive preservation

This scheduler-only job considers four already-compressed artifact roots:

- `preserved-sdk-artifacts-v1`
- `preserved-sdk-artifacts-v2`
- `preserved-consumer-artifacts-v1`
- `preserved-consumer-artifacts-v2`

It uses a single-core XZ stream with a 256 MiB LZMA2 dictionary to exploit byte
similarity among the original gzip archives without decoding or changing any
artifact. The tar members are the original files; every path, mode, symlink or
hardlink structure, and regular-file SHA-256 is recorded before writing and
verified after reopening the XZ bundle.

The bundle has a 650,000,000-byte file cap and is created before any deletion.
The originals stay in place unless their allocated-byte replacement by the
verified bundle saves at least 150,000,000 bytes. A no-gain result removes only
the candidate bundle and records the result; it never removes an original.

The job requires the root scheduler lease and no `lsof` users before manifesting
or replacement. It rejects selected hardlinks escaping the four roots and a
changed source tree after verification. Historical receipts retain the original
paths; on success, `RESTORE.md` records the exact extraction command needed
before a reader needs those paths.
