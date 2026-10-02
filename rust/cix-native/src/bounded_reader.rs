//! Bounded, single-pass source buffering for whole-input candidates.
//!
//! Callers provide both a format limit and an admitted source-buffer limit.
//! The extra byte is read into a stack buffer, so an over-limit source never
//! causes the retained `Vec` to grow merely to report the limit violation.

use std::io::{self, Read};

const CHUNK: usize = 64 * 1024;

pub fn read_bounded<R: Read>(mut source: R, maximum: usize, allowance: usize) -> io::Result<Vec<u8>> {
    if allowance > maximum {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "source allowance exceeds maximum"));
    }
    let mut out = Vec::with_capacity(allowance.min(CHUNK));
    let mut buffer = [0u8; CHUNK];
    loop {
        let remaining = maximum.saturating_sub(out.len());
        let requested = remaining.min(buffer.len());
        if requested == 0 {
            // Do not retain a max+1 byte: the fixed probe proves overflow.
            if source.read(&mut buffer[..1])? != 0 {
                return Err(io::Error::new(io::ErrorKind::InvalidData, "input exceeds bounded source limit"));
            }
            return Ok(out);
        }
        let got = source.read(&mut buffer[..requested])?;
        if got == 0 {
            return Ok(out);
        }
        let needed = out.len().checked_add(got).ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "input length overflow"))?;
        if needed > allowance {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "input exceeds admitted source buffer"));
        }
        if needed > out.capacity() {
            let target = out.capacity().max(1).saturating_mul(2).max(needed).min(allowance);
            out.try_reserve_exact(target - out.capacity())
                .map_err(|_| io::Error::new(io::ErrorKind::OutOfMemory, "cannot reserve bounded source buffer"))?;
            if out.capacity() > allowance {
                return Err(io::Error::new(io::ErrorKind::OutOfMemory, "source allocation exceeded admitted buffer"));
            }
        }
        out.extend_from_slice(&buffer[..got]);
    }
}
