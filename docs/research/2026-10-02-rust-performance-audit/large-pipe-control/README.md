# Large native pipe control

The recorded native `9214e2f8b` checkpoint encoded and decoded 256 MiB through
actual anonymous pipes under an aggregate 64 MiB cgroup with swap disabled.
The generator retains one 64 KiB block; the relay never exceeded 64 KiB.
No input, archive or reconstructed output was spooled to a file. Fresh encoder
and decoder processes exited zero and the entire original/reconstructed lengths
and SHA-256 matched. The complete compressed stream was 268,603,446 bytes.

Downstream reads were held for 300 ms. Only 393,216 source bytes had been
accepted at release in this run, demonstrating backpressure rather than
whole-stream queuing. The cgroup's retained peak was 11,419,648 bytes; sampled
native RSS peaks were approximately 6.6 MB encoder and 5.5 MB decoder (sampled
lower bounds, with shared pages counted per process). All child cgroup paths
matched the parent resource guard. Whole-stream integrity was accepted only
after EOF/footer verification and successful native decoder exit.

This is a one-run synthetic raw-route correctness screen. The explicit FAST/raw
route isolates framing and buffers; it does not qualify persistent histories,
automatic BEST selection, comparative codec speed or corpus ranking. The
1.67-second pipeline wall time includes generation, hashing and relay overhead.

The insufficient 4 MiB encoder-budget attempt is retained separately: CIX
rejected two worker stacks/buffers with exit 2. The probe retained diagnostics
and killed its dependent decoder. It was not promoted to a successful result.

Reproduce from the repository root using a new result path and unit name:

```sh
systemd-run --user --wait --collect --unit=cix-large-pipe-NEW \
  --property=MemoryMax=64M --property=MemorySwapMax=0 \
  --property=CPUAffinity=8 --property=WorkingDirectory="$PWD" \
  /usr/bin/python3 -m benchmarks.cix_large_pipe_probe \
  --release benchmark-work/combined-9214-validation/final \
  --output /tmp/cix-large-pipe-NEW.json
```

Native binary and resolved DSO hashes, commands, resource readbacks and complete
stream identities are in the receipts; `manifest.json` freezes the probe hash.
