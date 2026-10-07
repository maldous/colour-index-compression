//! Research adapter for actual provider bytes; not the integrated product CLI.
use crate::full_engine::{address_relations as address, dynamic_library::DynamicLibrary};
use crate::paq_bridge::{PaqBridge, PaqExecutionScope, PaqInvocation, PaqVariant, PaqWorkerEnvironment};
use std::{ffi::{c_int, c_void, CStr, OsString}, fs, path::Path};

// These declarations, RAII decoder and exact stream-consumption function are
// a byte-identical excerpt of the pinned production external.rs, not a mock.
include!("brotli_exact.inc");

const CAP: usize = 1_048_576;
const PAQ_LIBRARY: &str = "/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/paq-cix-worker-v2-output/lib/libcix_paq_v215_bridge.so";

fn brotli(input: &[u8], encode: bool, limit: usize) -> Result<Vec<u8>, String> {
    if unsafe { BrotliEncoderVersion() } != 0x01002000 {
        return Err("unexpected Brotli version".into());
    }
    let mut output = vec![0; limit.min(CAP)];
    let used = if encode {
        let mut size = output.len().min(unsafe { BrotliEncoderMaxCompressedSize(input.len()) });
        let status = unsafe { BrotliEncoderCompress(11, 24, 0, input.len(), input.as_ptr(), &mut size, output.as_mut_ptr()) };
        if status != 1 || size > output.len() { return Err("Brotli encode failed or exceeded bound".into()); }
        size
    } else {
        brotli_decode_exact(input, &mut output)?
    };
    output.truncate(used);
    Ok(output)
}

fn paq(input: &[u8], encode: bool, limit: usize, work: &Path) -> Result<Vec<u8>, String> {
    if !std::is_x86_feature_detected!("avx2") { return Err("AVX2 unavailable".into()); }
    for (kind, requested) in [(libc::RLIMIT_AS, 6_000_000_000u64), (libc::RLIMIT_FSIZE, CAP as u64)] {
        let mut old: libc::rlimit = unsafe { std::mem::zeroed() };
        if unsafe { libc::getrlimit(kind, &mut old) } != 0 { return Err("getrlimit failed".into()); }
        let hard = old.rlim_max.min(requested as libc::rlim_t);
        let bound = libc::rlimit { rlim_cur: old.rlim_cur.min(hard), rlim_max: hard };
        if unsafe { libc::setrlimit(kind, &bound) } != 0 { return Err("setrlimit failed".into()); }
    }
    let source = work.join("provider-input");
    let destination = work.join("provider-output");
    if source.exists() || destination.exists() { return Err("provider paths already used".into()); }
    fs::write(&source, input).map_err(|e| e.to_string())?;
    let library = DynamicLibrary::open(Path::new(PAQ_LIBRARY)).map_err(|e| format!("{e:?}"))?;
    let version: unsafe extern "C" fn() -> *const libc::c_char = unsafe { library.symbol("cix_paq_v215_bridge_version") }.map_err(|e| format!("{e:?}"))?;
    let identity = unsafe { version() };
    if identity.is_null() || unsafe { CStr::from_ptr(identity) }.to_bytes() != b"cix-paq-v215-bridge/1" { return Err("PAQ ABI mismatch".into()); }
    let process = unsafe { library.symbol("cix_paq_v215_process") }.map_err(|e| format!("{e:?}"))?;
    let args: Vec<OsString> = vec!["cix-physical-qualification".into(), if encode { "-8" } else { "-d" }.into(), "-simd".into(), "AVX2".into(), source.clone().into(), destination.clone().into()];
    let request = PaqInvocation { scope: PaqExecutionScope::IsolatedWorker, variant: PaqVariant::V215,
        argv: args, input: source, output: destination.clone(), worker_environment: PaqWorkerEnvironment { entries: Vec::new() }, memory_limit_bytes: 6_000_000_000 };
    unsafe { PaqBridge::from_symbol(PaqVariant::V215, process) }.invoke(&request).map_err(|e| e.to_string())?;
    if fs::metadata(&destination).map_err(|e| e.to_string())?.len() > limit.min(CAP) as u64 { return Err("PAQ output bound exceeded".into()); }
    fs::read(destination).map_err(|e| e.to_string())
}

fn payload(variant: address::BackendVariant, input: &[u8], encode: bool, limit: usize, work: &Path) -> Result<Vec<u8>, String> {
    match variant {
        address::BackendVariant::Brotli => brotli(input, encode, limit),
        address::BackendVariant::PaqV215 => paq(input, encode, limit, work),
        _ => Err("unqualified provider requested".into()),
    }
}

pub fn execute(operation: &str, backend: &str, input: &Path, output: &Path, work: &Path) -> Result<(), String> {
    if !input.is_absolute() || !output.is_absolute() || !work.is_absolute() || output.exists() { return Err("invalid driver paths".into()); }
    if fs::metadata(input).map_err(|e| e.to_string())?.len() > CAP as u64 { return Err("input exceeds fixture cap".into()); }
    let source = fs::read(input).map_err(|e| e.to_string())?;
    let variant = match backend { "brotli" => address::BackendVariant::Brotli, "paq" => address::BackendVariant::PaqV215, _ => return Err("unknown provider".into()) };
    let result = match operation {
        "encode-payload" => payload(variant, &source, true, CAP, work),
        "decode-payload" => payload(variant, &source, false, CAP, work),
        "encode-frame" => address::encode_transformed_frame(address::HistoricalFrame::Relocated,
            address::Transform::RelocatedPointers { mode: 5, shared: true }, &source,
            address::BackendRequest { variant, options: "-8".into(), stream: 0 },
            &mut |request, raw| {
                if request.variant != variant { return Err("provider mismatch".into()); }
                payload(request.variant, raw, true, CAP, work)
            }),
        "decode-frame" => address::decode_transformed_frame(address::HistoricalFrame::Relocated, &source, CAP, 16 * CAP,
            &mut |request, raw, limit| {
                if request.variant != variant { return Err("provider mismatch".into()); }
                payload(request.variant, raw, false, limit.min(CAP), work)
            }),
        _ => Err("unknown physical operation".into()),
    }?;
    fs::write(output, result).map_err(|e| e.to_string())
}
