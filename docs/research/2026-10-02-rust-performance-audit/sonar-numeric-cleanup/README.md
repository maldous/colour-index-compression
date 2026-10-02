# Numeric cleanup

Base: `1146f0252cf14b9c51956c5f3f1173d72d8a055c`.

This cleanup separates numeric candidate enumeration, PFOR width selection,
byte candidate evaluation, Rice candidate construction, and checked exception
stream decoding. It preserves candidate order and only replaces an incumbent
when a candidate is strictly smaller.

## Raw qualification receipt

```
service=cix-numeric-final-3763917.service
cpu_affinity=14
memory.max=1073741824
memory.swap.max=0
cargo=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo
rustc=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc
command=cargo test numeric::tests --lib
result=6 passed; 0 failed
memory.swap.current=0
```

The module test set covers every numeric candidate round trip, truncated
candidate rejection, arithmetic bit-count overflow, payload-end overflow, and
canonical u64 varint boundary/overflow handling.

## Archive route probe

```
service=run-u113430.service
command=old/new cix --format cixm6 -1, followed by cross-decode
input_sha256=b33dd739a3b1d1e659a638b318bdcfbaed8eb8cca224dbf0a76e9e1a81db57bc
old_archive_sha256=9d80e051d58a521b113cce2d76097e4697c4eb9db6d1071f27bdc0d7a05a47d4
new_archive_sha256=6297d76f3f2304aee8c807d76958d3e58e1dc05b51f8e4f49129d245c1b1d337
old_to_new_decode=passed
new_to_old_decode=passed
archive_byte_identity=failed
truncation=decoded rejected: truncated archive
trailing=decoded rejected: trailing bytes after CIXM6 stream
memory.max=1073741824
memory.swap.max=0
memory.swap.current=0
```

The route probe establishes interoperability and malformed-file rejection, but
does not establish byte identity. It must not be used as a byte-identity
qualification result.

## Exact-parent identity check

The earlier failed comparison used a `9214` binary and was not the frozen
parent for this numeric change. The direct-toolchain build of exact parent
`1146f0252` and the candidate were rerun with identical CIXM6 fast options.

```
service=run-u113617.service
input_sha256=b33dd739a3b1d1e659a638b318bdcfbaed8eb8cca224dbf0a76e9e1a81db57bc
parent_archive_sha256=9d80e051d58a521b113cce2d76097e4697c4eb9db6d1071f27bdc0d7a05a47d4
candidate_archive_sha256=9d80e051d58a521b113cce2d76097e4697c4eb9db6d1071f27bdc0d7a05a47d4
archive_byte_identity=passed
parent_decode_candidate=passed
candidate_decode_parent=passed
memory.max=1073741824
memory.swap.max=0
```
