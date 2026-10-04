//! Typed binding for the CIX-owned libjxl grayscale bridge.
//!
//! The platform loader supplies symbols from the package's sibling
//! `cix_jxl_bridge` library. This module intentionally does not `dlopen`, set
//! environment variables, or select a host libjxl. Registration and package
//! loading remain the responsibility of the full engine.

use std::fmt;
use std::os::raw::c_int;

pub const LIBJXL_0_12_0_VERSION: u32 = 12_000;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u32)]
pub enum JxlSampleType {
    Uint8 = 1,
    Uint16 = 2,
}

impl JxlSampleType {
    pub fn bytes_per_sample(self) -> usize {
        match self {
            Self::Uint8 => 1,
            Self::Uint16 => 2,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(i32)]
pub enum JxlBridgeStatus {
    Ok = 0,
    InvalidArgument = 1,
    Unsupported = 2,
    OutputLimit = 3,
    EncodeFailure = 4,
    DecodeFailure = 5,
    AllocationFailure = 6,
    Exception = 7,
}

impl JxlBridgeStatus {
    fn from_raw(value: c_int) -> Option<Self> {
        match value {
            0 => Some(Self::Ok),
            1 => Some(Self::InvalidArgument),
            2 => Some(Self::Unsupported),
            3 => Some(Self::OutputLimit),
            4 => Some(Self::EncodeFailure),
            5 => Some(Self::DecodeFailure),
            6 => Some(Self::AllocationFailure),
            7 => Some(Self::Exception),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct JxlGrayGeometry {
    pub width: u32,
    pub height: u32,
    pub bits_per_sample: u32,
    pub sample_type: JxlSampleType,
}

impl JxlGrayGeometry {
    pub fn byte_len(self) -> Result<usize, JxlBridgeError> {
        if self.width == 0 || self.height == 0 || self.bits_per_sample == 0 {
            return Err(JxlBridgeError::InvalidImage(
                "zero image dimension or depth",
            ));
        }
        if self.bits_per_sample > 16
            || (self.sample_type == JxlSampleType::Uint8 && self.bits_per_sample > 8)
            || (self.sample_type == JxlSampleType::Uint16 && self.bits_per_sample <= 8)
        {
            return Err(JxlBridgeError::InvalidImage(
                "incompatible sample type and depth",
            ));
        }
        usize::try_from(self.width)
            .ok()
            .and_then(|width| {
                usize::try_from(self.height)
                    .ok()
                    .and_then(|height| width.checked_mul(height))
            })
            .and_then(|pixels| pixels.checked_mul(self.sample_type.bytes_per_sample()))
            .ok_or(JxlBridgeError::InvalidImage(
                "image byte count overflows usize",
            ))
    }
}

#[derive(Clone, Copy, Debug)]
pub struct JxlGrayImage<'a> {
    pub geometry: JxlGrayGeometry,
    pub effort: u32,
    pub bytes: &'a [u8],
}

impl<'a> JxlGrayImage<'a> {
    pub fn validate(self) -> Result<(), JxlBridgeError> {
        if !(1..=10).contains(&self.effort) {
            return Err(JxlBridgeError::InvalidImage("effort must be in 1..=10"));
        }
        if self.bytes.len() != self.geometry.byte_len()? {
            return Err(JxlBridgeError::InvalidImage(
                "pixel bytes do not match geometry",
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum JxlBridgeError {
    InvalidImage(&'static str),
    InvalidOutputBuffer,
    WrongLibraryVersion(u32),
    Status(Option<JxlBridgeStatus>),
}

impl fmt::Display for JxlBridgeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidImage(reason) => write!(formatter, "invalid JXL gray image: {reason}"),
            Self::InvalidOutputBuffer => write!(formatter, "JXL bridge returned an invalid buffer"),
            Self::WrongLibraryVersion(version) => write!(
                formatter,
                "CIX JXL bridge requires libjxl 0.12.0 (12000), loaded {version}"
            ),
            Self::Status(status) => write!(formatter, "CIX JXL bridge returned {status:?}"),
        }
    }
}

impl std::error::Error for JxlBridgeError {}

/// Raw ABI descriptor passed to `cix_jxl_encode_gray_2d`.
///
/// The full-engine loader needs this public type to resolve the C symbol with
/// its real signature. Safe callers use [`JxlGrayImage`] instead.
#[repr(C)]
pub struct JxlRawGrayImage {
    pixels: *const u8,
    pixels_size: usize,
    width: u32,
    height: u32,
    bits_per_sample: u32,
    sample_type: u32,
    effort: u32,
}

/// Raw ABI buffer returned by `cix_jxl_encode_gray_2d`.
///
/// It is released only through the matching `JxlFreeBufferFn` from the same
/// loaded bridge.
#[repr(C)]
pub struct JxlRawBuffer {
    data: *mut u8,
    size: usize,
}

/// Resolved `cix_jxl_encode_gray_2d` symbol type.
pub type JxlEncodeFn =
    unsafe extern "C" fn(*const JxlRawGrayImage, usize, *mut JxlRawBuffer) -> c_int;
/// Resolved `cix_jxl_decode_gray_2d` symbol type.
pub type JxlDecodeFn =
    unsafe extern "C" fn(*const u8, usize, u32, u32, u32, u32, *mut u8, usize) -> c_int;
/// Resolved `cix_jxl_free_buffer` symbol type.
pub type JxlFreeBufferFn = unsafe extern "C" fn(*mut JxlRawBuffer);
/// Resolved `cix_jxl_library_version` symbol type.
pub type JxlLibraryVersionFn = unsafe extern "C" fn() -> u32;

/// Functions resolved by the full engine from the CIX-packaged bridge.
#[derive(Clone, Copy)]
pub struct JxlBridge {
    encode: JxlEncodeFn,
    decode: JxlDecodeFn,
    free_buffer: JxlFreeBufferFn,
    library_version: JxlLibraryVersionFn,
}

impl JxlBridge {
    /// # Safety
    ///
    /// All supplied pointers must come from the matching CIX-owned
    /// `cix_jxl_bridge` build. The engine must not bind an arbitrary host DSO.
    pub const unsafe fn from_symbols(
        encode: JxlEncodeFn,
        decode: JxlDecodeFn,
        free_buffer: JxlFreeBufferFn,
        library_version: JxlLibraryVersionFn,
    ) -> Self {
        Self {
            encode,
            decode,
            free_buffer,
            library_version,
        }
    }

    pub fn verify_pinned_library(self) -> Result<(), JxlBridgeError> {
        let version = unsafe { (self.library_version)() };
        if version == LIBJXL_0_12_0_VERSION {
            Ok(())
        } else {
            Err(JxlBridgeError::WrongLibraryVersion(version))
        }
    }

    pub fn encode_gray_2d(
        self,
        image: JxlGrayImage<'_>,
        max_output_bytes: usize,
    ) -> Result<Vec<u8>, JxlBridgeError> {
        image.validate()?;
        if max_output_bytes == 0 {
            return Err(JxlBridgeError::InvalidOutputBuffer);
        }
        self.verify_pinned_library()?;
        let request = JxlRawGrayImage {
            pixels: image.bytes.as_ptr(),
            pixels_size: image.bytes.len(),
            width: image.geometry.width,
            height: image.geometry.height,
            bits_per_sample: image.geometry.bits_per_sample,
            sample_type: image.geometry.sample_type as u32,
            effort: image.effort,
        };
        let mut output = JxlRawBuffer {
            data: std::ptr::null_mut(),
            size: 0,
        };
        let status = unsafe { (self.encode)(&request, max_output_bytes, &mut output) };
        let parsed = JxlBridgeStatus::from_raw(status);
        if parsed != Some(JxlBridgeStatus::Ok) {
            if !output.data.is_null() {
                unsafe { (self.free_buffer)(&mut output) };
            }
            return Err(JxlBridgeError::Status(parsed));
        }
        if output.data.is_null()
            || output.size == 0
            || output.size > max_output_bytes
            || output.size > isize::MAX as usize
        {
            unsafe { (self.free_buffer)(&mut output) };
            return Err(JxlBridgeError::InvalidOutputBuffer);
        }
        let encoded = unsafe { std::slice::from_raw_parts(output.data, output.size).to_vec() };
        unsafe { (self.free_buffer)(&mut output) };
        Ok(encoded)
    }

    pub fn decode_gray_2d(
        self,
        input: &[u8],
        geometry: JxlGrayGeometry,
        output: &mut [u8],
    ) -> Result<(), JxlBridgeError> {
        let expected = geometry.byte_len()?;
        if input.is_empty() || output.len() != expected {
            return Err(JxlBridgeError::InvalidOutputBuffer);
        }
        self.verify_pinned_library()?;
        let status = unsafe {
            (self.decode)(
                input.as_ptr(),
                input.len(),
                geometry.width,
                geometry.height,
                geometry.bits_per_sample,
                geometry.sample_type as u32,
                output.as_mut_ptr(),
                output.len(),
            )
        };
        match JxlBridgeStatus::from_raw(status) {
            Some(JxlBridgeStatus::Ok) => Ok(()),
            other => Err(JxlBridgeError::Status(other)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Mutex;

    static TEST_LOCK: Mutex<()> = Mutex::new(());
    static ENCODE_CALLS: AtomicUsize = AtomicUsize::new(0);
    static DECODE_CALLS: AtomicUsize = AtomicUsize::new(0);
    static FREE_CALLS: AtomicUsize = AtomicUsize::new(0);

    unsafe extern "C" fn good_version() -> u32 {
        LIBJXL_0_12_0_VERSION
    }

    unsafe extern "C" fn wrong_version() -> u32 {
        LIBJXL_0_12_0_VERSION - 1
    }

    unsafe extern "C" fn mock_encode(
        image: *const JxlRawGrayImage,
        max_output_bytes: usize,
        output: *mut JxlRawBuffer,
    ) -> c_int {
        ENCODE_CALLS.fetch_add(1, Ordering::SeqCst);
        if image.is_null() || output.is_null() || max_output_bytes < 4 {
            return JxlBridgeStatus::InvalidArgument as c_int;
        }
        let encoded = Box::new([1_u8, 2, 3, 4]);
        (*output).data = Box::into_raw(encoded).cast::<u8>();
        (*output).size = 4;
        JxlBridgeStatus::Ok as c_int
    }

    unsafe extern "C" fn mock_decode(
        input: *const u8,
        input_size: usize,
        width: u32,
        height: u32,
        bits: u32,
        sample_type: u32,
        output: *mut u8,
        output_size: usize,
    ) -> c_int {
        DECODE_CALLS.fetch_add(1, Ordering::SeqCst);
        if input.is_null()
            || output.is_null()
            || input_size != 4
            || width != 2
            || height != 2
            || bits != 8
            || sample_type != JxlSampleType::Uint8 as u32
            || output_size != 4
        {
            return JxlBridgeStatus::InvalidArgument as c_int;
        }
        std::ptr::copy_nonoverlapping(input, output, output_size);
        JxlBridgeStatus::Ok as c_int
    }

    unsafe extern "C" fn mock_free(buffer: *mut JxlRawBuffer) {
        FREE_CALLS.fetch_add(1, Ordering::SeqCst);
        if !buffer.is_null() && !(*buffer).data.is_null() {
            drop(Box::from_raw((*buffer).data.cast::<[u8; 4]>()));
            (*buffer).data = std::ptr::null_mut();
            (*buffer).size = 0;
        }
    }

    fn bridge(version: JxlLibraryVersionFn) -> JxlBridge {
        unsafe { JxlBridge::from_symbols(mock_encode, mock_decode, mock_free, version) }
    }

    fn geometry() -> JxlGrayGeometry {
        JxlGrayGeometry {
            width: 2,
            height: 2,
            bits_per_sample: 8,
            sample_type: JxlSampleType::Uint8,
        }
    }

    fn reset_calls() {
        ENCODE_CALLS.store(0, Ordering::SeqCst);
        DECODE_CALLS.store(0, Ordering::SeqCst);
        FREE_CALLS.store(0, Ordering::SeqCst);
    }

    #[test]
    fn wrong_version_rejects_before_codec_invocation() {
        let _serial = TEST_LOCK.lock().unwrap();
        reset_calls();
        let bridge = bridge(wrong_version);
        let image = JxlGrayImage {
            geometry: geometry(),
            effort: 7,
            bytes: &[1, 2, 3, 4],
        };
        assert_eq!(
            bridge.encode_gray_2d(image, 4),
            Err(JxlBridgeError::WrongLibraryVersion(11_999))
        );
        let mut output = [0_u8; 4];
        assert_eq!(
            bridge.decode_gray_2d(&[1, 2, 3, 4], geometry(), &mut output),
            Err(JxlBridgeError::WrongLibraryVersion(11_999))
        );
        assert_eq!(ENCODE_CALLS.load(Ordering::SeqCst), 0);
        assert_eq!(DECODE_CALLS.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn invalid_geometry_or_size_never_reaches_codec() {
        let _serial = TEST_LOCK.lock().unwrap();
        reset_calls();
        let bridge = bridge(good_version);
        let invalid = JxlGrayImage {
            geometry: JxlGrayGeometry {
                width: 2,
                height: 2,
                bits_per_sample: 8,
                sample_type: JxlSampleType::Uint16,
            },
            effort: 7,
            bytes: &[1, 2, 3, 4],
        };
        assert!(matches!(
            bridge.encode_gray_2d(invalid, 4),
            Err(JxlBridgeError::InvalidImage(_))
        ));
        let mut too_small = [0_u8; 3];
        assert_eq!(
            bridge.decode_gray_2d(&[1, 2, 3, 4], geometry(), &mut too_small),
            Err(JxlBridgeError::InvalidOutputBuffer)
        );
        assert_eq!(ENCODE_CALLS.load(Ordering::SeqCst), 0);
        assert_eq!(DECODE_CALLS.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn bounded_mock_round_trip_releases_bridge_buffer() {
        let _serial = TEST_LOCK.lock().unwrap();
        reset_calls();
        let bridge = bridge(good_version);
        let original = [1_u8, 2, 3, 4];
        let encoded = bridge
            .encode_gray_2d(
                JxlGrayImage {
                    geometry: geometry(),
                    effort: 7,
                    bytes: &original,
                },
                4,
            )
            .unwrap();
        assert_eq!(encoded, original);
        assert_eq!(FREE_CALLS.load(Ordering::SeqCst), 1);
        let mut restored = [0_u8; 4];
        bridge
            .decode_gray_2d(&encoded, geometry(), &mut restored)
            .unwrap();
        assert_eq!(restored, original);
        assert_eq!(ENCODE_CALLS.load(Ordering::SeqCst), 1);
        assert_eq!(DECODE_CALLS.load(Ordering::SeqCst), 1);
    }
}
