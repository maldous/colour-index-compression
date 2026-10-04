/* Experimental, block-local CIX SquashFS profile. See SPEC.md. */
#ifndef CIX_SQUASHFS_PROFILE_H
#define CIX_SQUASHFS_PROFILE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum cix_squashfs_profile_kind {
    CIX_SQUASHFS_DATA = 0,
    CIX_SQUASHFS_METADATA = 1
};

enum cix_squashfs_profile_status {
    CIX_SQUASHFS_OK = 0,
    CIX_SQUASHFS_NO_BENEFIT = 1,
    CIX_SQUASHFS_INVALID_ARGUMENT = 2,
    CIX_SQUASHFS_OUTPUT_TOO_SMALL = 3,
    CIX_SQUASHFS_MALFORMED = 4,
    CIX_SQUASHFS_LIMIT = 5
};

/* 131072 for data, 8192 for metadata, or zero for an invalid kind. */
size_t cix_squashfs_profile_max_input(enum cix_squashfs_profile_kind kind);

/* Bytes and alignment needed by the caller-owned adaptive decode model. */
size_t cix_squashfs_profile_decode_workspace_size(void);

/*
 * `src` and `dst` must name non-overlapping ranges. `dst` must be at least
 * src_len bytes. On success, written is smaller than src_len. NO_BENEFIT tells
 * a SquashFS caller to store its input uncompressed. No heap allocation,
 * process state, history, dictionary, or floating point is used. dst contents
 * are unspecified unless this returns OK.
 */
int cix_squashfs_profile_encode(enum cix_squashfs_profile_kind kind,
    const uint8_t *src, size_t src_len, uint8_t *dst, size_t dst_cap,
    size_t *written);

/*
 * Decodes one complete, non-overlapping profile block. written equals the
 * declared length only on success.
 */
int cix_squashfs_profile_decode(enum cix_squashfs_profile_kind kind,
    const uint8_t *src, size_t src_len, uint8_t *dst, size_t dst_cap,
    size_t *written);

/*
 * Equivalent to decode, but its adaptive model lives in `workspace`.  This is
 * the kernel-safe entry point: workspace must have at least
 * cix_squashfs_profile_decode_workspace_size() bytes and suitable uint32_t
 * alignment.  The workspace must not overlap either src or dst.  It has no
 * allocation and never retains the workspace.
 */
int cix_squashfs_profile_decode_with_workspace(
    enum cix_squashfs_profile_kind kind, const uint8_t *src, size_t src_len,
    uint8_t *dst, size_t dst_cap, void *workspace, size_t workspace_len,
    size_t *written);

#ifdef __cplusplus
}
#endif
#endif
