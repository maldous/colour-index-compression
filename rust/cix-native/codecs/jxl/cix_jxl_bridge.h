/* CIX-owned, bounded libjxl 0.12 bridge for one 2-D grayscale image. */
#ifndef CIX_JXL_BRIDGE_H
#define CIX_JXL_BRIDGE_H

#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32)
#  if defined(CIX_JXL_BRIDGE_BUILDING)
#    define CIX_JXL_API __declspec(dllexport)
#  else
#    define CIX_JXL_API __declspec(dllimport)
#  endif
#else
#  define CIX_JXL_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

enum cix_jxl_status {
    CIX_JXL_OK = 0,
    CIX_JXL_INVALID_ARGUMENT = 1,
    CIX_JXL_UNSUPPORTED = 2,
    CIX_JXL_OUTPUT_LIMIT = 3,
    CIX_JXL_ENCODE_FAILURE = 4,
    CIX_JXL_DECODE_FAILURE = 5,
    CIX_JXL_ALLOCATION_FAILURE = 6,
    CIX_JXL_EXCEPTION = 7
};

enum cix_jxl_sample_type {
    CIX_JXL_UINT8 = 1,
    CIX_JXL_UINT16 = 2
};

/* Pixels are one interleaved grayscale plane; UINT16 samples are little-endian. */
struct cix_jxl_gray_image {
    const uint8_t *pixels;
    size_t pixels_size;
    uint32_t width;
    uint32_t height;
    uint32_t bits_per_sample;
    uint32_t sample_type;
    uint32_t effort;
};

/* CIX owns the returned allocation and must release it with cix_jxl_free_buffer. */
struct cix_jxl_buffer {
    uint8_t *data;
    size_t size;
};

/*
 * Encode exactly one 2-D grayscale image. The bridge enforces lossless=true
 * and frame distance=0. max_output_bytes bounds the returned codestream.
 */
CIX_JXL_API int cix_jxl_encode_gray_2d(
    const struct cix_jxl_gray_image *image,
    size_t max_output_bytes,
    struct cix_jxl_buffer *output
);

/*
 * Decode exactly one, non-animated 2-D grayscale image into caller storage.
 * The expected geometry/type are validated at BASIC_INFO before an image buffer
 * is supplied to libjxl. output_size must exactly equal the expected samples.
 */
CIX_JXL_API int cix_jxl_decode_gray_2d(
    const uint8_t *input,
    size_t input_size,
    uint32_t expected_width,
    uint32_t expected_height,
    uint32_t expected_bits_per_sample,
    uint32_t expected_sample_type,
    uint8_t *output,
    size_t output_size
);

CIX_JXL_API void cix_jxl_free_buffer(struct cix_jxl_buffer *buffer);
CIX_JXL_API uint32_t cix_jxl_library_version(void);
CIX_JXL_API const char *cix_jxl_bridge_version(void);

#ifdef __cplusplus
}
#endif
#endif
