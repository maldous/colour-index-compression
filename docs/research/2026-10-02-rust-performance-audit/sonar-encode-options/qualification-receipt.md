# Qualification receipt

Exact base `52cd25716` and candidate `d5bf389e` were built with stable Rust in `systemd-run --user` services: `MemoryMax=1073741824`, `MemorySwapMax=0`, `CPUAffinity=16`, `TasksMax=16`. Input length: 26624; SHA-256 `a5ef6b097587b9c0a1c5ccc76e01417b6e08c950c46411d38dae1ad9dc7f2bb8`.

Commands (all exit 0) used each old/new binary, then `cmp` archives, each old/new `uncix` decoded the other archive, and `cmp input output` passed:

```text
cix --format cixg1 --fast --stream --route composition --block-size 4KiB --memory 128MiB --threads 1 --explain -o ARCHIVE input
cix --format cixg2 --route composition --backend huffman --block-size 4KiB --memory 128MiB --threads 1 --explain -o ARCHIVE input
```

G1 archive: 1665 bytes, SHA-256 `aad5dce795b1fcb172cace5a9b39938365fbb85894b4f5d1cb9b8e06aad6044c`; trace selected `composition:deflate` for all 26624 bytes.

G2 archive: 18516 bytes, SHA-256 `5195cbf8b9041f12e1b9722cbd1e7f8f8bad8805b8eccbe123696508619e1d80`; trace selected `composition:huffman` for 20480 bytes and raw fallback for 6144 bytes. Full sanitized explain logs remain at `/tmp/cix-encode-qual/{old,new}-{g1,g2}.log`.

The archive bytes are equal old/new and reciprocal decodes matched the input.

The same G2 command was exercised on stdin/stdout (`cat input | cix ... -c -o -`); old and candidate pipe archives were equal to the recorded G2 SHA-256, and candidate `cat archive | uncix -c -o -` restored the input SHA-256.

Candidate forwarding paths were also exercised under the same cgroup: `--best --stream --memory 128MiB` restored exactly through the persistent stream dispatcher; `--portfolio fast --memory 512M` selected `cix-adaptive`, produced a 448-byte archive with SHA-256 `bf8405f9b557ceb85237999c460bacbb1d4ee6915e2423705a8cb4e0379343b4`, and restored exactly.

The committed `benchmarks/cix_stream_latency_probe.py` was copied outside Git and only its CIX/UNCIX paths and CPU affinity were replaced (candidate binaries, CPU 16). Its raw JSON receipt is `/tmp/cix-encode-qual/probe.json`. With `--flush-interval 100ms`, its idle-open first 32 KiB probe at 450 ms recorded 32,822 compressed bytes and 32,768 decoded bytes before EOF; the 4 KiB-pipe slow-consumer case paused for 0.7 s, kept both processes alive before EOF, and restored exactly. It rejected a truncated archive and a corrupted first frame with exit 2; truncated output contained only the already verified 65,536-byte prefix before footer failure. A separate candidate `--best --stream` process received SIGINT during an 8 MiB named-input encode: exit 2, named output absent, input retained, and no `.sig-output*` temporary file remained.
