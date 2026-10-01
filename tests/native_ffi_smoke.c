#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int32_t (*CixRead)(size_t *size, uint8_t *buffer, void *user);
typedef int32_t (*CixWrite)(size_t *size, const uint8_t *buffer, void *user);

extern int32_t cix_squash_splice(int32_t direction, int32_t level,
                                 CixRead read_cb, CixWrite write_cb,
                                 void *user);

enum { CIX_OK = 1, CIX_EOF = 3 };

struct context {
  uint8_t *input;
  size_t input_len;
  size_t input_pos;
  uint8_t *output;
  size_t output_len;
  size_t output_cap;
  size_t read_calls;
  size_t write_calls;
  size_t read_cursor;
  size_t write_cursor;
  int fail_read;
  int fail_write;
};

static const size_t read_chunks[] = {1, 7, 113, 2, 4093, 31, 8191, 5, 257};
static const size_t write_chunks[] = {3, 1, 79, 5, 4096, 13, 257};

static int32_t read_irregular(size_t *size, uint8_t *buffer, void *user) {
  struct context *ctx = user;
  ctx->read_calls++;
  if (ctx->fail_read) return -1;
  if (ctx->input_pos == ctx->input_len) {
    *size = 0;
    return CIX_EOF;
  }
  size_t want = read_chunks[ctx->read_cursor++ %
                            (sizeof(read_chunks) / sizeof(read_chunks[0]))];
  if (want > *size) want = *size;
  if (want > ctx->input_len - ctx->input_pos) want = ctx->input_len - ctx->input_pos;
  memcpy(buffer, ctx->input + ctx->input_pos, want);
  ctx->input_pos += want;
  *size = want;
  return CIX_OK;
}

static int reserve_output(struct context *ctx, size_t more) {
  if (more > SIZE_MAX - ctx->output_len) return 0;
  size_t needed = ctx->output_len + more;
  if (needed <= ctx->output_cap) return 1;
  size_t capacity = ctx->output_cap ? ctx->output_cap : 256;
  while (capacity < needed) {
    if (capacity > SIZE_MAX / 2) return 0;
    capacity *= 2;
  }
  uint8_t *next = realloc(ctx->output, capacity);
  if (!next) return 0;
  ctx->output = next;
  ctx->output_cap = capacity;
  return 1;
}

static int32_t write_irregular(size_t *size, const uint8_t *buffer, void *user) {
  struct context *ctx = user;
  ctx->write_calls++;
  if (ctx->fail_write) return -1;
  size_t want = write_chunks[ctx->write_cursor++ %
                             (sizeof(write_chunks) / sizeof(write_chunks[0]))];
  if (want > *size) want = *size;
  if (want == 0 || !reserve_output(ctx, want)) return -1;
  memcpy(ctx->output + ctx->output_len, buffer, want);
  ctx->output_len += want;
  *size = want;
  return CIX_OK;
}

static int load_file(const char *path, uint8_t **data, size_t *length) {
  FILE *file = fopen(path, "rb");
  if (!file) return 0;
  if (fseek(file, 0, SEEK_END) != 0) goto failed;
  long end = ftell(file);
  if (end < 0 || (uintmax_t)end > SIZE_MAX) goto failed;
  if (fseek(file, 0, SEEK_SET) != 0) goto failed;
  size_t len = (size_t)end;
  uint8_t *buffer = malloc(len ? len : 1);
  if (!buffer) goto failed;
  if (len && fread(buffer, 1, len, file) != len) {
    free(buffer);
    goto failed;
  }
  fclose(file);
  *data = buffer;
  *length = len;
  return 1;
failed:
  fclose(file);
  return 0;
}

static int save_file(const char *path, const uint8_t *data, size_t length) {
  FILE *file = fopen(path, "wb");
  if (!file) return 0;
  int good = !length || fwrite(data, 1, length, file) == length;
  good = good && fclose(file) == 0;
  return good;
}

static int splice_file(int direction, int level, const char *input_path,
                       const char *output_path) {
  struct context ctx = {0};
  if (!load_file(input_path, &ctx.input, &ctx.input_len)) {
    fprintf(stderr, "cannot load %s: %s\n", input_path, strerror(errno));
    return 1;
  }
  int32_t status = cix_squash_splice(direction, level, read_irregular,
                                     write_irregular, &ctx);
  int result = 0;
  if (status != CIX_OK) {
    fprintf(stderr, "splice direction=%d returned %d\n", direction, status);
    result = 1;
  } else if (!save_file(output_path, ctx.output, ctx.output_len)) {
    fprintf(stderr, "cannot save %s: %s\n", output_path, strerror(errno));
    result = 1;
  }
  printf("direction=%d level=%d status=%d input=%zu output=%zu read_callbacks=%zu write_callbacks=%zu\n",
         direction, level, status, ctx.input_len, ctx.output_len,
         ctx.read_calls, ctx.write_calls);
  free(ctx.input);
  free(ctx.output);
  return result;
}

static int make_input(const char *path) {
  const size_t length = 131071;
  uint8_t *data = malloc(length);
  if (!data) return 1;
  uint32_t state = 0x13579bdfu;
  for (size_t i = 0; i < length; i++) {
    state = state * 1664525u + 1013904223u;
    size_t phase = i % 4096;
    if (phase < 1024) data[i] = (uint8_t)('A' + (i % 4));
    else if (phase < 2048) data[i] = (uint8_t)(i >> 3);
    else if (phase < 3072) data[i] = (uint8_t)state;
    else data[i] = (uint8_t)(i % 251);
  }
  int result = save_file(path, data, length) ? 0 : 1;
  free(data);
  return result;
}

static int error_smoke(void) {
  static uint8_t input[] = {0x43, 0x49, 0x58, 0x47, 0x31, 0, 0, 0};
  struct context read_failure = {.input = input, .input_len = sizeof(input), .fail_read = 1};
  struct context write_failure = {.input = input, .input_len = sizeof(input), .fail_write = 1};
  struct context truncated = {.input = input, .input_len = sizeof(input)};
  int32_t a = cix_squash_splice(1, 6, read_irregular, write_irregular, &read_failure);
  int32_t b = cix_squash_splice(1, 6, read_irregular, write_irregular, &write_failure);
  int32_t c = cix_squash_splice(2, 6, read_irregular, write_irregular, &truncated);
  int32_t d = cix_squash_splice(1, 0, read_irregular, write_irregular, &truncated);
  printf("error_statuses read=%d write=%d truncated_decode=%d invalid_level=%d\n", a, b, c, d);
  free(read_failure.output);
  free(write_failure.output);
  free(truncated.output);
  return (a == -1 && b == -1 && c == -1 && d == -1) ? 0 : 1;
}

int main(int argc, char **argv) {
  if (argc == 3 && strcmp(argv[1], "make") == 0) return make_input(argv[2]);
  if (argc == 4 && strcmp(argv[1], "encode") == 0)
    return splice_file(1, 6, argv[2], argv[3]);
  if (argc == 4 && strcmp(argv[1], "decode") == 0)
    return splice_file(2, 6, argv[2], argv[3]);
  if (argc == 2 && strcmp(argv[1], "errors") == 0) return error_smoke();
  fprintf(stderr, "usage: %s make INPUT | encode INPUT ARCHIVE | decode ARCHIVE OUTPUT | errors\n", argv[0]);
  return 2;
}
