# Lease-only measurement plan

The driver is [conditional_cost_v1.rs](../../../../rust/cix-native/experiments/conditional-cost-v1/conditional_cost_v1.rs). It is intentionally outside Cargo targets and no manifest changes are required.

After root grants a scheduler lease and seals its dependency links, use the immutable rlib at `benchmark-work/ptt5-fixed-8439/target/release-lto/libcix_native.rlib` (6,772,248 bytes) and its sibling `deps` directory. Do not substitute an unpinned build. Generate each input once outside timing, retain it, and SHA-256 it. Then run exactly one complete archive encode and one fresh-process complete archive decode for each `(case, codec)`. The archive and restored input are retained temporary storage and must be charged against the 1 MiB cap. Root's wrapper owns its transient cgroup cap, `memory.swap.max=0`, and the cgroup readbacks; `taskset` alone is insufficient.

```sh
for case in alternating clustered periodic random; do
  /tmp/conditional-cost-v1 generate "$case" "RESULT_DIR/$case.input"
  sha256sum "RESULT_DIR/$case.input" >> "RESULT_DIR/input.sha256"
  for codec in exact-rank remaining-count-range; do
    ROOT_CGROUP_WRAPPER /tmp/conditional-cost-v1 encode "$codec" "$case" "RESULT_DIR/$case.$codec.cixcc" > "RESULT_DIR/$case.$codec.encode.json"
    ROOT_CGROUP_WRAPPER /tmp/conditional-cost-v1 decode "RESULT_DIR/$case.$codec.cixcc" "RESULT_DIR/$case.$codec.restored" > "RESULT_DIR/$case.$codec.decode.json"
    sha256sum "RESULT_DIR/$case.input" "RESULT_DIR/$case.$codec.restored" >> "RESULT_DIR/restore.sha256"
  done
done
```

Record the resolved binary SHA-256, source hashes in `SOURCE-AUDIT.md`, scheduler lease, command, process receipt, cgroup memory/swap readback, and SHA-256 of generated, archive, restored, and JSON files. Do not average or repeat runs. The decode command rejects archive framing errors, trailing payload, inconsistent tile count, a contradiction between outer coder ID and inner sequence mode, and a range bit length that contradicts tile length. It charges 26-byte experimental archive framing, every tile-length varint, identical count-header bytes, mode byte, range bit-length varint, emitted payload bytes, and byte padding. `arithmetic_stream_bits` is the stored range bit length including termination, not a quantized-CDF probability cost.

Do not interpret a difference as conditional, contextual, or predictive gain. With counts fixed and charged, both coders describe the same type class. Retain a verified native-coder comparison, including a null or negative result, as evidence.
