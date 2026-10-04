#ifndef CIX_H
#define CIX_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define CIX_ABI_VERSION_1 UINT32_C(1)

typedef struct cix_context cix_context;

typedef enum cix_status {
    CIX_STATUS_OK = 0,
    CIX_STATUS_INVALID_ARGUMENT = 1,
    CIX_STATUS_INVALID_OPTIONS = 2,
    CIX_STATUS_OUTPUT_TOO_SMALL = 3,
    CIX_STATUS_CODEC_ERROR = 4,
    CIX_STATUS_PANIC = 5,
    CIX_STATUS_RESOURCE_LIMIT = 6
} cix_status;

typedef enum cix_profile {
    CIX_PROFILE_FAST = 1,
    CIX_PROFILE_DEFAULT = 2,
    CIX_PROFILE_BEST = 3
} cix_profile;

/* Append-only layout.  Set abi_version and struct_size before creation. */
typedef struct cix_options_v1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t profile;
    uint32_t workers;
    uint64_t output_limit;
    uint64_t memory_limit;
} cix_options_v1;

/* Writes valid v1 defaults to a writable complete cix_options_v1 object. */
cix_status cix_options_v1_default(cix_options_v1 *out);

/* Creates an opaque context. `options` must point to a readable prefix through
 * struct_size; v1 requires at least sizeof(cix_options_v1). On failure, a
 * writable out_context is set to NULL. Pass a successful context to exactly
 * one destroy call. */
cix_status cix_context_create(const cix_options_v1 *options, cix_context **out_context);
void cix_context_destroy(cix_context *context);

/*
 * Complete-buffer operations.  They are not incremental operations.
 * input may be NULL only when input_len is zero; output may be NULL only when
 * output_capacity is zero.  needed is required.  A successful call writes
 * needed bytes.  OUTPUT_TOO_SMALL writes the required count and does not write
 * output. Input, output, and needed storage must not overlap. CIX never
 * allocates an output buffer for the caller.
 */
cix_status cix_encode_buffer(cix_context *context,
                             const uint8_t *input, size_t input_len,
                             uint8_t *output, size_t output_capacity,
                             size_t *needed);
cix_status cix_decode_buffer(cix_context *context,
                             const uint8_t *input, size_t input_len,
                             uint8_t *output, size_t output_capacity,
                             size_t *needed);

/* Copies the context-owned diagnostic.  needed includes its NUL terminator. */
cix_status cix_context_last_error(const cix_context *context,
                                  char *output, size_t output_capacity,
                                  size_t *needed);

/*
 * Contexts own independent immutable option snapshots and bounded diagnostics.
 * Calls on one context are serialized; distinct live contexts may be used
 * concurrently.  Destroying a context concurrently with any call using it is
 * invalid.  This v1 buffer ABI has no cancellation-handle ownership transfer,
 * no incremental API, and no process-RSS hard-cap guarantee.
 */

#ifdef __cplusplus
}
#endif

#endif /* CIX_H */
