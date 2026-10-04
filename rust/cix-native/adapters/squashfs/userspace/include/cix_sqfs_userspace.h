/* Experimental userspace-only SquashFS CIX decoder bridge. */
#ifndef CIX_SQFS_USERSPACE_H
#define CIX_SQFS_USERSPACE_H

#include <stddef.h>
#include <stdint.h>

#define CIX_SQFS_EXPERIMENTAL_COMPRESSION_ID 65001u

enum cix_sqfs_block_class {
    CIX_SQFS_BLOCK_DATA = 0,
    CIX_SQFS_BLOCK_FRAGMENT = 1,
    CIX_SQFS_BLOCK_METADATA = 2,
    CIX_SQFS_BLOCK_XATTR = 3
};

/* The source adapter must pass the superblock method and the real block class.
 * It returns zero only after a complete bounded profile decode. */
int cix_sqfs_userspace_decode(uint16_t compression_id,
    enum cix_sqfs_block_class block_class, const void *compressed,
    size_t compressed_size, void *output, size_t output_capacity,
    size_t *output_size);

#endif
