/* SPDX-License-Identifier: GPL-2.0-only */
/* CIX-owned, allocation-free decoder for private SquashFS compressor 65001. */
#ifndef CIX_SQUASHFS_KERNEL_H
#define CIX_SQUASHFS_KERNEL_H

#include <linux/types.h>

#define CIX_SQUASHFS_COMPRESSION 65001
#define CIX_SQUASHFS_DATA_LIMIT (128 * 1024)
#define CIX_SQUASHFS_METADATA_LIMIT (8 * 1024)

extern size_t cix_squashfs_profile_decode_workspace_size(void);
extern int cix_squashfs_profile_decode_with_workspace(int kind, const u8 *src,
	size_t src_len, u8 *dst, size_t dst_cap, void *workspace,
	size_t workspace_len, size_t *written);

enum cix_squashfs_kernel_kind {
	CIX_SQUASHFS_KERNEL_DATA,
	CIX_SQUASHFS_KERNEL_METADATA,
};

#endif
