//! Bounded CIXB1 reference-backend envelope codecs.
use flate2::{bufread::GzDecoder, Compression, GzBuilder};
use sha2::{Digest, Sha256};
use std::ffi::{c_char, c_int, c_uint, c_void, CStr};
use std::io::{Cursor, Read, Write};

// CIXB1 direct backends may call a native one-shot implementation.  The
// shared flag is observed before and after those calls; one-shot libraries
// cannot be preempted safely in the middle of a call.
#[inline]
fn check_cancel() -> Result<(), String> {
    crate::limits::check()
}

// Match the existing Python CIXB1 envelope limit. The payload length is
// stored as u32, so this remains comfortably within the on-disk format.
pub const MAX_INPUT: usize = 64 * 1024 * 1024;
pub const MAX_PAYLOAD: usize = MAX_INPUT + 1024 * 1024;
const HEADER: usize = 47;
/// bzip2, Brotli and zstd use their stable one-shot APIs in this bounded
/// envelope.  Cancellation is observed immediately before and after each
/// call, so interruption latency can be one native call. XZ encoding is
/// incrementally polled per 64 KiB output chunk; its existing bounded decode
/// ABI remains one-shot. Replacing the former APIs with streaming state
/// machines is a separate compatibility/performance change and must be
/// measured before it is claimed as an improvement.
pub const ONE_SHOT_CANCELLATION_LIMITATION: &str =
    "bzip2/Brotli/zstd and XZ decode use one-shot native calls with before/after cancellation checks; XZ encode polls per 64 KiB output chunk";

#[link(name = "bz2")]
unsafe extern "C" {
    fn BZ2_bzBuffToBuffCompress(
        dest: *mut c_char,
        dest_len: *mut c_uint,
        source: *mut c_char,
        source_len: c_uint,
        block_size_100k: c_int,
        verbosity: c_int,
        work_factor: c_int,
    ) -> c_int;
    fn BZ2_bzDecompressInit(stream: *mut BzStream, verbosity: c_int, small: c_int) -> c_int;
    fn BZ2_bzDecompress(stream: *mut BzStream) -> c_int;
    fn BZ2_bzDecompressEnd(stream: *mut BzStream) -> c_int;
    fn BZ2_bzlibVersion() -> *const c_char;
}

#[link(name = "z")]
unsafe extern "C" {
    fn zlibVersion() -> *const c_char;
}
#[repr(C)]
struct BzStream {
    next_in: *mut c_char,
    avail_in: c_uint,
    total_in_lo32: c_uint,
    total_in_hi32: c_uint,
    next_out: *mut c_char,
    avail_out: c_uint,
    total_out_lo32: c_uint,
    total_out_hi32: c_uint,
    state: *mut c_void,
    bzalloc: Option<unsafe extern "C" fn(*mut c_void, c_int, c_int) -> *mut c_void>,
    bzfree: Option<unsafe extern "C" fn(*mut c_void, *mut c_void)>,
    opaque: *mut c_void,
}

#[link(name = "lzma")]
unsafe extern "C" {
    fn lzma_stream_buffer_bound(uncompressed_size: usize) -> usize;
    fn lzma_easy_encoder_memusage(preset: u32) -> u64;
    fn lzma_raw_encoder_memusage(filters: *const LzmaFilter) -> u64;
    fn lzma_easy_encoder(stream: *mut LzmaStream, preset: u32, check: u32) -> c_int;
    fn lzma_stream_encoder(stream: *mut LzmaStream, filters: *mut LzmaFilter, check: u32) -> c_int;
    fn lzma_lzma_preset(options: *mut LzmaOptionsLzma, preset: u32) -> c_int;
    fn lzma_code(stream: *mut LzmaStream, action: c_int) -> c_int;
    fn lzma_end(stream: *mut LzmaStream);
    fn lzma_stream_buffer_decode(
        memlimit: *mut u64,
        flags: u32,
        allocator: *const c_void,
        input: *const u8,
        input_pos: *mut usize,
        input_size: usize,
        output: *mut u8,
        output_pos: *mut usize,
        output_size: usize,
    ) -> u32;
    fn lzma_version_string() -> *const c_char;
}

// ABI layout from liblzma's lzma_stream. Streaming encode leaves the XZ block
// size unknown, matching Python's canonical liblzma stream output.
#[repr(C)]
struct LzmaStream {
    next_in: *const u8,
    avail_in: usize,
    total_in: u64,
    next_out: *mut u8,
    avail_out: usize,
    total_out: u64,
    allocator: *const c_void,
    internal: *mut c_void,
    reserved_ptr1: *mut c_void,
    reserved_ptr2: *mut c_void,
    reserved_ptr3: *mut c_void,
    reserved_ptr4: *mut c_void,
    seek_pos: u64,
    reserved_int2: u64,
    reserved_int3: usize,
    reserved_int4: usize,
    reserved_enum1: c_int,
    reserved_enum2: c_int,
}

impl Drop for LzmaStream {
    fn drop(&mut self) {
        // lzma_end accepts the initialized zero/null stream too. This also
        // releases native state on a cooperative cancellation or deadline.
        unsafe { lzma_end(self) };
    }
}

#[repr(C)]
struct LzmaOptionsLzma {
    dict_size: u32,
    preset_dict: *const u8,
    preset_dict_size: u32,
    lc: u32,
    lp: u32,
    pb: u32,
    mode: c_int,
    nice_len: u32,
    mf: c_int,
    depth: u32,
    ext_flags: u32,
    ext_size_low: u32,
    ext_size_high: u32,
    reserved_int4: u32,
    reserved_int5: u32,
    reserved_int6: u32,
    reserved_int7: u32,
    reserved_int8: u32,
    reserved_enum1: c_int,
    reserved_enum2: c_int,
    reserved_enum3: c_int,
    reserved_enum4: c_int,
    reserved_ptr1: *mut c_void,
    reserved_ptr2: *mut c_void,
}

#[repr(C)]
struct LzmaFilter {
    id: u64,
    options: *mut c_void,
}

#[link(name = "zstd")]
unsafe extern "C" {
    fn ZSTD_compressBound(src_size: usize) -> usize;
    fn ZSTD_compress(
        dst: *mut c_void,
        dst_capacity: usize,
        src: *const c_void,
        src_size: usize,
        level: c_int,
    ) -> usize;
    fn ZSTD_decompress(
        dst: *mut c_void,
        dst_capacity: usize,
        src: *const c_void,
        src_size: usize,
    ) -> usize;
    fn ZSTD_findFrameCompressedSize(src: *const c_void, src_size: usize) -> usize;
    fn ZSTD_isError(code: usize) -> u32;
    fn ZSTD_getErrorName(code: usize) -> *const c_char;
    // This is declared as a static-only API by zstd because callers that
    // dynamically load zstd cannot rely on it.  CIX links to zstd directly,
    // and the installed shared library exports it, so it is the appropriate
    // estimator for our one-shot `ZSTD_compress` call.
    fn ZSTD_estimateCCtxSize(compression_level: c_int) -> usize;
    fn ZSTD_versionString() -> *const c_char;
}

/// A legal, already implemented direct CIXB1 backend configuration.
///
/// These descriptors are deliberately configuration-level rather than just
/// backend-level.  For example, `xz-size-9e` and `xz-dict128-preset6` have
/// different encoder state and can produce different complete archives.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CandidateDescriptor {
    pub id: &'static str,
    pub backend: &'static str,
    pub profile: &'static str,
    pub config: CandidateConfig,
}

/// Extra configuration carried by a CIXB1 candidate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CandidateConfig {
    /// The canonical `encode(backend, profile, input)` configuration.
    Canonical,
    /// An existing XZ stream with a 128 MiB dictionary and an explicit preset.
    XzDictionary { dictionary_bytes: u32, preset: u32 },
    /// Brotli's generic encoder mode.  Quality/window affect encoding only;
    /// the emitted Brotli payload carries the decoder-relevant window and is
    /// enclosed in the regular CIXB1 backend/profile envelope.  No custom or
    /// source-specific dictionary is supplied.
    BrotliQuality {
        quality: u8,
        lgwin: u8,
        mode: BrotliMode,
    },
}

/// Brotli's mode is typed so a future text/font setting cannot silently be
/// selected under a generic candidate identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BrotliMode {
    Generic,
}

/// Why a complete CIXB1 candidate could not be admitted under the caller's
/// remaining budget.  It is structured so explain output never turns a
/// resource omission into a silent portfolio gap.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CandidateOmission {
    pub needed_bytes: usize,
    pub available_bytes: usize,
    pub reason: String,
}

const CIXB1_BEST_CANDIDATES: &[CandidateDescriptor] = &[
    CandidateDescriptor {
        id: "gzip-fast",
        backend: "gzip",
        profile: "fast",
        config: CandidateConfig::Canonical,
    },
    // gzip's default settings equal its size settings.  The `size` envelope
    // is retained as the single deterministic representative.
    CandidateDescriptor {
        id: "gzip-size",
        backend: "gzip",
        profile: "size",
        config: CandidateConfig::Canonical,
    },
    CandidateDescriptor {
        id: "bzip2-size",
        backend: "bzip2",
        profile: "size",
        config: CandidateConfig::Canonical,
    },
    CandidateDescriptor {
        id: "xz-default-6",
        backend: "xz",
        profile: "default",
        config: CandidateConfig::Canonical,
    },
    CandidateDescriptor {
        id: "xz-size-9e",
        backend: "xz",
        profile: "size",
        config: CandidateConfig::Canonical,
    },
    CandidateDescriptor {
        id: "zstd-fast",
        backend: "zstd",
        profile: "fast",
        config: CandidateConfig::Canonical,
    },
    CandidateDescriptor {
        id: "zstd-default-3",
        backend: "zstd",
        profile: "default",
        config: CandidateConfig::Canonical,
    },
    CandidateDescriptor {
        id: "zstd-size-22",
        backend: "zstd",
        profile: "size",
        config: CandidateConfig::Canonical,
    },
    CandidateDescriptor {
        id: "brotli-fast-0",
        backend: "brotli",
        profile: "fast",
        config: CandidateConfig::Canonical,
    },
    // The previous registry incorrectly treated its historical fast envelope
    // as Brotli coverage.  Quality 11 is a legal generic, self-describing
    // Brotli payload inside CIXB1's existing `brotli/size` envelope.  Its
    // configuration is explicit in this typed descriptor and explain output;
    // the decoder needs neither the quality nor a dictionary to restore it.
    CandidateDescriptor {
        id: "brotli-size-q11-generic-w22",
        backend: "brotli",
        profile: "size",
        config: CandidateConfig::BrotliQuality {
            quality: 11,
            lgwin: 22,
            mode: BrotliMode::Generic,
        },
    },
    CandidateDescriptor {
        id: "xz-dict128-size-9e",
        backend: "xz",
        profile: "size",
        config: CandidateConfig::XzDictionary {
            dictionary_bytes: 128 * 1024 * 1024,
            preset: (1 << 31) | 9,
        },
    },
    CandidateDescriptor {
        id: "xz-dict128-preset6",
        backend: "xz",
        profile: "size",
        config: CandidateConfig::XzDictionary {
            dictionary_bytes: 128 * 1024 * 1024,
            preset: 6,
        },
    },
];

/// Every direct backend configuration automatically eligible to BEST.
///
/// `gzip-default` is intentionally omitted: it uses the same deflate level
/// as `gzip-size`, while the latter is the historical size-profile envelope.
pub fn best_candidates() -> &'static [CandidateDescriptor] {
    // Existing canonical CIXB1 paths have frozen full-archive restoration
    // evidence. New configurations stay experimental until matched complete
    // cost and resource qualification; correctness tests alone do not promote.
    &CIXB1_BEST_CANDIDATES[..9]
}

pub fn experimental_candidates() -> &'static [CandidateDescriptor] {
    &CIXB1_BEST_CANDIDATES[9..]
}

/// Runtime version of the native backend selected by a descriptor. Evidence
/// recorders can use this without guessing package-manager versions.
pub fn backend_version(backend: &str) -> Result<String, String> {
    unsafe {
        let version = match backend {
            "gzip" => CStr::from_ptr(zlibVersion()).to_string_lossy().into_owned(),
            "bzip2" => CStr::from_ptr(BZ2_bzlibVersion())
                .to_string_lossy()
                .into_owned(),
            "xz" => CStr::from_ptr(lzma_version_string())
                .to_string_lossy()
                .into_owned(),
            "zstd" => CStr::from_ptr(ZSTD_versionString())
                .to_string_lossy()
                .into_owned(),
            "brotli" => {
                let version = BrotliEncoderVersion();
                format!(
                    "{}.{}.{}",
                    version >> 24,
                    (version >> 12) & 0x0fff,
                    version & 0x0fff
                )
            }
            _ => return Err(format!("unsupported CIXB1 backend: {backend}")),
        };
        if version.is_empty() {
            Err(format!("native backend {backend} did not report a version"))
        } else {
            Ok(version)
        }
    }
}

impl CandidateDescriptor {
    /// Materialise the complete CIXB1 archive, including its header, length
    /// fields and checksum.  Callers must compare this result directly.
    pub fn full_archive_encode(&self, input: &[u8]) -> Result<Vec<u8>, String> {
        match self.config {
            CandidateConfig::Canonical => encode(self.backend, self.profile, input),
            CandidateConfig::XzDictionary {
                dictionary_bytes,
                preset,
            } => encode_xz_dictionary_preset(self.profile, input, dictionary_bytes, preset),
            CandidateConfig::BrotliQuality {
                quality,
                lgwin,
                mode,
            } => {
                if self.backend != "brotli" {
                    return Err(format!(
                        "Brotli configuration used by non-Brotli candidate {}",
                        self.id
                    ));
                }
                encode_brotli_quality(self.profile, input, quality, lgwin, mode)
            }
        }
    }

    /// Conservative additional encoder memory required after the caller has
    /// retained the source input and any incumbent archive.  This includes
    /// native codec state, payload storage and the separately allocated CIXB1
    /// wrapper.  It is intentionally an admission estimate, not an RSS claim.
    pub fn encoder_peak_bytes(&self, input_len: usize) -> Result<usize, String> {
        if input_len > MAX_INPUT {
            return Err("CIXB1 input exceeds 64 MiB limit".into());
        }
        let payload = input_len
            .checked_add(1024 * 1024)
            .ok_or_else(|| "CIXB1 payload estimate overflow".to_string())?;
        // All ordinary backends hold a payload vector and then construct a
        // complete wrapper vector.  The dictionary XZ encoder grows its
        // payload dynamically, so reserve one further payload bound for a
        // potential capacity growth before it becomes the wrapper.
        let copies = match self.config {
            CandidateConfig::Canonical => 2usize,
            CandidateConfig::XzDictionary { .. } | CandidateConfig::BrotliQuality { .. } => 3usize,
        };
        let storage = payload
            .checked_mul(copies)
            .and_then(|v| v.checked_add(HEADER))
            .ok_or_else(|| "CIXB1 output estimate overflow".to_string())?;
        let native = self.native_encoder_bytes()?;
        storage
            .checked_add(native)
            .and_then(|v| v.checked_add(128 * 1024)) // stream chunks and ABI bookkeeping
            .ok_or_else(|| "CIXB1 encoder estimate overflow".to_string())
    }

    /// Admit this candidate against the budget remaining after source and
    /// incumbent ownership have been charged by the automatic selector.
    pub fn admit(
        &self,
        input_len: usize,
        available_bytes: usize,
    ) -> Result<usize, CandidateOmission> {
        let needed_bytes = match self.encoder_peak_bytes(input_len) {
            Ok(needed) => needed,
            Err(reason) => {
                return Err(CandidateOmission {
                    needed_bytes: usize::MAX,
                    available_bytes,
                    reason,
                });
            }
        };
        if needed_bytes > available_bytes {
            return Err(CandidateOmission {
                needed_bytes,
                available_bytes,
                reason: format!(
                    "need {needed_bytes} bytes for CIXB1 {} ({}), available {available_bytes}",
                    self.id, self.backend
                ),
            });
        }
        Ok(needed_bytes)
    }

    fn native_encoder_bytes(&self) -> Result<usize, String> {
        let bytes = match self.config {
            CandidateConfig::XzDictionary {
                dictionary_bytes,
                preset,
            } => xz_dictionary_memory_usage(dictionary_bytes, preset)?,
            CandidateConfig::Canonical if self.backend == "xz" => {
                let preset = match self.profile {
                    "fast" => 0,
                    "default" | "current" => 6,
                    "size" => (1 << 31) | 9,
                    _ => return Err(format!("unsupported xz profile {}", self.profile)),
                };
                xz_easy_memory_usage(preset)
            }
            CandidateConfig::Canonical if self.backend == "zstd" => {
                let level = match self.profile {
                    "fast" => -131072,
                    "default" | "current" => 3,
                    "size" => 22,
                    _ => return Err(format!("unsupported zstd profile {}", self.profile)),
                };
                zstd_memory_usage(level)
            }
            CandidateConfig::Canonical if self.backend == "gzip" => 16 * 1024 * 1024,
            CandidateConfig::Canonical if self.backend == "bzip2" => 24 * 1024 * 1024,
            CandidateConfig::Canonical if self.backend == "brotli" => 16 * 1024 * 1024,
            // Brotli's documented maximum quality makes substantially larger
            // encoder tables than quality 0.  Keep an intentionally
            // conservative admission bound; this is not an RSS assertion.
            CandidateConfig::BrotliQuality {
                quality,
                lgwin,
                mode: BrotliMode::Generic,
            } if self.backend == "brotli" && quality <= 11 && (10..=24).contains(&lgwin) => {
                256 * 1024 * 1024
            }
            _ => return Err(format!("unsupported CIXB1 candidate {}", self.id)),
        };
        Ok(bytes)
    }

    /// Conservative decoder admission for a complete CIXB1 candidate whose
    /// uncompressed length is known from its wrapper.  It counts a bounded
    /// maximum payload, reconstructed output and native decoder state.  The
    /// caller still passes the actual archive length to `decode`, which
    /// performs exact header and output limits before invoking native code.
    pub fn decoder_peak_bytes(&self, input_len: usize) -> Result<usize, String> {
        if input_len > MAX_INPUT {
            return Err("CIXB1 input exceeds 64 MiB limit".into());
        }
        let native = match self.config {
            CandidateConfig::XzDictionary {
                dictionary_bytes, ..
            } => dictionary_bytes as usize + 32 * 1024 * 1024,
            CandidateConfig::Canonical if self.backend == "xz" => 128 * 1024 * 1024,
            CandidateConfig::BrotliQuality { lgwin, .. } if self.backend == "brotli" => {
                // lgwin is payload-described to the decoder.  Account above
                // its declared window for decoder tables and allocator slack.
                (1usize << lgwin).saturating_add(32 * 1024 * 1024)
            }
            CandidateConfig::Canonical if self.backend == "brotli" => 48 * 1024 * 1024,
            CandidateConfig::Canonical if self.backend == "bzip2" => 32 * 1024 * 1024,
            CandidateConfig::Canonical if self.backend == "zstd" => 64 * 1024 * 1024,
            CandidateConfig::Canonical if self.backend == "gzip" => 8 * 1024 * 1024,
            _ => return Err(format!("unsupported CIXB1 candidate {}", self.id)),
        };
        MAX_PAYLOAD
            .checked_add(input_len)
            .and_then(|v| v.checked_add(HEADER))
            .and_then(|v| v.checked_add(native))
            .ok_or_else(|| "CIXB1 decoder estimate overflow".into())
    }
}

fn xz_easy_memory_usage(preset: u32) -> usize {
    let reported = unsafe { lzma_easy_encoder_memusage(preset) };
    // LZMA_UINT64_MAX signals unsupported options.  The configured presets
    // are known legal; use a deliberately large fallback instead of admitting
    // an unknown native allocation on a small estimate.
    if reported == u64::MAX || reported > usize::MAX as u64 {
        2 * 1024 * 1024 * 1024usize
    } else {
        reported as usize
    }
}

fn xz_dictionary_memory_usage(dictionary_bytes: u32, preset: u32) -> Result<usize, String> {
    let mut options: LzmaOptionsLzma = unsafe { std::mem::zeroed() };
    if unsafe { lzma_lzma_preset(&mut options, preset) } != 0 {
        return Err("liblzma rejected the requested preset".into());
    }
    options.dict_size = dictionary_bytes;
    let filters = [
        LzmaFilter {
            id: 0x21,
            options: (&mut options as *mut LzmaOptionsLzma).cast(),
        },
        LzmaFilter {
            id: u64::MAX,
            options: std::ptr::null_mut(),
        },
    ];
    let reported = unsafe { lzma_raw_encoder_memusage(filters.as_ptr()) };
    if reported == u64::MAX || reported > usize::MAX as u64 {
        Ok(2 * 1024 * 1024 * 1024usize)
    } else {
        Ok(reported as usize)
    }
}

fn zstd_memory_usage(level: c_int) -> usize {
    let reported = unsafe { ZSTD_estimateCCtxSize(level) };
    // ZSTD_isError accepts a size_t result.  The static fallback deliberately
    // exceeds a level-22 window/table budget, avoiding a false small
    // admission if an old library rejects the estimator query.
    if unsafe { ZSTD_isError(reported) } != 0 || reported == 0 {
        2 * 1024 * 1024 * 1024usize
    } else {
        reported
    }
}

#[link(name = "brotlienc")]
unsafe extern "C" {
    fn BrotliEncoderMaxCompressedSize(input_size: usize) -> usize;
    fn BrotliEncoderCompress(
        quality: c_int,
        lgwin: c_int,
        mode: c_int,
        input_size: usize,
        input: *const u8,
        encoded_size: *mut usize,
        encoded: *mut u8,
    ) -> c_int;
    fn BrotliEncoderVersion() -> u32;
}
#[link(name = "brotlidec")]
unsafe extern "C" {
    fn BrotliDecoderDecompress(
        encoded_size: usize,
        encoded: *const u8,
        decoded_size: *mut usize,
        decoded: *mut u8,
    ) -> c_int;
}

fn backend_id(name: &str) -> Result<u8, String> {
    match name {
        "gzip" => Ok(1),
        "bzip2" => Ok(2),
        "xz" => Ok(3),
        "zstd" => Ok(4),
        "brotli" => Ok(5),
        _ => Err(format!("unsupported CIXB1 backend: {name}")),
    }
}
fn profile_id(name: &str) -> Result<u8, String> {
    match name {
        "fast" => Ok(1),
        "default" | "current" => Ok(2),
        "size" => Ok(3),
        _ => Err(format!("unsupported CIXB1 profile: {name}")),
    }
}
fn check_eligible(backend: &str, profile: &str) -> Result<(), String> {
    let valid = match profile {
        "fast" => matches!(backend, "gzip" | "zstd" | "brotli"),
        "default" | "current" | "size" => matches!(backend, "gzip" | "bzip2" | "xz" | "zstd"),
        _ => false,
    };
    if valid {
        Ok(())
    } else {
        Err(format!(
            "CIXB1 backend {backend} is not eligible for profile {profile}"
        ))
    }
}
fn zstd_error(code: usize) -> String {
    unsafe {
        CStr::from_ptr(ZSTD_getErrorName(code))
            .to_string_lossy()
            .into_owned()
    }
}

pub fn encode(backend: &str, profile: &str, input: &[u8]) -> Result<Vec<u8>, String> {
    check_eligible(backend, profile)?;
    check_cancel()?;
    if input.len() > MAX_INPUT {
        return Err("CIXB1 input exceeds 64 MiB limit".into());
    }
    let payload = match backend {
        "gzip" => {
            let level = if profile == "fast" { 1 } else { 9 };
            let mut encoder = GzBuilder::new().mtime(0).write(
                Vec::with_capacity(input.len() + 1024 * 1024),
                Compression::new(level),
            );
            encoder.write_all(input).map_err(|e| e.to_string())?;
            let payload = encoder.finish().map_err(|e| e.to_string())?;
            check_cancel()?;
            payload
        }
        "bzip2" => {
            let level = if profile == "fast" { 1 } else { 9 };
            let cap = input
                .len()
                .saturating_add(input.len() / 100)
                .saturating_add(601)
                .max(601);
            let mut out = vec![0u8; cap];
            let mut n = u32::try_from(cap).map_err(|_| "bzip2 output bound overflow")?;
            let srcn = u32::try_from(input.len()).map_err(|_| "bzip2 source too large")?;
            let rc = unsafe {
                BZ2_bzBuffToBuffCompress(
                    out.as_mut_ptr().cast(),
                    &mut n,
                    input.as_ptr().cast_mut().cast(),
                    srcn,
                    level,
                    0,
                    30,
                )
            };
            if rc != 0 {
                return Err(format!("bzip2 compressor returned {rc}"));
            }
            check_cancel()?;
            out.truncate(n as usize);
            out
        }
        "xz" => {
            let base = match profile {
                "fast" => 0,
                "default" | "current" => 6,
                _ => 9,
            };
            let preset = base | if profile == "size" { 1u32 << 31 } else { 0 };
            let cap = unsafe { lzma_stream_buffer_bound(input.len()) };
            let mut stream: LzmaStream = unsafe { std::mem::zeroed() };
            stream.next_in = input.as_ptr();
            stream.avail_in = input.len();
            let init = unsafe { lzma_easy_encoder(&mut stream, preset, 4) };
            if init != 0 {
                return Err(format!("xz encoder initialization returned {init}"));
            }
            let mut out = Vec::with_capacity(cap);
            let mut chunk = [0u8; 65536];
            loop {
                check_cancel()?;
                stream.next_out = chunk.as_mut_ptr();
                stream.avail_out = chunk.len();
                let before_in = stream.avail_in;
                let rc = unsafe { lzma_code(&mut stream, 3) }; // LZMA_FINISH
                let written = chunk.len() - stream.avail_out;
                out.extend_from_slice(&chunk[..written]);
                if rc != 0 {
                    if rc != 1 {
                        return Err(format!("xz encoder returned {rc}"));
                    }
                }
                check_cancel()?;
                if rc == 1 {
                    break;
                } // LZMA_STREAM_END
                if written == 0 && stream.avail_in == before_in {
                    return Err("xz encoder made no progress".into());
                }
            }
            out
        }
        "zstd" => {
            let level = match profile {
                "fast" => -131072,
                "default" | "current" => 3,
                _ => 22,
            };
            let cap = unsafe { ZSTD_compressBound(input.len()) };
            let mut out = vec![0u8; cap];
            let n = unsafe {
                ZSTD_compress(
                    out.as_mut_ptr().cast(),
                    out.len(),
                    input.as_ptr().cast(),
                    input.len(),
                    level,
                )
            };
            if unsafe { ZSTD_isError(n) } != 0 {
                return Err(format!("zstd encode: {}", zstd_error(n)));
            }
            check_cancel()?;
            out.truncate(n);
            out
        }
        "brotli" => brotli_payload(input, 0, 22, BrotliMode::Generic)?,
        _ => return Err(format!("unsupported CIXB1 backend: {backend}")),
    };
    if payload.len() > MAX_PAYLOAD {
        return Err("CIXB1 payload exceeds bounded limit".into());
    }
    let mut out = Vec::with_capacity(HEADER + payload.len());
    out.extend_from_slice(b"CIXB1");
    out.push(backend_id(backend)?);
    out.push(profile_id(profile)?);
    out.extend_from_slice(&(input.len() as u32).to_le_bytes());
    out.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    out.extend_from_slice(&Sha256::digest(input));
    out.extend_from_slice(&payload);
    Ok(out)
}

fn brotli_payload(
    input: &[u8],
    quality: u8,
    lgwin: u8,
    mode: BrotliMode,
) -> Result<Vec<u8>, String> {
    if quality > 11 || !(10..=24).contains(&lgwin) {
        return Err("unsupported Brotli quality/window configuration".into());
    }
    let mode = match mode {
        BrotliMode::Generic => 0,
    };
    check_cancel()?;
    let cap = unsafe { BrotliEncoderMaxCompressedSize(input.len()) };
    let mut out = vec![0u8; cap];
    let mut n = cap;
    let ok = unsafe {
        BrotliEncoderCompress(
            quality as c_int,
            lgwin as c_int,
            mode,
            input.len(),
            input.as_ptr(),
            &mut n,
            out.as_mut_ptr(),
        )
    };
    // Native failure takes precedence over a concurrently noticed interrupt.
    if ok == 0 {
        return Err("brotli encoder failed".into());
    }
    check_cancel()?;
    out.truncate(n);
    Ok(out)
}

/// Encode a generic Brotli payload at an explicit quality/window.  The CIXB1
/// `brotli/size` profile identifies the size-search envelope; Brotli itself
/// serializes the decoder-relevant window in its payload.  Quality is an
/// encoder effort setting and is retained in the candidate descriptor/evidence
/// rather than requiring a decoder-side source dictionary.
pub fn encode_brotli_quality(
    profile: &str,
    input: &[u8],
    quality: u8,
    lgwin: u8,
    mode: BrotliMode,
) -> Result<Vec<u8>, String> {
    if !matches!(profile, "fast" | "default" | "current" | "size") {
        return Err(format!("unsupported CIXB1 profile: {profile}"));
    }
    if input.len() > MAX_INPUT {
        return Err("CIXB1 input exceeds 64 MiB limit".into());
    }
    let payload = brotli_payload(input, quality, lgwin, mode)?;
    if payload.len() > MAX_PAYLOAD {
        return Err("CIXB1 payload exceeds bounded limit".into());
    }
    let mut out = Vec::with_capacity(HEADER + payload.len());
    out.extend_from_slice(b"CIXB1");
    out.push(backend_id("brotli")?);
    out.push(profile_id(profile)?);
    out.extend_from_slice(&(input.len() as u32).to_le_bytes());
    out.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    out.extend_from_slice(&Sha256::digest(input));
    out.extend_from_slice(&payload);
    Ok(out)
}

/// Encode an xz preset with a larger self-describing dictionary. The Python
/// preset remains available through `encode`; this is an additional measured
/// size candidate whose settings are carried inside the XZ stream itself.
pub fn encode_xz_dictionary(
    profile: &str,
    input: &[u8],
    dictionary_bytes: u32,
) -> Result<Vec<u8>, String> {
    check_eligible("xz", profile)?;
    if input.len() > MAX_INPUT {
        return Err("CIXB1 input exceeds 64 MiB limit".into());
    }
    let base = match profile {
        "fast" => 0,
        "default" | "current" => 6,
        _ => 9,
    };
    let preset = base | if profile == "size" { 1u32 << 31 } else { 0 };
    encode_xz_dictionary_preset(profile, input, dictionary_bytes, preset)
}

pub fn encode_xz_dictionary_preset(
    profile: &str,
    input: &[u8],
    dictionary_bytes: u32,
    preset: u32,
) -> Result<Vec<u8>, String> {
    check_eligible("xz", profile)?;
    check_cancel()?;
    if input.len() > MAX_INPUT {
        return Err("CIXB1 input exceeds 64 MiB limit".into());
    }
    let mut options: LzmaOptionsLzma = unsafe { std::mem::zeroed() };
    if unsafe { lzma_lzma_preset(&mut options, preset) } != 0 {
        return Err("liblzma rejected the requested preset".into());
    }
    options.dict_size = dictionary_bytes;
    let mut filters = [
        LzmaFilter {
            id: 0x21,
            options: (&mut options as *mut LzmaOptionsLzma).cast(),
        },
        LzmaFilter {
            id: u64::MAX,
            options: std::ptr::null_mut(),
        },
    ];
    let mut stream: LzmaStream = unsafe { std::mem::zeroed() };
    stream.next_in = input.as_ptr();
    stream.avail_in = input.len();
    let init = unsafe { lzma_stream_encoder(&mut stream, filters.as_mut_ptr(), 4) };
    if init != 0 {
        return Err(format!("xz encoder initialization returned {init}"));
    }
    let mut payload = Vec::with_capacity(input.len() + 1024 * 1024);
    let mut chunk = [0u8; 65536];
    loop {
        check_cancel()?;
        stream.next_out = chunk.as_mut_ptr();
        stream.avail_out = chunk.len();
        let before_in = stream.avail_in;
        let rc = unsafe { lzma_code(&mut stream, 3) };
        let written = chunk.len() - stream.avail_out;
        payload.extend_from_slice(&chunk[..written]);
        if rc == 1 {
            break;
        }
        if rc != 0 {
            return Err(format!("xz encoder returned {rc}"));
        }
        check_cancel()?;
        if written == 0 && stream.avail_in == before_in {
            return Err("xz encoder made no progress".into());
        }
    }
    if payload.len() > MAX_PAYLOAD {
        return Err("CIXB1 payload exceeds bounded limit".into());
    }
    let mut archive = Vec::with_capacity(HEADER + payload.len());
    archive.extend_from_slice(b"CIXB1");
    archive.push(backend_id("xz")?);
    archive.push(profile_id(profile)?);
    archive.extend_from_slice(&(input.len() as u32).to_le_bytes());
    archive.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    archive.extend_from_slice(&Sha256::digest(input));
    archive.extend_from_slice(&payload);
    Ok(archive)
}

pub fn decode(archive: &[u8], memory_limit: usize) -> Result<Vec<u8>, String> {
    check_cancel()?;
    if archive.len() < HEADER || &archive[..5] != b"CIXB1" {
        return Err("truncated or invalid CIXB1 header".into());
    }
    let bid = archive[5];
    let profile = archive[6];
    if !(1..=5).contains(&bid) || !(1..=3).contains(&profile) {
        return Err("unsupported CIXB1 backend or profile ID".into());
    }
    let expected = u32::from_le_bytes(archive[7..11].try_into().unwrap()) as usize;
    let size = u32::from_le_bytes(archive[11..15].try_into().unwrap()) as usize;
    if expected > MAX_INPUT
        || size > MAX_PAYLOAD
        || expected.saturating_add(size).saturating_add(HEADER) > memory_limit
    {
        return Err("CIXB1 memory/resource limit exceeded".into());
    }
    if archive.len() != HEADER + size {
        return Err("CIXB1 payload length mismatch".into());
    }
    let payload = &archive[HEADER..];
    let fixed = archive
        .len()
        .checked_add(expected + 1)
        .ok_or("CIXB1 memory/resource limit exceeded")?;
    let native_memory = memory_limit
        .checked_sub(fixed)
        .ok_or("CIXB1 memory/resource limit exceeded")?;
    let native_reserve = match bid {
        1 => 8 * 1024 * 1024,
        2 => 32 * 1024 * 1024,
        3 => 0, // liblzma enforces the exact remainder below.
        4 => 64 * 1024 * 1024,
        5 => 48 * 1024 * 1024,
        _ => unreachable!(),
    };
    if native_memory < native_reserve {
        return Err("CIXB1 decoder memory/resource limit exceeded".into());
    }
    let mut output = vec![0u8; expected.saturating_add(1)];
    let written = match bid {
        1 => {
            output.clear();
            let mut decoder = GzDecoder::new(Cursor::new(payload));
            std::io::Read::by_ref(&mut decoder)
                .take((expected + 1) as u64)
                .read_to_end(&mut output)
                .map_err(|e| format!("gzip decode: {e}"))?;
            check_cancel()?;
            let pos = decoder.get_ref().position() as usize;
            if pos != payload.len() {
                return Err("gzip trailing or concatenated data".into());
            }
            output.len()
        }
        2 => {
            let mut stream = BzStream {
                next_in: payload.as_ptr().cast_mut().cast(),
                avail_in: u32::try_from(payload.len()).map_err(|_| "bzip2 input too large")?,
                total_in_lo32: 0,
                total_in_hi32: 0,
                next_out: output.as_mut_ptr().cast(),
                avail_out: u32::try_from(output.len()).map_err(|_| "bzip2 output too large")?,
                total_out_lo32: 0,
                total_out_hi32: 0,
                state: std::ptr::null_mut(),
                bzalloc: None,
                bzfree: None,
                opaque: std::ptr::null_mut(),
            };
            let init = unsafe { BZ2_bzDecompressInit(&mut stream, 0, 0) };
            if init != 0 {
                return Err(format!("bzip2 init returned {init}"));
            }
            let mut rc;
            loop {
                rc = unsafe { BZ2_bzDecompress(&mut stream) };
                if rc == 4 || rc < 0 || rc == 0 && stream.avail_in == 0 || stream.avail_out == 0 {
                    break;
                }
                if let Err(error) = check_cancel() {
                    unsafe { BZ2_bzDecompressEnd(&mut stream) };
                    return Err(error);
                }
            }
            let _ = unsafe { BZ2_bzDecompressEnd(&mut stream) };
            if rc != 4 || stream.avail_in != 0 {
                return Err("bzip2 truncated, trailing or invalid data".into());
            }
            check_cancel()?;
            stream.total_out_lo32 as usize | ((stream.total_out_hi32 as usize) << 32)
        }
        3 => {
            let mut inpos = 0usize;
            let mut outpos = 0usize;
            let mut memlimit = native_memory as u64;
            let rc = unsafe {
                lzma_stream_buffer_decode(
                    &mut memlimit,
                    0,
                    std::ptr::null(),
                    payload.as_ptr(),
                    &mut inpos,
                    payload.len(),
                    output.as_mut_ptr(),
                    &mut outpos,
                    output.len(),
                )
            };
            if rc != 0 || inpos != payload.len() {
                return Err(format!("xz invalid/trailing data (status {rc})"));
            }
            check_cancel()?;
            outpos
        }
        4 => {
            let frame =
                unsafe { ZSTD_findFrameCompressedSize(payload.as_ptr().cast(), payload.len()) };
            if unsafe { ZSTD_isError(frame) } != 0 || frame != payload.len() {
                return Err("zstd invalid or trailing data".into());
            }
            let n = unsafe {
                ZSTD_decompress(
                    output.as_mut_ptr().cast(),
                    output.len(),
                    payload.as_ptr().cast(),
                    payload.len(),
                )
            };
            if unsafe { ZSTD_isError(n) } != 0 {
                return Err(format!("zstd decode: {}", zstd_error(n)));
            }
            check_cancel()?;
            n
        }
        5 => {
            let mut n = output.len();
            let rc = unsafe {
                BrotliDecoderDecompress(
                    payload.len(),
                    payload.as_ptr(),
                    &mut n,
                    output.as_mut_ptr(),
                )
            };
            if rc != 1 {
                return Err("brotli decode failed".into());
            }
            check_cancel()?;
            n
        }
        _ => return Err("unknown CIXB1 backend".into()),
    };
    if written != expected {
        return Err(format!(
            "CIXB1 decoded length mismatch: expected {expected}, got {written}"
        ));
    }
    output.truncate(written);
    if Sha256::digest(&output).as_slice() != &archive[15..47] {
        return Err("CIXB1 SHA-256 checksum mismatch".into());
    }
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::{decode, encode_xz_dictionary};

    #[test]
    fn xz_larger_dictionary_archive_round_trips() {
        let input = b"CIX xz dictionary fixture: abcdef0123456789 ".repeat(8192);
        let archive = encode_xz_dictionary("size", &input, 128 * 1024 * 1024).unwrap();
        assert_eq!(decode(&archive, 1024 * 1024 * 1024).unwrap(), input);
    }
}
