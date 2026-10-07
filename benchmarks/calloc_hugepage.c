/* Linux/glibc-only performance probe. No allocator, byte or global VM policy
 * is replaced: retain libc calloc/free and advise only complete owned pages
 * inside allocations of at least 4 MiB. Set LD_PRELOAD only on probe children.
 * Reference: kernel.org/doc/html/latest/admin-guide/mm/transhuge.html
 */
#define _GNU_SOURCE
#include <errno.h>
#include <stdint.h>
#include <stddef.h>
#include <sys/mman.h>
#include <unistd.h>

extern void *__libc_calloc(size_t, size_t);

void *calloc(size_t count, size_t size) {
    void *memory = __libc_calloc(count, size);
    if (!memory || !count || size > SIZE_MAX / count)
        return memory;
    const size_t bytes = count * size;
    if (bytes >= (4u << 20)) {
        const int saved_errno = errno;
        const long page = sysconf(_SC_PAGESIZE);
        if (page > 0 && ((unsigned long)page & ((unsigned long)page - 1)) == 0) {
            const uintptr_t mask = (uintptr_t)page - 1;
            const uintptr_t first = ((uintptr_t)memory + mask) & ~mask;
            const uintptr_t end = ((uintptr_t)memory + bytes) & ~mask;
            if (end > first)
                (void)madvise((void *)first, end - first, MADV_HUGEPAGE);
        }
        errno = saved_errno;
    }
    return memory;
}
