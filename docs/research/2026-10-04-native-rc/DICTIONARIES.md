# Native Zstd dictionaries

`dictionaries.rs` owns trained dictionary bytes and exposes ordinary Zstd
payloads only. Its identity is the library dictionary ID plus SHA-256. A
nonzero frame ID must match; ID 0 is not trusted as an identity and requires
the caller's separately declared SHA-256. No CIX framing extension is added.

Training uses `ZDICT_trainFromBuffer`, which upstream documents as about 6 MiB
working memory; the module additionally requires total samples ×6 within the
caller budget. Encode/decode use CDict/DDict and bounded output buffers.
Root must run the small contract fixture against the staged libzstd before
registering the module.

The initial qualification binds the installed system libzstd ABI. It requires
exported `ZSTD_estimateCCtxSize`, `ZSTD_estimateCDictSize`,
`ZSTD_estimateDCtxSize`, and `ZSTD_estimateDDictSize`; these are static API
entries in the pinned headers and were read back as dynamic exports before
source use. Their returned estimates are charged before native handles are
created. This is an admission estimate, not a hard RSS guarantee.
