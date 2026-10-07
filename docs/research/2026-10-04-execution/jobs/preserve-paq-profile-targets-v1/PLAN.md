# Preservation recipe

This is a scheduler-only, unexecuted recipe. It selects exactly:

- `paq-loader-slice1-v1/target`
- `squashfs-profile-alignment-v2/cargo-target`

It first requires the PAQ work receipt and outer raw result to be terminal passes, and the squashfs v2 receipt and outer raw result to be terminal passes. It rejects active users of either selected tree.

For each root it creates a separate sorted full manifest of every directory, regular file (SHA-256, mode, device/inode/link count), and safe relative symlink. It rejects a selected inode linked outside its root or across the other selected root. The PAQ `debug/cix` hardlink group is copied once, byte/mode-verified under `preserved-paq-profile-targets-v1/binaries`, and represented in its manifest; all other members are written to its XZ preset-9 archive with original hardlink entries. The profile target is fully archived independently. Both archives are reopened and verified against their complete manifests; the retained `cix` copy is verified against its manifest identity.

The combined archive files, manifests, and separate `cix` copy must measure at most 80,000,000 bytes before either deletion. A failed or over-cap attempt leaves both targets and partial archives intact and writes a failure receipt. After both independent archive verifications and unchanged re-manifests, remove only the two selected roots. Keep PAQ private/provider paths, squashfs C objects, contract, differential/source evidence, logs, receipts, and all other work untouched. Record aggregate work before/after; this job does not admit Sonar. Sonar admission must later measure `retained_work + 620756992 <= 4000000000` independently.
