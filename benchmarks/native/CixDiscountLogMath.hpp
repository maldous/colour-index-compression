#pragma once
#include "CixLogTables.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <stdexcept>

namespace cix_log_math {
static constexpr int64_t SCALE = INT64_C(1) << 20;

inline int64_t logProbability(uint32_t p) {
  if (p == 0 || p > (UINT32_C(1) << 31)) throw std::runtime_error("invalid log probability");
  const unsigned exponent = 31u - unsigned(__builtin_clz(p));
  const uint64_t mantissa = (uint64_t(p) << 30) >> exponent;
  const uint32_t fraction = uint32_t(mantissa - (UINT64_C(1) << 30));
  const unsigned index = fraction >> 18, remainder = fraction & ((1u << 18) - 1);
  const uint64_t interpolated = LOG2_MANTISSA[index] +
    ((uint64_t(LOG2_MANTISSA[index+1] - LOG2_MANTISSA[index]) * remainder + (1u << 17)) >> 18);
  return (int64_t(exponent) - 31) * SCALE + int64_t((interpolated + 512) >> 10);
}

inline uint64_t codingWeight(uint64_t deficit) {
  const uint64_t whole = deficit >> 20;
  if (whole >= 64) return 0;
  const unsigned fraction = unsigned(deficit & ((1u << 20) - 1));
  const unsigned index = fraction >> 8, remainder = fraction & 255;
  const uint64_t interpolated = EXP2_NEGATIVE[index] -
    (((EXP2_NEGATIVE[index] - EXP2_NEGATIVE[index+1]) * remainder + 128) >> 8);
  if (whole == 0) return interpolated;
  return (interpolated + (UINT64_C(1) << (whole-1))) >> whole;
}
}

class CixLogPosterior {
  std::array<int64_t,5> scores{};
public:
  void reset(bool nativeBias) { scores.fill(0); if (nativeBias) scores[0] = 3 * cix_log_math::SCALE; }
  uint32_t mix(const std::array<uint32_t,5>& predictions) const {
    const int64_t top = *std::max_element(scores.begin(),scores.end());
    uint64_t total = 0; unsigned __int128 weighted = 0;
    for (unsigned i = 0; i < 5; ++i) {
      const uint64_t weight = cix_log_math::codingWeight(uint64_t(top-scores[i]));
      total += weight; weighted += static_cast<unsigned __int128>(weight) * predictions[i];
    }
    const uint64_t result = uint64_t((weighted + total/2) / total);
    return uint32_t(std::max(uint64_t(1),std::min(uint64_t(0x7fffffff),result)));
  }
  void observe(const std::array<uint32_t,5>& predictions,unsigned y,unsigned discountShift=0) {
    if (std::all_of(predictions.begin(),predictions.end(),[&](uint32_t p){return p==predictions[0];})) return;
    for (unsigned i = 0; i < 5; ++i)
      scores[i] += cix_log_math::logProbability(y ? predictions[i] : (UINT32_C(1)<<31)-predictions[i]);
    const int64_t top = *std::max_element(scores.begin(),scores.end());
    for (auto& score : scores) score -= top;
    if (discountShift) {
      if (discountShift != 5 && discountShift != 7) throw std::runtime_error("invalid discount shift");
      const uint64_t denominator = UINT64_C(1) << discountShift;
      for (auto& score : scores) {
        const uint64_t penalty = uint64_t(-score);
        score = -int64_t((penalty*(denominator-1) + denominator/2) / denominator);
      }
    }
  }
};
