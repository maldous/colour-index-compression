// Audit-only direct fixed-PPM eligible-scan kernel benchmark.
use cix_native::ppm;
use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use sha2::{Digest, Sha256};

const INPUT_BYTES: usize = 4 * 1024;

fn random_input() -> Vec<u8> {
    let mut state = 0x9e37_79b9_u32;
    (0..INPUT_BYTES)
        .map(|index| {
            state ^= state << 13;
            state ^= state >> 17;
            state ^= state << 5;
            (state as u8).wrapping_add(((index / 17) % 11) as u8)
        })
        .collect()
}

fn de_bruijn(t: usize, p: usize, a: &mut [u8], out: &mut Vec<u8>) {
    const K: usize = 16;
    const N: usize = 3;
    if t > N {
        if N.is_multiple_of(p) {
            out.extend_from_slice(&a[1..=p]);
        }
        return;
    }
    a[t] = a[t - p];
    de_bruijn(t + 1, p, a, out);
    for value in (a[t - p] + 1)..K as u8 {
        a[t] = value;
        de_bruijn(t + 1, t, a, out);
    }
}

fn input(case: &str) -> Vec<u8> {
    match case {
        "random" => random_input(),
        "strong" => (0..INPUT_BYTES)
            .map(|index| b'A' + (index % 4) as u8)
            .collect(),
        "weak" => (0..INPUT_BYTES)
            .map(|index| ((index * 17 + index / 23) & 0xff) as u8)
            .collect(),
        "absent" => {
            let mut sequence = Vec::with_capacity(INPUT_BYTES);
            de_bruijn(1, 1, &mut [0; 4], &mut sequence);
            sequence
        }
        other => panic!("unknown CIX_AUDIT_CASE={other}"),
    }
}

fn ppm_eligible_kernel(c: &mut Criterion) {
    let case = std::env::var("CIX_AUDIT_CASE").unwrap_or_else(|_| "random".into());
    let escape_method = std::env::var("CIX_AUDIT_ESCAPE_METHOD").map_or(0, |value| {
        value.parse().expect("valid CIX_AUDIT_ESCAPE_METHOD")
    });
    let update_exclusion =
        std::env::var("CIX_AUDIT_UPDATE_EXCLUSION").map_or(false, |value| value == "1");
    let input = input(&case);
    let encoded =
        ppm::encode_fixed(&input, 3, &[], escape_method, update_exclusion).expect("PPM encode");
    assert_eq!(
        ppm::decode(&encoded, input.len()).expect("PPM decode"),
        input
    );
    if let Ok(path) = std::env::var("CIX_AUDIT_PAYLOAD_OUT") {
        std::fs::write(path, &encoded).expect("write audit payload");
    }
    if let Ok(path) = std::env::var("CIX_AUDIT_CROSS_PAYLOAD") {
        let foreign = std::fs::read(path).expect("read cross payload");
        assert_eq!(
            ppm::decode(&foreign, input.len()).expect("cross decode"),
            input
        );
    }
    println!(
        "audit-case={case} audit-escape-method={escape_method} audit-update-exclusion={update_exclusion} audit-input-sha256={:x} audit-payload-bytes={} audit-payload-sha256={:x}",
        Sha256::digest(&input), encoded.len(), Sha256::digest(&encoded),
    );
    let mut group = c.benchmark_group(format!("ppm-eligible-direct-kernel/{case}"));
    group.throughput(Throughput::Bytes(INPUT_BYTES as u64));
    group.bench_with_input(
        BenchmarkId::new("encode_o3_fresh", INPUT_BYTES),
        &input,
        |b, data| {
            b.iter(|| {
                black_box(
                    ppm::encode_fixed(black_box(data), 3, &[], escape_method, update_exclusion)
                        .expect("PPM encode"),
                )
            })
        },
    );
    group.bench_with_input(
        BenchmarkId::new("decode_o3_fresh", INPUT_BYTES),
        &encoded,
        |b, payload| {
            b.iter(|| black_box(ppm::decode(black_box(payload), INPUT_BYTES).expect("PPM decode")))
        },
    );
    group.finish();
}

fn audit_criterion() -> Criterion {
    match std::env::var("CIX_AUDIT_CRITERION_DIR") {
        Ok(output) => Criterion::default().output_directory(std::path::Path::new(&output)),
        Err(_) => Criterion::default(),
    }
}

criterion_group! { name = benches; config = audit_criterion(); targets = ppm_eligible_kernel }
criterion_main!(benches);
