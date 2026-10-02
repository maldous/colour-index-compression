use cix_native::ppm;
use sha2::{Digest, Sha256};

fn main() {
    let input: Vec<u8> = (0..4096).map(|i| ((i * 17 + i / 23) & 255) as u8).collect();
    let prefix: Vec<u8> = (0..257).map(|i| ((i * 11) & 255) as u8).collect();
    let fixed = ppm::encode_fixed(&input, 3, &prefix, 2, true).unwrap();
    let see = ppm::encode_secondary(&input, 3, &prefix, true).unwrap();
    assert_eq!(ppm::decode_with_history(&fixed, input.len(), &prefix).unwrap(), input);
    assert_eq!(ppm::decode_with_history(&see, input.len(), &prefix).unwrap(), input);
    if let Ok(dir) = std::env::var("CIX_AUDIT_OUT") {
        std::fs::write(format!("{dir}/fixed.bin"), &fixed).unwrap();
        std::fs::write(format!("{dir}/see.bin"), &see).unwrap();
    }
    if let Ok(path) = std::env::var("CIX_AUDIT_FOREIGN_FIXED") {
        assert_eq!(ppm::decode_with_history(&std::fs::read(path).unwrap(), input.len(), &prefix).unwrap(), input);
    }
    if let Ok(path) = std::env::var("CIX_AUDIT_FOREIGN_SEE") {
        assert_eq!(ppm::decode_with_history(&std::fs::read(path).unwrap(), input.len(), &prefix).unwrap(), input);
    }
    assert!(ppm::decode(&[6, 0, 0], 1).is_err());
    println!("fixed {} {:x}", fixed.len(), Sha256::digest(&fixed));
    println!("see {} {:x}", see.len(), Sha256::digest(&see));
}
