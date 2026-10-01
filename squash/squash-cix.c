#include <squash/squash.h>
#include <stdint.h>
#include <string.h>

extern int32_t cix_squash_splice(
    int32_t direction,
    int32_t level,
    SquashReadFunc read_cb,
    SquashWriteFunc write_cb,
    void* user_data);

static SquashOptionInfo cix_options[] = {
  { "level", SQUASH_OPTION_TYPE_RANGE_INT,
    .info.range_int = { .min = 1, .max = 9 },
    .default_value.int_value = 6 },
  { NULL, SQUASH_OPTION_TYPE_NONE, }
};

static size_t cix_max_compressed_size(SquashCodec* codec, size_t input_size) {
  (void) codec;
  size_t frames = input_size / 65536 + 1;
  if (input_size > (SIZE_MAX - 128 - frames * 45) / 8) return SIZE_MAX;
  return input_size * 8 + frames * 45 + 128;
}

static SquashStatus cix_splice(SquashCodec* codec,
                               SquashOptions* options,
                               SquashStreamType stream_type,
                               SquashReadFunc read_cb,
                               SquashWriteFunc write_cb,
                               void* user_data) {
  int level = squash_options_get_int(options, codec, "level");
  int32_t result = cix_squash_splice((int32_t) stream_type, level, read_cb, write_cb, user_data);
  return result == 1 ? SQUASH_OK : squash_error(SQUASH_FAILED);
}

SQUASH_PLUGIN_EXPORT
SquashStatus squash_plugin_init_codec(SquashCodec* codec, SquashCodecImpl* impl) {
  if (strcmp(squash_codec_get_name(codec), "cix") != 0) return squash_error(SQUASH_UNABLE_TO_LOAD);
  impl->info = SQUASH_CODEC_INFO_CAN_FLUSH;
  impl->options = cix_options;
  impl->get_max_compressed_size = cix_max_compressed_size;
  impl->splice = cix_splice;
  return SQUASH_OK;
}
