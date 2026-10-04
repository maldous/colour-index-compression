/* CIX-owned worker-only boundary for the unchanged PAQ store_state sources. */
#ifndef CIX_PAQ_STORE_STATE_BRIDGE_H
#define CIX_PAQ_STORE_STATE_BRIDGE_H

#include <stddef.h>

#if defined(_WIN32)
#  if defined(CIX_PAQ_STORE_STATE_BUILDING)
#    define CIX_PAQ_STORE_STATE_API __declspec(dllexport)
#  else
#    define CIX_PAQ_STORE_STATE_API __declspec(dllimport)
#  endif
#else
#  define CIX_PAQ_STORE_STATE_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

enum cix_paq_store_state_status {
    CIX_PAQ_STORE_STATE_OK = 0,
    CIX_PAQ_STORE_STATE_INVALID_ARGUMENT = 1,
    CIX_PAQ_STORE_STATE_ALREADY_USED = 2,
    CIX_PAQ_STORE_STATE_UPSTREAM_FAILURE = 3,
    CIX_PAQ_STORE_STATE_EXCEPTION = 4
};

/*
 * Invoke PAQ store_state's unchanged command-line implementation exactly once in an
 * isolated CIX worker. `argv` is passed verbatim to processCommandLine.
 * `expected_output` must name a non-existent ordinary output file before the
 * call and is checked after it. This converts PAQ's intentional-error return
 * convention (which can be zero) into a stable status for the worker.
 *
 * The CIX bridge itself does not fork, call exit, change environment variables,
 * or install signal/resource handlers. Upstream PAQ contains LSTM error paths
 * that call exit(1), so this API is deliberately unsuitable for a native SDK:
 * PAQ store_state retains process-lifetime static model state. The caller owns the
 * isolated same-CIX worker, directory, environment, rlimits and cancellation.
 */
CIX_PAQ_STORE_STATE_API int cix_paq_store_state_process(
    int argc,
    const char *const argv[],
    const char *expected_output,
    char *error_buffer,
    size_t error_buffer_size
);

CIX_PAQ_STORE_STATE_API const char *cix_paq_store_state_bridge_version(void);

#ifdef __cplusplus
}
#endif
#endif
