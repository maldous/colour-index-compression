# Inactive ARM64 Rust sysroot preservation candidate

Only the extracted sysroot is a candidate for later retirement. All 61 file bytes already exist in the publisher-hashed retained archive. This preparation leaves the extracted tree unchanged.

The manifest preserves paths, regular-file hashes and sizes, file and directory mode, uid/gid, mtime_ns and link counts. ctime, inode numbers and atime are filesystem observations rather than promised restore metadata. No symlinks or external hardlinks exist.

Future offline recovery uses `restore.py` only under a separately admitted root scheduler job, a 164 MB reservation, an absent target, and admission JSON binding operation, comment_id, reserved_bytes and manifest_sha256. It validates the archive before creation and each restored file, restores declared metadata, then compares the complete tree. This source recipe is independently reviewable; no disk restore drill has run under this preparation.

The privileged process preflight records only matched target paths/kinds/PIDs and error counts. Any retirement needs a fresh identical scan and independent acceptance first. No ARM64 capability is removed from scope; future Rust use requires restoration.
