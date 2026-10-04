# Adapter Cppcheck projection prerequisite v3

v3 follows the retained v2 projection evidence. It runs only after v18 tool
checks. The compiler continues to produce the kernel translation unit. During
projection normalisation, only lexical GNU `typeof` tokens outside strings and
comments in `cix_squashfs_decompressor.c` are written as the equivalent
`__typeof__` GNU spelling understood by Cppcheck. No macro is defined, no
source or vendor input changes, and no diagnostic is suppressed. The v3 receipt
requires at least one conversion on that projection and zero on every other
projection before any new Sonar server may start.
