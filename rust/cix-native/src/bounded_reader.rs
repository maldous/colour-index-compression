//! Bounded, single-pass source buffering for whole-input candidates.
//!
//! Callers provide both a format limit and an admitted source-buffer limit.
//! The extra byte is read into a stack buffer, so an over-limit source never
//! causes the retained `Vec` to grow merely to report the limit violation.

use std::io::{self, Read};

const CHUNK: usize = 64 * 1024;

/// Conservative source allowance for a read budget that must cover both the
/// old and replacement Vec allocations plus the stack chunk during growth.
/// This is allocator accounting, not an RSS guarantee.
pub fn conservative_allowance(total_read_budget: usize) -> usize {
    total_read_budget.saturating_sub(CHUNK) / 2
}

pub fn read_bounded<R: Read>(mut source: R, maximum: usize, allowance: usize) -> io::Result<Vec<u8>> {
    if allowance > maximum {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "source allowance exceeds maximum"));
    }
    let mut out = Vec::new();
    let initial = allowance.min(CHUNK);
    if initial != 0 {
        out.try_reserve_exact(initial)
            .map_err(|_| io::Error::new(io::ErrorKind::OutOfMemory, "cannot reserve bounded source buffer"))?;
        if out.capacity() > allowance {
            return Err(io::Error::new(io::ErrorKind::OutOfMemory, "source allocation exceeded admitted buffer"));
        }
    }
    let mut buffer = [0u8; CHUNK];
    loop {
        let remaining = maximum.saturating_sub(out.len());
        let requested = remaining.min(buffer.len());
        if requested == 0 {
            // Do not retain a max+1 byte: the fixed probe proves overflow.
            let probe = read_retry(&mut source, &mut buffer[..1])?;
            if probe != 0 {
                return Err(io::Error::new(io::ErrorKind::InvalidData, "input exceeds bounded source limit"));
            }
            return Ok(out);
        }
        let got = read_retry(&mut source, &mut buffer[..requested])?;
        if got == 0 {
            return Ok(out);
        }
        let needed = out.len().checked_add(got).ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "input length overflow"))?;
        if needed > allowance {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "input exceeds admitted source buffer"));
        }
        if needed > out.capacity() {
            let target = out.capacity().max(1).saturating_mul(2).max(needed).min(allowance);
            if out.capacity().saturating_add(target) > allowance.saturating_mul(2) {
                return Err(io::Error::new(io::ErrorKind::OutOfMemory, "source growth exceeds admitted transient buffer"));
            }
            // `try_reserve_exact` takes additional elements relative to len,
            // rather than relative to capacity.
            out.try_reserve_exact(target - out.len())
                .map_err(|_| io::Error::new(io::ErrorKind::OutOfMemory, "cannot reserve bounded source buffer"))?;
            if out.capacity() < needed || out.capacity() > allowance {
                return Err(io::Error::new(io::ErrorKind::OutOfMemory, "source allocation exceeded admitted buffer"));
            }
        }
        out.extend_from_slice(&buffer[..got]);
    }
}

fn read_retry<R: Read>(source: &mut R, buffer: &mut [u8]) -> io::Result<usize> {
    loop {
        match source.read(buffer) {
            Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
            result => return result,
        }
    }
}
