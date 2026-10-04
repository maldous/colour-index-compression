#include "cix_jxl_bridge.h"

#include <jxl/decode.h>
#include <jxl/encode.h>
#include <jxl/thread_parallel_runner.h>

#include <algorithm>
#include <cstring>
#include <exception>
#include <limits>
#include <new>
#include <vector>

namespace {

class Encoder final {
 public:
  Encoder() : encoder_(JxlEncoderCreate(nullptr)), runner_(nullptr) {
    if (encoder_ != nullptr) {
      runner_ = JxlThreadParallelRunnerCreate(nullptr, 1);
    }
  }
  ~Encoder() {
    if (runner_ != nullptr) JxlThreadParallelRunnerDestroy(runner_);
    if (encoder_ != nullptr) JxlEncoderDestroy(encoder_);
  }
  JxlEncoder* get() const { return encoder_; }
  void* runner() const { return runner_; }

 private:
  JxlEncoder* encoder_;
  void* runner_;
};

class Decoder final {
 public:
  Decoder() : decoder_(JxlDecoderCreate(nullptr)), runner_(nullptr) {
    if (decoder_ != nullptr) {
      runner_ = JxlThreadParallelRunnerCreate(nullptr, 1);
    }
  }
  ~Decoder() {
    if (runner_ != nullptr) JxlThreadParallelRunnerDestroy(runner_);
    if (decoder_ != nullptr) JxlDecoderDestroy(decoder_);
  }
  JxlDecoder* get() const { return decoder_; }
  void* runner() const { return runner_; }

 private:
  JxlDecoder* decoder_;
  void* runner_;
};

bool checked_product(uint32_t width, uint32_t height, size_t sample_bytes,
                     size_t* result) {
  if (width == 0 || height == 0 || sample_bytes == 0) return false;
  const size_t w = static_cast<size_t>(width);
  const size_t h = static_cast<size_t>(height);
  if (w > std::numeric_limits<size_t>::max() / h) return false;
  const size_t pixels = w * h;
  if (pixels > std::numeric_limits<size_t>::max() / sample_bytes) return false;
  *result = pixels * sample_bytes;
  return true;
}

bool valid_sample(uint32_t bits, uint32_t sample_type, size_t* sample_bytes,
                  JxlDataType* data_type) {
  if (bits == 0 || bits > 16) return false;
  if (sample_type == CIX_JXL_UINT8 && bits <= 8) {
    *sample_bytes = 1;
    *data_type = JXL_TYPE_UINT8;
    return true;
  }
  if (sample_type == CIX_JXL_UINT16 && bits > 8) {
    *sample_bytes = 2;
    *data_type = JXL_TYPE_UINT16;
    return true;
  }
  return false;
}

JxlPixelFormat gray_format(JxlDataType type) {
  // CIX image regions are byte streams: keep UINT16 input/output explicitly
  // little-endian instead of making archive meaning depend on the host.
  const JxlEndianness endianness =
      type == JXL_TYPE_UINT16 ? JXL_LITTLE_ENDIAN : JXL_NATIVE_ENDIAN;
  return JxlPixelFormat{1, type, endianness, 0};
}

int encoder_status(const Encoder& encoder, JxlEncoderStatus status) {
  if (status != JXL_ENC_ERROR) return CIX_JXL_ENCODE_FAILURE;
  return JxlEncoderGetError(encoder.get()) == JXL_ENC_ERR_OOM
             ? CIX_JXL_ALLOCATION_FAILURE
             : CIX_JXL_ENCODE_FAILURE;
}

bool supported_info(const JxlBasicInfo& info, uint32_t width, uint32_t height,
                    uint32_t bits) {
  return info.xsize == width && info.ysize == height &&
         info.bits_per_sample == bits && info.exponent_bits_per_sample == 0 &&
         info.num_color_channels == 1 && info.num_extra_channels == 0 &&
         info.alpha_bits == 0 && info.have_animation == JXL_FALSE &&
         info.have_preview == JXL_FALSE && info.orientation == JXL_ORIENT_IDENTITY;
}

int set_decoder_buffer(Decoder* decoder, const JxlPixelFormat& format,
                       uint32_t bits_per_sample, uint8_t* output,
                       size_t output_size) {
  size_t required = 0;
  if (JxlDecoderImageOutBufferSize(decoder->get(), &format, &required) !=
          JXL_DEC_SUCCESS ||
      required != output_size) {
    return CIX_JXL_UNSUPPORTED;
  }
  if (JxlDecoderSetImageOutBuffer(decoder->get(), &format, output,
                                  output_size) != JXL_DEC_SUCCESS) {
    return CIX_JXL_DECODE_FAILURE;
  }
  const JxlBitDepth bit_depth = {JXL_BIT_DEPTH_FROM_CODESTREAM,
                                 bits_per_sample, 0};
  return JxlDecoderSetImageOutBitDepth(decoder->get(), &bit_depth) ==
                 JXL_DEC_SUCCESS
             ? CIX_JXL_OK
             : CIX_JXL_DECODE_FAILURE;
}

}  // namespace

extern "C" int cix_jxl_encode_gray_2d(const cix_jxl_gray_image* image,
                                       size_t max_output_bytes,
                                       cix_jxl_buffer* output) {
  if (output == nullptr) return CIX_JXL_INVALID_ARGUMENT;
  output->data = nullptr;
  output->size = 0;
  if (image == nullptr || image->pixels == nullptr || max_output_bytes == 0 ||
      image->effort < 1 || image->effort > 10) {
    return CIX_JXL_INVALID_ARGUMENT;
  }

  size_t sample_bytes = 0;
  JxlDataType data_type;
  size_t expected_input = 0;
  if (!valid_sample(image->bits_per_sample, image->sample_type, &sample_bytes,
                    &data_type) ||
      !checked_product(image->width, image->height, sample_bytes,
                       &expected_input) ||
      image->pixels_size != expected_input) {
    return CIX_JXL_INVALID_ARGUMENT;
  }

  try {
    Encoder encoder;
    if (encoder.get() == nullptr || encoder.runner() == nullptr) {
      return CIX_JXL_ALLOCATION_FAILURE;
    }
    if (JxlEncoderSetParallelRunner(encoder.get(), JxlThreadParallelRunner,
                                    encoder.runner()) != JXL_ENC_SUCCESS) {
      return CIX_JXL_ENCODE_FAILURE;
    }

    JxlBasicInfo info;
    JxlEncoderInitBasicInfo(&info);
    info.xsize = image->width;
    info.ysize = image->height;
    info.bits_per_sample = image->bits_per_sample;
    info.exponent_bits_per_sample = 0;
    info.num_color_channels = 1;
    info.num_extra_channels = 0;
    info.uses_original_profile = JXL_TRUE;
    if (JxlEncoderSetBasicInfo(encoder.get(), &info) != JXL_ENC_SUCCESS) {
      return CIX_JXL_ENCODE_FAILURE;
    }

    JxlColorEncoding color;
    JxlColorEncodingSetToSRGB(&color, JXL_TRUE);
    if (JxlEncoderSetColorEncoding(encoder.get(), &color) != JXL_ENC_SUCCESS) {
      return CIX_JXL_ENCODE_FAILURE;
    }

    JxlEncoderFrameSettings* settings =
        JxlEncoderFrameSettingsCreate(encoder.get(), nullptr);
    const JxlBitDepth bit_depth = {JXL_BIT_DEPTH_FROM_CODESTREAM,
                                   image->bits_per_sample, 0};
    if (settings == nullptr ||
        JxlEncoderSetFrameBitDepth(settings, &bit_depth) != JXL_ENC_SUCCESS ||
        JxlEncoderFrameSettingsSetOption(settings,
                                          JXL_ENC_FRAME_SETTING_EFFORT,
                                          image->effort) != JXL_ENC_SUCCESS ||
        JxlEncoderSetFrameLossless(settings, JXL_TRUE) != JXL_ENC_SUCCESS ||
        JxlEncoderSetFrameDistance(settings, 0.0f) != JXL_ENC_SUCCESS) {
      return CIX_JXL_ENCODE_FAILURE;
    }

    const JxlPixelFormat format = gray_format(data_type);
    if (JxlEncoderAddImageFrame(settings, &format, image->pixels,
                                image->pixels_size) != JXL_ENC_SUCCESS) {
      return CIX_JXL_ENCODE_FAILURE;
    }
    JxlEncoderCloseInput(encoder.get());

    std::vector<uint8_t> encoded;
    encoded.reserve(std::min(max_output_bytes, static_cast<size_t>(4096)));
    uint8_t scratch[4096];
    for (;;) {
      uint8_t* next = scratch;
      size_t available = sizeof(scratch);
      const JxlEncoderStatus status =
          JxlEncoderProcessOutput(encoder.get(), &next, &available);
      const size_t produced = sizeof(scratch) - available;
      if (produced > max_output_bytes - encoded.size()) {
        return CIX_JXL_OUTPUT_LIMIT;
      }
      encoded.insert(encoded.end(), scratch, next);
      if (status == JXL_ENC_SUCCESS) break;
      if (status != JXL_ENC_NEED_MORE_OUTPUT) return encoder_status(encoder, status);
    }

    uint8_t* allocated = new uint8_t[encoded.size()];
    std::memcpy(allocated, encoded.data(), encoded.size());
    output->data = allocated;
    output->size = encoded.size();
    return CIX_JXL_OK;
  } catch (const std::bad_alloc&) {
    return CIX_JXL_ALLOCATION_FAILURE;
  } catch (...) {
    return CIX_JXL_EXCEPTION;
  }
}

extern "C" int cix_jxl_decode_gray_2d(
    const uint8_t* input, size_t input_size, uint32_t expected_width,
    uint32_t expected_height, uint32_t expected_bits_per_sample,
    uint32_t expected_sample_type, uint8_t* output, size_t output_size) {
  if (input == nullptr || input_size == 0 || output == nullptr) {
    return CIX_JXL_INVALID_ARGUMENT;
  }
  size_t sample_bytes = 0;
  JxlDataType data_type;
  size_t expected_output = 0;
  if (!valid_sample(expected_bits_per_sample, expected_sample_type,
                    &sample_bytes, &data_type) ||
      !checked_product(expected_width, expected_height, sample_bytes,
                       &expected_output) ||
      output_size != expected_output) {
    return CIX_JXL_INVALID_ARGUMENT;
  }

  try {
    Decoder decoder;
    if (decoder.get() == nullptr || decoder.runner() == nullptr) {
      return CIX_JXL_ALLOCATION_FAILURE;
    }
    if (JxlDecoderSetParallelRunner(decoder.get(), JxlThreadParallelRunner,
                                    decoder.runner()) != JXL_DEC_SUCCESS ||
        JxlDecoderSubscribeEvents(decoder.get(), JXL_DEC_BASIC_INFO) !=
            JXL_DEC_SUCCESS ||
        JxlDecoderSetInput(decoder.get(), input, input_size) != JXL_DEC_SUCCESS) {
      return CIX_JXL_DECODE_FAILURE;
    }
    JxlDecoderCloseInput(decoder.get());

    const JxlPixelFormat format = gray_format(data_type);
    bool basic_info_seen = false;
    bool image_buffer_set = false;
    for (;;) {
      const JxlDecoderStatus status = JxlDecoderProcessInput(decoder.get());
      if (status == JXL_DEC_BASIC_INFO) {
        JxlBasicInfo info;
        if (JxlDecoderGetBasicInfo(decoder.get(), &info) != JXL_DEC_SUCCESS ||
            !supported_info(info, expected_width, expected_height,
                            expected_bits_per_sample)) {
          return CIX_JXL_UNSUPPORTED;
        }
        basic_info_seen = true;
        continue;
      }
      if (status == JXL_DEC_NEED_IMAGE_OUT_BUFFER) {
        if (!basic_info_seen || image_buffer_set) return CIX_JXL_UNSUPPORTED;
        const int result =
            set_decoder_buffer(&decoder, format, expected_bits_per_sample,
                               output, output_size);
        if (result != CIX_JXL_OK) return result;
        image_buffer_set = true;
        continue;
      }
      if (status == JXL_DEC_SUCCESS) {
        if (!basic_info_seen || !image_buffer_set ||
            JxlDecoderReleaseInput(decoder.get()) != 0) {
          return CIX_JXL_DECODE_FAILURE;
        }
        return CIX_JXL_OK;
      }
      if (status == JXL_DEC_ERROR) return CIX_JXL_DECODE_FAILURE;
      return CIX_JXL_DECODE_FAILURE;
    }
  } catch (const std::bad_alloc&) {
    return CIX_JXL_ALLOCATION_FAILURE;
  } catch (...) {
    return CIX_JXL_EXCEPTION;
  }
}

extern "C" void cix_jxl_free_buffer(cix_jxl_buffer* buffer) {
  if (buffer == nullptr) return;
  delete[] buffer->data;
  buffer->data = nullptr;
  buffer->size = 0;
}

extern "C" uint32_t cix_jxl_library_version(void) {
  return JxlEncoderVersion();
}

extern "C" const char* cix_jxl_bridge_version(void) {
  return "cix-jxl-gray2d-bridge/1";
}
