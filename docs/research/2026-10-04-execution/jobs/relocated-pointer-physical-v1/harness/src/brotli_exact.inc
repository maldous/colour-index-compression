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
    fn BrotliDecoderCreateInstance(
        alloc_func: *const c_void,
        free_func: *const c_void,
        opaque: *mut c_void,
    ) -> *mut BrotliDecoderState;
    fn BrotliDecoderDestroyInstance(state: *mut BrotliDecoderState);
    fn BrotliDecoderDecompressStream(
        state: *mut BrotliDecoderState,
        available_in: *mut usize,
        next_in: *mut *const u8,
        available_out: *mut usize,
        next_out: *mut *mut u8,
        total_out: *mut usize,
    ) -> c_int;
}

#[repr(C)]
struct BrotliDecoderState {
    _opaque: [u8; 0],
}

struct BrotliDecoder(*mut BrotliDecoderState);

impl Drop for BrotliDecoder {
    fn drop(&mut self) {
        if !self.0.is_null() {
            unsafe { BrotliDecoderDestroyInstance(self.0) };
        }
    }
}

/// Decode exactly one Brotli stream. The one-shot Brotli API reports success
/// after a valid stream even when bytes remain in its input buffer. CIXB1
/// treats such bytes as a forged trailing payload, so use the streaming API
/// and require that the successful decode consumes every wrapper payload byte.
fn brotli_decode_exact(payload: &[u8], output: &mut [u8]) -> Result<usize, String> {
    let state = unsafe {
        BrotliDecoderCreateInstance(std::ptr::null(), std::ptr::null(), std::ptr::null_mut())
    };
    if state.is_null() {
        return Err("brotli decoder allocation failed".into());
    }
    let _state = BrotliDecoder(state);
    let mut available_in = payload.len();
    let mut next_in = payload.as_ptr();
    let mut available_out = output.len();
    let mut next_out = output.as_mut_ptr();
    let mut total_out = 0usize;
    let status = unsafe {
        BrotliDecoderDecompressStream(
            state,
            &mut available_in,
            &mut next_in,
            &mut available_out,
            &mut next_out,
            &mut total_out,
        )
    };
    // BROTLI_DECODER_RESULT_SUCCESS is 1. NEEDS_MORE_INPUT (2) means a
    // truncated payload; NEEDS_MORE_OUTPUT (3) exceeds the bounded output.
    if status != 1 {
        return Err("brotli truncated, invalid or oversized data".into());
    }
    if available_in != 0 {
        return Err("brotli trailing data".into());
    }
    if total_out > output.len() {
        return Err("brotli decoder returned invalid output length".into());
    }
    Ok(total_out)
}

