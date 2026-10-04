/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef CIX_SQUASHFS_REGISTER_H
#define CIX_SQUASHFS_REGISTER_H

#include <linux/fs.h>
int cix_squashfs_register_filesystem(struct file_system_type *fs);
int cix_squashfs_unregister_filesystem(struct file_system_type *fs);
#endif
