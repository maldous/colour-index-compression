#include "cix_compression_manager.h"
#include <rocksdb/db.h>
#include <rocksdb/options.h>
#include <rocksdb/table_properties.h>
#include <rocksdb/table.h>
#include <array>
#include <cassert>
#include <filesystem>
#include <map>
#include <string>

int main() {
  auto path = (std::filesystem::temp_directory_path() / "cix-rocksdb-v10101-contract").string();
  std::filesystem::remove_all(path);
  auto manager = rocksdb::NewCixCompressionManagerV1(); assert(manager);
  assert(!rocksdb::NewCixCompressionManagerV1((128U << 20) + 1));
  rocksdb::Options options; options.create_if_missing = true;
  options.compression = rocksdb::kCustomCompression80; options.compression_manager = manager;
  rocksdb::BlockBasedTableOptions table_options; table_options.format_version = 7;
  options.table_factory.reset(rocksdb::NewBlockBasedTableFactory(table_options));
  options.write_buffer_size = 64U << 10;
  rocksdb::DB* db = nullptr; assert(rocksdb::DB::Open(options, path, &db).ok());
  std::string repetitive(256U << 10, 'A'), random(256U << 10, '\0'); uint32_t state = 0x12345678;
  for (char& byte : random) { state = state * 1664525U + 1013904223U; byte = static_cast<char>(state >> 24); }
  assert(db->Put(rocksdb::WriteOptions(), "repetitive", repetitive).ok());
  assert(db->Put(rocksdb::WriteOptions(), "random", random).ok());
  rocksdb::FlushOptions flush; flush.wait = true; assert(db->Flush(flush).ok());
  rocksdb::TablePropertiesCollection properties;
  assert(db->GetPropertiesOfAllTables(&properties).ok()); bool cix_sst = false;
  for (const auto& entry : properties) cix_sst |= entry.second->compression_name.find("CIX_RocksDB_Experimental_v1;80;") != std::string::npos;
  assert(cix_sst); delete db;
  // The persisted custom-codec identity requires the compatible manager on
  // reopen; a fresh ordinary RocksDB configuration must refuse the SST.
  rocksdb::Options no_manager; no_manager.create_if_missing = false;
  no_manager.compression = rocksdb::kNoCompression;
  rocksdb::BlockBasedTableOptions no_manager_table; no_manager_table.format_version = 7;
  no_manager.table_factory.reset(rocksdb::NewBlockBasedTableFactory(no_manager_table));
  rocksdb::DB* no_manager_db = nullptr;
  const auto no_manager_open = rocksdb::DB::Open(no_manager, path, &no_manager_db);
  if (no_manager_open.ok()) {
    // Some host configurations defer this compatibility check until block
    // decode.  It must still reject the custom payload without a manager.
    std::string unreadable;
    assert(!no_manager_db->Get(rocksdb::ReadOptions(), "repetitive", &unreadable).ok());
    delete no_manager_db;
  } else {
    assert(no_manager_db == nullptr);
  }
  options.create_if_missing = false; db = nullptr; assert(rocksdb::DB::Open(options, path, &db).ok());
  std::string value; assert(db->Get(rocksdb::ReadOptions(), "repetitive", &value).ok() && value == repetitive);
  assert(db->Get(rocksdb::ReadOptions(), "random", &value).ok() && value == random); delete db;
  rocksdb::CixCompressionManagerStatsV1 stats{};
  assert(rocksdb::GetCixCompressionManagerStatsV1(manager, &stats));
  assert(stats.encode_attempts && stats.cix_blocks && stats.raw_fallbacks && stats.decode_attempts);
  auto decoder = manager->GetDecompressor(); rocksdb::Decompressor::Args bad;
  bad.compression_type = rocksdb::kCustomCompression80; bad.compressed_data = rocksdb::Slice("bad", 3);
  assert(!decoder->ExtractUncompressedSize(bad).ok());
  // The length header is checked before RocksDB allocates an output buffer.
  std::array<char, 16> oversized = {'C', 'I', 'X', 'R', 1, 0, 0, 0};
  oversized[11] = 4;  // 64 MiB in little-endian header form, one byte over the cap below.
  auto limited = rocksdb::NewCixCompressionManagerV1((64U << 20) - 1); assert(limited);
  auto limited_decoder = limited->GetDecompressor(); rocksdb::Decompressor::Args oversized_args;
  oversized_args.compression_type = rocksdb::kCustomCompression80;
  oversized_args.compressed_data = rocksdb::Slice(oversized.data(), oversized.size());
  assert(!limited_decoder->ExtractUncompressedSize(oversized_args).ok());
  std::filesystem::remove_all(path);
}
