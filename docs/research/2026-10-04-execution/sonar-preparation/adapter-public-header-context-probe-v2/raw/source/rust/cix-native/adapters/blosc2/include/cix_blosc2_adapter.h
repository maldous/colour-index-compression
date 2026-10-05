#ifndef CIX_BLOSC2_ADAPTER_H
#define CIX_BLOSC2_ADAPTER_H

#include <blosc2.h>

#ifdef __cplusplus
extern "C" {
#endif

/* `compcode_meta` required on every CIX Blosc2 chunk. */
#define CIX_BLOSC2_ADAPTER_METADATA_V1 UINT8_C(1)
#define CIX_BLOSC2_ADAPTER_CODEC_VERSION UINT8_C(1)

/*
 * Registers the explicitly configured CIX user codec with this process's
 * Blosc2 registry.  This is intentionally explicit: applications choose when
 * registration happens and the CMake configuration chooses the codec ID.
 * Returns the upstream blosc2_register_codec result.
 */
#if defined(_WIN32)
# if defined(CIX_BLOSC2_BUILDING)
#  define CIX_BLOSC2_EXPORT __declspec(dllexport)
# else
#  define CIX_BLOSC2_EXPORT __declspec(dllimport)
# endif
#else
# define CIX_BLOSC2_EXPORT __attribute__((visibility("default")))
#endif
CIX_BLOSC2_EXPORT int cix_blosc2_register(void);

#ifdef __cplusplus
}
#endif

#endif /* CIX_BLOSC2_ADAPTER_H */
