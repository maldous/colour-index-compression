#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>

#include <rocksdb/advanced_compression.h>

namespace rocksdb {

// Experimental, pinned to RocksDB v10.10.1 / commit 4595a5e.
std::shared_ptr<CompressionManager> NewCixCompressionManagerV1(
    size_t max_block_bytes = 64U << 20);
struct CixCompressionManagerStatsV1 { uint64_t encode_attempts, cix_blocks, raw_fallbacks, decode_attempts; };
bool GetCixCompressionManagerStatsV1(const std::shared_ptr<CompressionManager>&,
                                     CixCompressionManagerStatsV1* out);

}  // namespace rocksdb
