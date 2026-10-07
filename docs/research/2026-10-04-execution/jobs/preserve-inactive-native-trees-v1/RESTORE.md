# Restore inactive native trees

The roots below were archived only after path, mode, symlink, hardlink, and SHA-256 verification. Restore them before rerunning a historical job that names one of their paths.

```sh
cd /home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1
tar -xJf preserve-inactive-native-trees-v1/inactive-native-trees.tar.xz
```

This restores:

- `python-host-sdk-v1`
- `native-final-source-v3`
- `runtime-closure-v1`
- `runtime-closure-v2`

Some archived files may also have retained hardlink names outside these roots. Those paths are never modified by restoration: extraction creates an independent byte-identical file where an external hardlink cannot be re-established without changing retained work.
