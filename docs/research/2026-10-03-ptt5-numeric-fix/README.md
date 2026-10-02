# Verified ptt5 numeric maximum fix

Fixed source `8439f4c414b06d0ff328c57c6bbc3b065f30c05a` changes only
optional numeric integer-class eligibility. When value+1 cannot be represented,
the encoder retains the already valid varint/Rice candidate rather than
failing the whole BEST portfolio. No wrapping, integer truncation, decoder
change or broad candidate error suppression is introduced. Independent source
review approved this change and its added boundary regression tests.

Per latest user instructions, validation used **one** full ptt5 BEST encode
and one fresh frozen-BD2 decoder process. Separate unit test execution was
cancelled and is not claimed passed. Baselines were reused, not rerun.

- Input: 513,216 bytes; SHA-256 `0ec3a75089bb52342813496b17e51377bc9eba3cb519a444d67025354841d650`.
- Complete archive: **27,614 bytes**, matching the existing
  pre-refactor Rust baseline; SHA-256 `72ba1e86d53b8e2f0f4490bd0e98080f21587fe9e6997183f4c4738997dc0dea`.
- Fresh archive-only frozen BD2 decode: byte equality and identical SHA-256.
- Encode wall: 490.89 s; CPU:
  527.02 s; peak process RSS:
  148,500,480 bytes.
- Decode wall: 2.03 s; peak process RSS:
  98,304,000 bytes.
- Four allowed physical CPUs16–19; memory ceiling2,899,996,672 bytes; zero swap.
  Actual inner affinity and cgroup readbacks retained. No averaging or speed
  superiority claim is made from this single validation. Work-directory temp
  high water includes the retained build target, not only compressor scratch.

The original failing v2 measurement remains UNQUALIFIED. The initial build
invocation missing Cargo manifest path and the user-cancelled unit phase remain
raw evidence. Corrected locked release-LTO/all-feature build exited0.

Binaries: `benchmark-work/ptt5-fixed-8439/final/`. The full corpus benchmark
is stopped. Sonar zero-issue evidence pertains to prior BD2; this small fix has
source review and exact fixture validation, not a fresh Sonar scan.
