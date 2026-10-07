#pragma once
#include "CixDiscountLogMath.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>

// Causal register mixture: mode1 persistent; modes2/3 retain31/32 or127/128
// of log evidence after informative observations. No floating-point codec math.
// Native PAQ receives its original probabilities when
// updating its models; only the arithmetic coder sees the mixture. Thus the
// native information stream can be independently compared bit for bit.
class CixRegisterPrior {
  unsigned mode = 0, cursor = 0, fieldStart = 0, nameSpace = 0;
  uint32_t word = 0;
  bool active = false, field = false;
  std::array<std::array<unsigned, 32>, 2> recency{};
  std::array<unsigned, 2> used{};
  FILE* trace = nullptr;
  std::array<CixLogPosterior,2048> models{};
  std::array<uint32_t,5> predictions{};
  unsigned context = 0;
  bool learning = false;

  bool locate() {
    if (cursor < 6) return false;
    const unsigned op = word >> (cursor - 6);
    auto at = [&](unsigned start, unsigned ns = 0) {
      if (cursor < start || cursor >= start + 5) return false;
      fieldStart = start; nameSpace = ns; return true;
    };
    if ((op >= 0x08 && op <= 0x0f) || (op >= 0x20 && op <= 0x2f))
      return at(6, op >= 0x20 && op <= 0x27) || at(11);
    if (op >= 0x14 && op <= 0x17) return at(17, 1) || at(22, 1) || at(27, 1);
    if (op == 0x18) return at(22) || at(27);
    if ((op >= 0x10 && op <= 0x13) || op == 0x1c) {
      if (cursor < 7) return false;
      const bool literal = (word >> (cursor - 7)) & 1;
      return at(14) || (!literal && at(19)) || at(27);
    }
    if (op == 0x1a) return at(6) || at(11);
    // BSR's apparent PAQ Rb state is part of its address, not a register.
    if (op >= 0x30) return at(6);
    return false;
  }

public:
  CixRegisterPrior() {
    if (const char* v = std::getenv("CIX_JOINT_DISCOUNT")) {
      if (v[0] < '0' || v[0] > '3' || v[1]) throw std::runtime_error("invalid register prior mode");
      mode = v[0] - '0';
    }
    if (const char* path = std::getenv("CIX_REGISTER_BASE_TRACE")) {
      trace = std::fopen(path, "wb");
      if (!trace) throw std::runtime_error("cannot open register base trace");
    }
  }
  ~CixRegisterPrior() { if (trace) std::fclose(trace); }
  CixRegisterPrior(const CixRegisterPrior&) = delete;
  CixRegisterPrior& operator=(const CixRegisterPrior&) = delete;

  void record(uint32_t p, unsigned y) {
    if (!trace) return;
    const uint32_t value = p | (uint32_t(y) << 31);
    unsigned char bytes[4];
    for (unsigned i = 0; i < 4; ++i) bytes[i] = (value >> (8*i)) & 255;
    if (std::fwrite(bytes, 1, 4, trace) != 4) throw std::runtime_error("register trace write failed");
  }

  uint32_t mix(uint32_t p, bool alpha, uint32_t blockPos, unsigned bitPos) {
    active = alpha; field = false; learning = false;
    if (!active) return p;
    if (blockPos == 0 && bitPos == 0) {
      cursor = word = 0; used.fill(0);
      for (auto& model : models) model.reset(false);
    }
    if (cursor != (blockPos % 4) * 8 + bitPos) throw std::runtime_error("register cursor mismatch");
    field = locate();
    if (!field || !mode || p < (1u << 26) || p > 31u*(1u << 26)) return p;
    unsigned masses[32]; std::fill(masses, masses + 32, 1u);
    for (unsigned rank = 0; rank < used[nameSpace]; ++rank)
      masses[recency[nameSpace][rank]] = std::max(1u, 256u >> rank);
    const unsigned bits = cursor - fieldStart;
    const unsigned prefix = word & ((1u << bits) - 1);
    const unsigned low = prefix << (5-bits), middle = low + (1u << (4-bits)), high = low + (1u << (5-bits));
    unsigned total = 0, ones = 0;
    for (unsigned i = low; i < high; ++i) { total += masses[i]; if (i >= middle) ones += masses[i]; }
    const uint64_t q = (uint64_t(ones) << 31) / total;
    context = (word >> (cursor-6))*32 + fieldStart;
    predictions[0] = p;
    const unsigned denominators[4] = {128,32,8,2};
    for (unsigned i = 0; i < 4; ++i) {
      const unsigned d = denominators[i];
      predictions[i+1] = uint32_t(((d-1)*uint64_t(p) + q + d/2) / d);
    }
    learning = true;
    return models[context].mix(predictions);
  }

  void observe(unsigned y) {
    if (!active) return;
    if (learning) models[context].observe(predictions,y,mode == 2 ? 5 : mode == 3 ? 7 : 0);
    word = (word << 1) | y; ++cursor;
    if (field && cursor == fieldStart + 5) {
      const unsigned value = word & 31;
      auto& row = recency[nameSpace]; auto& n = used[nameSpace];
      unsigned pos = 0;
      while (pos < n && row[pos] != value) ++pos;
      if (pos == n) ++n;
      for (unsigned i = pos; i > 0; --i) row[i] = row[i-1];
      row[0] = value;
    }
    if (cursor == 32) { word = 0; cursor = 0; }
  }
};
