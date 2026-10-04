# Go module cache restoration

This directory preserves the completed `go-mod-cache` that was reclaimed to
make room in the shared qualification work root. Any future Go job that would
reuse that cache must restore and verify it before using the cache path.

Expected archive SHA-256: `9801d0dd18ae78019e7edc6235bb3fb813f3c429f225222f1a2f319f3d67c579`
Expected manifest SHA-256: `d6840c7d061b4510ea8e9ed99dc20fe7f7cd5145164ba5faf27f2fd3b2def383`

1. Verify the archive and manifest hashes above.
2. Extract `go-mod-cache.tar.xz` into a fresh, empty temporary directory. The
   archive contains a top-level `target/` directory because the reviewed
   preservation helper uses a generic target archive layout.
3. Verify the extracted member hashes, modes, symlinks, and hardlinks against
   `go-mod-cache.manifest.json` using the preservation verifier before reuse.
4. Move the verified extracted `target/` directory to
   `benchmark-work/native-rc-check-v1/go-mod-cache` without merging it into an
   existing directory.
5. Recheck that no Go process is using the restored path before a future job
   modifies it.

The archive is a cache recovery artifact. It is not a source, dependency, or
binary distribution.
