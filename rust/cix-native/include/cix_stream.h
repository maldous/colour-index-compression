#ifndef CIX_STREAM_H
#define CIX_STREAM_H

#include "cix.h"

#ifdef __cplusplus
extern "C" {
#endif

#define CIX_STREAM_ABI_VERSION_1 UINT32_C(1)
typedef struct cix_stream_encoder cix_stream_encoder;
typedef struct cix_stream_decoder cix_stream_decoder;
typedef enum cix_stream_state { CIX_STREAM_NEEDS_INPUT=1, CIX_STREAM_NEEDS_OUTPUT=2, CIX_STREAM_FINISHED=3 } cix_stream_state;
typedef struct cix_stream_result_v1 { size_t consumed; size_t produced; uint32_t state; } cix_stream_result_v1;

/* Native independent CIXG1 blocks only: no full-engine routes or retained-history streams.
 * Each handle is internally serialized. Destroying it concurrently with a call is invalid.
 * `result` must point to one complete writable result record and must not overlap input or
 * output; input and output must also be disjoint. NULL buffers are allowed only at length 0. */
cix_status cix_stream_encoder_create(const cix_options_v1 *, cix_stream_encoder **);
cix_status cix_stream_decoder_create(const cix_options_v1 *, cix_stream_decoder **);
void cix_stream_encoder_destroy(cix_stream_encoder *);
void cix_stream_decoder_destroy(cix_stream_decoder *);
cix_status cix_stream_encoder_process(cix_stream_encoder *, const uint8_t *, size_t, uint8_t *, size_t, cix_stream_result_v1 *);
cix_status cix_stream_decoder_process(cix_stream_decoder *, const uint8_t *, size_t, uint8_t *, size_t, cix_stream_result_v1 *);
cix_status cix_stream_encoder_flush(cix_stream_encoder *, uint8_t *, size_t, cix_stream_result_v1 *);
cix_status cix_stream_encoder_finish(cix_stream_encoder *, uint8_t *, size_t, cix_stream_result_v1 *);
cix_status cix_stream_decoder_finish(cix_stream_decoder *, uint8_t *, size_t, cix_stream_result_v1 *);
cix_status cix_stream_encoder_reset(cix_stream_encoder *);
cix_status cix_stream_decoder_reset(cix_stream_decoder *);

#ifdef __cplusplus
}
#endif
#endif
