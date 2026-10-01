use cix_native::external::{
    backend_version, best_candidates, decode, experimental_candidates, BrotliMode, CandidateConfig,
    CandidateDescriptor, MAX_INPUT, ONE_SHOT_CANCELLATION_LIMITATION,
};

const HEADER: usize = 47;

#[test]
fn registry_covers_every_existing_best_backend_configuration() {
    let ids: Vec<_> = best_candidates()
        .iter()
        .map(|candidate| candidate.id)
        .collect();
    assert_eq!(
        ids,
        vec![
            "gzip-fast",
            "gzip-size",
            "bzip2-size",
            "xz-default-6",
            "xz-size-9e",
            "zstd-fast",
            "zstd-default-3",
            "zstd-size-22",
            "brotli-fast-0",
        ]
    );
    // The direct API has no distinct gzip default payload configuration.
    assert!(!ids.contains(&"gzip-default"));
    for backend in ["gzip", "bzip2", "xz", "zstd", "brotli"] {
        assert!(!backend_version(backend).unwrap().is_empty(), "{backend}");
    }
}

#[test]
fn canonical_candidates_make_complete_decodable_cixb1_archives() {
    let input = b"CIXB1 backend registry fixture\0with repeats CIXB1 backend registry fixture";
    for candidate in best_candidates()
        .iter()
        .filter(|candidate| candidate.config == CandidateConfig::Canonical)
    {
        let archive = candidate
            .full_archive_encode(input)
            .unwrap_or_else(|error| {
                panic!("{} did not encode: {error}", candidate.id);
            });
        assert_eq!(&archive[..5], b"CIXB1", "{}", candidate.id);
        assert_eq!(
            archive[6],
            match candidate.profile {
                "fast" => 1,
                "default" => 2,
                "size" => 3,
                _ => unreachable!(),
            }
        );
        assert_eq!(
            u32::from_le_bytes(archive[7..11].try_into().unwrap()) as usize,
            input.len()
        );
        let payload_size = u32::from_le_bytes(archive[11..15].try_into().unwrap()) as usize;
        assert_eq!(archive.len(), HEADER + payload_size, "{}", candidate.id);
        // XZ's canonical size preset advertises a large decoder dictionary;
        // give the archive-only decoder its declared resource headroom.
        assert_eq!(
            decode(&archive, 2 * 1024 * 1024 * 1024).unwrap(),
            input,
            "{}",
            candidate.id
        );
    }
}

#[test]
fn experimental_registry_retains_typed_brotli_quality_11_with_self_describing_payload() {
    let candidate = experimental_candidates()
        .iter()
        .find(|candidate| candidate.id == "brotli-size-q11-generic-w22")
        .expect("experimental Brotli quality-11 candidate");
    assert_eq!(candidate.backend, "brotli");
    assert_eq!(candidate.profile, "size");
    assert_eq!(
        candidate.config,
        CandidateConfig::BrotliQuality {
            quality: 11,
            lgwin: 22,
            mode: BrotliMode::Generic,
        }
    );
    let input = b"typed generic Brotli CIXB1 fixture ".repeat(1024);
    let archive = candidate.full_archive_encode(&input).unwrap();
    assert_eq!(&archive[..5], b"CIXB1");
    assert_eq!(archive[5], 5);
    assert_eq!(archive[6], 3);
    assert_eq!(
        decode(&archive, candidate.decoder_peak_bytes(input.len()).unwrap()).unwrap(),
        input
    );
    assert!(candidate.encoder_peak_bytes(input.len()).unwrap() >= 256 * 1024 * 1024);
    assert!(ONE_SHOT_CANCELLATION_LIMITATION.contains("Brotli"));
}

#[test]
fn estimates_use_native_queries_and_never_underflow_output_storage() {
    let input_len = 123_456;
    for candidate in best_candidates() {
        let estimate = candidate.encoder_peak_bytes(input_len).unwrap();
        assert!(
            estimate >= 2 * (input_len + 1024 * 1024),
            "{}",
            candidate.id
        );
        assert_eq!(candidate.admit(input_len, estimate).unwrap(), estimate);
        assert!(candidate.decoder_peak_bytes(input_len).unwrap() >= input_len);
    }
    let xz_easy = best_candidates()
        .iter()
        .find(|candidate| candidate.id == "xz-size-9e")
        .unwrap()
        .encoder_peak_bytes(input_len)
        .unwrap();
    let xz_dict = experimental_candidates()
        .iter()
        .find(|candidate| candidate.id == "xz-dict128-size-9e")
        .unwrap()
        .encoder_peak_bytes(input_len)
        .unwrap();
    assert!(xz_dict > xz_easy);
}

#[test]
fn admission_reports_exact_need_and_rejects_limit_or_overflow_inputs() {
    let candidate = best_candidates()
        .iter()
        .find(|candidate| candidate.id == "zstd-size-22")
        .unwrap();
    let needed = candidate.encoder_peak_bytes(1).unwrap();
    let omission = candidate.admit(1, needed - 1).unwrap_err();
    assert_eq!(omission.needed_bytes, needed);
    assert_eq!(omission.available_bytes, needed - 1);
    assert!(omission.reason.contains("need"));
    assert!(candidate.encoder_peak_bytes(MAX_INPUT + 1).is_err());
    assert!(candidate.admit(MAX_INPUT + 1, usize::MAX).is_err());
}

#[test]
fn descriptor_is_a_stable_public_configuration_value() {
    let candidate = CandidateDescriptor {
        id: "fixture",
        backend: "gzip",
        profile: "size",
        config: CandidateConfig::Canonical,
    };
    assert!(candidate.encoder_peak_bytes(0).unwrap() > 0);
}

#[test]
fn unqualified_settings_are_not_automatically_selected() {
    assert_eq!(experimental_candidates().len(), 3);
    for candidate in experimental_candidates() {
        assert!(!best_candidates()
            .iter()
            .any(|entry| entry.id == candidate.id));
    }
}

#[test]
fn malformed_gzip_cannot_expand_beyond_declared_length() {
    let mut archive = cix_native::external::encode("gzip", "size", &vec![b'a'; 1_048_576]).unwrap();
    archive[7..11].copy_from_slice(&1u32.to_le_bytes());
    assert!(decode(&archive, 16 * 1024 * 1024).is_err());
}

#[test]
fn decoder_requires_output_and_native_workspace_budget() {
    let archive = cix_native::external::encode("bzip2", "size", b"budget").unwrap();
    assert!(decode(&archive, archive.len() + 7)
        .unwrap_err()
        .contains("memory/resource"));
}
