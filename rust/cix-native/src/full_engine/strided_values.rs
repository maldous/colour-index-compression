//! Bounded recognition primitives for the historical 28-byte WCSTools grid.
//!
//! The full grid frame codecs retain several independently paid representations
//! (CIXS1, CIXY1, CIXZ1 and CIXB variants).  Their shared admission condition is
//! deliberately narrow: exactly the standard seven-int header followed by the
//! declared count of 28-byte records.

pub const RECORD_BYTES: usize = 28;
pub const MAX_RECORDS: usize = 8_000_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct WcsGrid {
    pub records: usize,
}

fn le_i32(data: &[u8], at: usize) -> Option<i32> {
    Some(i32::from_le_bytes(
        data.get(at..at.checked_add(4)?)?.try_into().ok()?,
    ))
}

/// Returns a grid only for the exact historical WCSTools subset.  The count's
/// sign is retained only for compatibility with the source recognizer; the
/// archive transform consumes the absolute number of records.
pub fn recognize_wcs_grid(data: &[u8]) -> Option<WcsGrid> {
    if data.len() < RECORD_BYTES {
        return None;
    }
    let count = le_i32(data, 8)?;
    let stnum = le_i32(data, 12)?;
    let mprop = le_i32(data, 16)?;
    let nmag = le_i32(data, 20)?;
    let width = le_i32(data, 24)?;
    let records = count.unsigned_abs() as usize;
    if count == 0
        || records > MAX_RECORDS
        || stnum != 0
        || mprop != 1
        || nmag.unsigned_abs() != 1
        || width != RECORD_BYTES as i32
    {
        return None;
    }
    let expected = RECORD_BYTES.checked_add(RECORD_BYTES.checked_mul(records)?)?;
    (expected == data.len()).then_some(WcsGrid { records })
}

pub fn zigzag_i64(value: i64) -> u64 {
    if value >= 0 {
        (value as u64) << 1
    } else {
        ((-value as u64) << 1) - 1
    }
}
pub fn unzigzag_i64(value: u64) -> i64 {
    if value & 1 == 0 {
        (value >> 1) as i64
    } else {
        -((value >> 1) as i64) - 1
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn recognizes_exact_wcs_extent() {
        let mut data = vec![0u8; RECORD_BYTES * 2];
        data[8..12].copy_from_slice(&(1i32).to_le_bytes());
        data[16..20].copy_from_slice(&(1i32).to_le_bytes());
        data[20..24].copy_from_slice(&(1i32).to_le_bytes());
        data[24..28].copy_from_slice(&(28i32).to_le_bytes());
        assert_eq!(recognize_wcs_grid(&data), Some(WcsGrid { records: 1 }));
        data.push(0);
        assert_eq!(recognize_wcs_grid(&data), None);
    }

    #[test]
    fn signed_varint_mapping_round_trips() {
        for value in [-123i64, -1, 0, 1, 127] {
            assert_eq!(unzigzag_i64(zigzag_i64(value)), value);
        }
    }
}
