# Native-final v2 cache delta v1

Date: 2026-10-05  
Scope: read-only comparison of the failed v2 job cache, its v2 receipt, and the retained distribution-engineering-v4 cache. No cache was removed.

`benchmark-work/native-rc-check-v1/native-final-source-v2/target` has 306 regular files and no symlinks. The retained `distribution-engineering-v4/target` tree also has 306 regular files and no symlinks. Their path sets are identical. The retained file hashes exactly equal `copied_lto_target.files_sha256` in the immutable v2 receipt.

The failed-job copy differs in exactly one member: `.rustc_info.json`. Its copied version is 1,269 bytes with SHA-256 `c77a25e289b63bbe72cd244563e847458ba478d1812d33d72ed6c288ebcb16eb`; the retained/receipt version is 1,268 bytes with SHA-256 `992942b8145317617b71dafce64b2f9f0a4744d6bde022045b6f90fb99d9086f`. The two JSON files differ only in Cargo’s hashed probe keys and `rustc_fingerprint`; both record the same Rust 1.98.1 compiler output.

The v2 Clippy phase failed after 0.22 seconds on Cargo parsing `CARGO_PROFILE_RELEASE`, before it could load the profile value. Its stderr contains only that configuration error. This is evidence that the changed member is Cargo’s compiler-information metadata generated before compilation; it does not establish a successful compile.

The prepared `native-final-v3-cache-reclaim` job will re-check all of these facts at execution time. It copies the sole changed `.rustc_info.json` into a new preserved evidence directory, verifies its byte hash and mode, records the receipt and both metadata identities, re-checks both cache trees, and only then removes the v2 duplicate. Any added, removed, other changed, symlink, hardlink, active-writer, source-receipt, or retained-cache difference aborts with no deletion.
