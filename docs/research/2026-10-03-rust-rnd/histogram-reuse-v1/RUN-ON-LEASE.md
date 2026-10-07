# One-run plan

Build only after root grants a lease. For each control, create one CIXCCV1 fixture outside timing, then perform one `pack` and one fresh-process `unpack`. Retain native input, CIXHRV1 archive, reconstructed native archive, process receipts, cgroup memory/swap readbacks, and SHA-256 values. The 1 MiB temporary budget includes all three files.

```sh
histogram_reuse_v1 fixture identical identical.cixcc
ROOT_CGROUP_WRAPPER histogram_reuse_v1 pack identical.cixcc identical.hrv
ROOT_CGROUP_WRAPPER histogram_reuse_v1 unpack identical.hrv identical.restored.cixcc
histogram_reuse_v1 decode-source identical.cixcc identical.source
ROOT_CGROUP_WRAPPER histogram_reuse_v1 decode-source identical.restored.cixcc identical.restored.source
sha256sum identical.cixcc identical.restored.cixcc
sha256sum identical.source identical.restored.source
```

Repeat once for `weak` and `absent`, and once for each of the eight exact frozen conditional-cost-v1 archives enumerated in freeze.json. Do not average or repeat. Confirm the generated fixture source SHA-256 against `freeze.json` before pack, then compare reconstructed-native SHA-256 and fresh generic native-decoder source SHA-256. Report complete native and CIXHRV1 bytes, literal/reference counts, net delta, encode/decode time, peak memory, and temporary storage separately.
