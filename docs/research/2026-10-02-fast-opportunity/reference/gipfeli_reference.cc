// Standalone reference wrapper for the Squash v0.7 Gipfeli plugin.
// It deliberately invokes the same no-option Stream API as
// plugins/gipfeli/squash-gipfeli.cpp.
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

#if defined(GIPFELI_SAFE_COPY_ONLY)
#include "gipfeli-safe-copy-only/gipfeli.h"
#elif defined(GIPFELI_READBITS_GUARD)
#include "gipfeli-readbits-guard/gipfeli.h"
#elif defined(GIPFELI_LATEST_04FE241)
#include "gipfeli-latest-04fe241/gipfeli.h"
#elif defined(GIPFELI_SAFE_SCALAR)
#include "gipfeli-safe-scalar/gipfeli.h"
#elif defined(GIPFELI_STREAM_LIFETIME_PATCH)
#include "gipfeli-stream-lifetime-fix/gipfeli.h"
#else
#include "gipfeli/gipfeli.h"
#endif

namespace {

bool ReadFile(const char* path, std::string* out) {
  std::ifstream in(path, std::ios::binary);
  if (!in) {
    std::cerr << "gipfeli-reference: cannot open " << path << ": "
              << std::strerror(errno) << "\n";
    return false;
  }
  out->assign(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
  // istreambuf_iterator reaches its end on either eofbit or failbit.  A
  // completed binary read may therefore have failbit set even though the
  // bytes were read correctly; only badbit denotes an I/O error here.
  if (in.bad()) {
    std::cerr << "gipfeli-reference: cannot read " << path << "\n";
    return false;
  }
  return true;
}

bool WriteFile(const char* path, const char* data, size_t size) {
  std::ofstream out(path, std::ios::binary | std::ios::trunc);
  if (!out) {
    std::cerr << "gipfeli-reference: cannot create " << path << ": "
              << std::strerror(errno) << "\n";
    return false;
  }
  out.write(data, static_cast<std::streamsize>(size));
  if (!out) {
    std::cerr << "gipfeli-reference: cannot write " << path << "\n";
    return false;
  }
  return true;
}

void Usage() {
  std::cerr << "usage: gipfeli-reference encode INPUT OUTPUT\n"
            << "       gipfeli-reference decode ARCHIVE RESTORED\n";
}

// Gipfeli's supplied UncheckedByteArraySink does not expose its current
// destination.  This sink implements the actual Sink virtual method and
// records every accepted byte, so a preallocated MaxCompressedLength buffer
// never becomes the physical archive length.
class TrackingByteArraySink : public util::compression::Sink {
 public:
  TrackingByteArraySink(char* begin, size_t capacity)
      : begin_(begin), dest_(begin), end_(begin + capacity) {}

  virtual void Append(const char* data, size_t n) {
    if (n > Remaining()) throw std::overflow_error("output buffer too small");
    if (data != dest_) std::memcpy(dest_, data, n);
    dest_ += n;
  }

  virtual char* GetAppendBuffer(size_t min_size, size_t,
                                char*, size_t, size_t* allocated_size) {
    if (min_size > Remaining()) throw std::overflow_error("output buffer too small");
    *allocated_size = Remaining();
    return dest_;
  }

  size_t Size() const { return static_cast<size_t>(dest_ - begin_); }

 private:
  size_t Remaining() const { return static_cast<size_t>(end_ - dest_); }

  char* begin_;
  char* dest_;
  char* end_;
};

int Encode(const char* input_path, const char* output_path) {
  std::string input;
  if (!ReadFile(input_path, &input)) return 1;
  util::compression::Compressor* compressor =
      util::compression::NewGipfeliCompressor();
  if (compressor == NULL) {
    std::cerr << "gipfeli-reference: cannot create compressor\n";
    return 1;
  }
#if defined(GIPFELI_BUFFER_API)
  std::string compressed;
  const size_t size = compressor->Compress(input, &compressed);
  delete compressor;
  if (size != compressed.size() || (size == 0 && !input.empty())) {
    std::cerr << "gipfeli-reference: compression failed\n";
    return 1;
  }
  return WriteFile(output_path, compressed.data(), size) ? 0 : 1;
#else
  const size_t max_size = compressor->MaxCompressedLength(input.size());
  std::vector<char> compressed(max_size == 0 ? 1 : max_size);
  util::compression::ByteArraySource source(input.data(), input.size());
  TrackingByteArraySink sink(compressed.data(), compressed.size());
  const size_t stream_size = compressor->CompressStream(&source, &sink);
  delete compressor;
  const size_t size = sink.Size();
  if (stream_size != size || (size == 0 && !input.empty())) {
    std::cerr << "gipfeli-reference: compression failed\n";
    return 1;
  }
  return WriteFile(output_path, compressed.data(), size) ? 0 : 1;
#endif
}

int Decode(const char* input_path, const char* output_path) {
  std::string compressed;
  if (!ReadFile(input_path, &compressed)) return 1;
  util::compression::Compressor* compressor =
      util::compression::NewGipfeliCompressor();
  if (compressor == NULL) {
    std::cerr << "gipfeli-reference: cannot create compressor\n";
    return 1;
  }
#if defined(GIPFELI_BUFFER_API)
  std::string output;
  const bool ok = compressor->Uncompress(compressed, &output);
  delete compressor;
  if (!ok) {
    std::cerr << "gipfeli-reference: invalid archive\n";
    return 1;
  }
  return WriteFile(output_path, output.data(), output.size()) ? 0 : 1;
#else
  size_t uncompressed_size = 0;
  if (!compressor->GetUncompressedLength(compressed, &uncompressed_size)) {
    std::cerr << "gipfeli-reference: invalid archive length\n";
    delete compressor;
    return 1;
  }
  std::vector<char> output(uncompressed_size == 0 ? 1 : uncompressed_size);
  util::compression::ByteArraySource source(compressed.data(), compressed.size());
  TrackingByteArraySink sink(output.data(), output.size());
  const bool ok = compressor->UncompressStream(&source, &sink);
  delete compressor;
  if (!ok || sink.Size() != uncompressed_size) {
    std::cerr << "gipfeli-reference: invalid archive\n";
    return 1;
  }
  return WriteFile(output_path, output.data(), sink.Size()) ? 0 : 1;
#endif
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 4) {
    Usage();
    return 2;
  }
  if (std::strcmp(argv[1], "encode") == 0) return Encode(argv[2], argv[3]);
  if (std::strcmp(argv[1], "decode") == 0) return Decode(argv[2], argv[3]);
  Usage();
  return 2;
}
