/* CIX-owned bounded JPEG-LS/JPEG 2000 grayscale bridge. */
#ifndef CIX_SPATIAL_BRIDGE_H
#define CIX_SPATIAL_BRIDGE_H

#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32)
# if defined(CIX_SPATIAL_BRIDGE_BUILDING)
#  define CIX_SPATIAL_API __declspec(dllexport)
# else
#  define CIX_SPATIAL_API __declspec(dllimport)
# endif
#else
# define CIX_SPATIAL_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

enum cix_spatial_status { CIX_SPATIAL_OK=0, CIX_SPATIAL_INVALID_ARGUMENT=1,
  CIX_SPATIAL_UNSUPPORTED=2, CIX_SPATIAL_OUTPUT_LIMIT=3,
  CIX_SPATIAL_ENCODE_FAILURE=4, CIX_SPATIAL_DECODE_FAILURE=5,
  CIX_SPATIAL_ALLOCATION_FAILURE=6, CIX_SPATIAL_EXCEPTION=7 };
enum cix_spatial_codec { CIX_SPATIAL_JPEG2000=2, CIX_SPATIAL_JPEGLS=3 };
struct cix_spatial_buffer { uint8_t* data; size_t size; };
struct cix_spatial_info { uint32_t width, height, bits_per_sample; };

/* Input and output samples are one grayscale plane of canonical LE u16. */
CIX_SPATIAL_API int cix_spatial_encode_u16_gray(
  uint32_t codec, const uint8_t* pixels, size_t pixels_size,
  uint32_t width, uint32_t height, uint32_t bits_per_sample,
  size_t max_output_bytes, struct cix_spatial_buffer* output);
CIX_SPATIAL_API int cix_spatial_probe_gray(
  uint32_t codec, const uint8_t* input, size_t input_size,
  uint32_t expected_width, uint32_t expected_height,
  uint32_t expected_bits_per_sample, struct cix_spatial_info* info);
CIX_SPATIAL_API int cix_spatial_decode_u16_gray(
  uint32_t codec, const uint8_t* input, size_t input_size,
  uint32_t expected_width, uint32_t expected_height,
  uint32_t expected_bits_per_sample, uint8_t* output, size_t output_size);
CIX_SPATIAL_API void cix_spatial_free_buffer(struct cix_spatial_buffer* buffer);
CIX_SPATIAL_API uint32_t cix_spatial_charls_version(void);
CIX_SPATIAL_API uint32_t cix_spatial_openjpeg_version(void);
CIX_SPATIAL_API const char* cix_spatial_bridge_version(void);
#ifdef __cplusplus
}
#endif
#endif
