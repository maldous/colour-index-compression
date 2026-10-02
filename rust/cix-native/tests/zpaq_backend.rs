use cix_native::external::{decode, encode_zpaq};

#[test]
fn pinned_zpaq715_level5_round_trips_large_fixture_and_rejects_trailing_data() {
    // More than one MiB exercises libzpaq's block/model path rather than only
    // a tiny header fixture. The CIX envelope supplies the independent SHA-256
    // check in addition to ZPAQ's own block checksum.
    let input = b"ZPAQ level five CIX bounded native fixture 0123456789\n".repeat(32_768);
    let archive = encode_zpaq("size", &input, 5).expect("encode pinned ZPAQ");
    assert_eq!(decode(&archive, 2 * 1024 * 1024 * 1024).unwrap(), input);

    let mut trailing = archive;
    trailing.push(0);
    let payload_size = u32::try_from(trailing.len() - 47).unwrap();
    trailing[11..15].copy_from_slice(&payload_size.to_le_bytes());
    assert!(decode(&trailing, 2 * 1024 * 1024 * 1024).is_err());

    // Empty originals are still a tagged ZPAQ stream. A forged CIXB1
    // envelope with a zero payload must not become an alternate spelling.
    let mut missing_payload = encode_zpaq("size", &[], 5).expect("encode empty ZPAQ");
    missing_payload.truncate(47);
    missing_payload[11..15].copy_from_slice(&0u32.to_le_bytes());
    assert!(decode(&missing_payload, 2 * 1024 * 1024 * 1024).is_err());
}
