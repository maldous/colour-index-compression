/* CIX-owned, bounded libjxl 0.12 bridge for gray and Z/H/W planar images. */
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

/* Basic info obtained without installing an image output buffer. */
struct cix_jxl_gray_info {
    uint32_t width;
    uint32_t height;
    uint32_t bits_per_sample;
    uint32_t sample_type;
};

/* Contiguous Z/H/W planes. Plane zero is gray; remaining planes are optional
 * JXL extra channels in increasing channel-index order. */
struct cix_jxl_planar_image {
    const uint8_t *pixels;
    size_t pixels_size;
    uint32_t depth;
    uint32_t width;
    uint32_t height;
    uint32_t bits_per_sample;
    uint32_t sample_type;
    uint32_t effort;
};

struct cix_jxl_planar_info {
    uint32_t depth;
    uint32_t width;
    uint32_t height;
    uint32_t bits_per_sample;
    uint32_t sample_type;
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
/*
 * Inspect one grayscale still image without decoding pixels. expected_pixels is
 * derived from CIX framing and is checked before any output buffer is given to
 * libjxl. This is the bounded legacy-CIXI1 shape recovery primitive.
 */
CIX_JXL_API int cix_jxl_probe_gray_2d(
    const uint8_t *input,
    size_t input_size,
    size_t expected_pixels,
    struct cix_jxl_gray_info *info
);

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

/* Bounded Z/H/W gray-plus-optional-channel transport for historical planar
 * CIXV1 mode 3 and CIXI2 bands. */
CIX_JXL_API int cix_jxl_encode_planar(
    const struct cix_jxl_planar_image *image,
    size_t max_output_bytes,
    struct cix_jxl_buffer *output
);
CIX_JXL_API int cix_jxl_probe_planar(
    const uint8_t *input,
    size_t input_size,
    uint32_t expected_depth,
    size_t expected_pixels,
    struct cix_jxl_planar_info *info
);
CIX_JXL_API int cix_jxl_decode_planar(
    const uint8_t *input,
    size_t input_size,
    uint32_t expected_depth,
    uint32_t expected_width,
    uint32_t expected_height,
    uint32_t expected_bits_per_sample,
    uint32_t expected_sample_type,
    uint8_t *output,
    size_t output_size
);

/* Exact XZ metadata stream used by the retained CIX image envelopes. */
CIX_JXL_API int cix_lzma_compress_preset9(
    const uint8_t *input,
    size_t input_size,
    size_t max_output_bytes,
    struct cix_jxl_buffer *output
);
CIX_JXL_API int cix_lzma_decompress_exact(
    const uint8_t *input,
    size_t input_size,
    size_t expected_output_bytes,
    size_t memory_bytes,
    struct cix_jxl_buffer *output
);

CIX_JXL_API void cix_jxl_free_buffer(struct cix_jxl_buffer *buffer);
CIX_JXL_API uint32_t cix_jxl_library_version(void);
CIX_JXL_API const char *cix_jxl_bridge_version(void);

#ifdef __cplusplus
}
#endif
#endif
