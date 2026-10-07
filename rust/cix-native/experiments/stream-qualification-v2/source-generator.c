/* Frozen source generator for stream-qualification-v2 prehashing.
 * Usage: stream-qv2-source-generator > source.bin
 * It writes exactly 32 MiB without allocating source-sized storage. */
#include <stdint.h>
#include <stdio.h>

int main(void) {
    uint64_t state = UINT64_C(0x6a09e667f3bcc909);
    uint64_t remaining = UINT64_C(32) * 1024 * 1024;
    while (remaining--) {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        if (putchar((int)((state >> 24) & UINT64_C(255))) == EOF) return 1;
    }
    return fflush(stdout) == EOF;
}
