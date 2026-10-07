# Wavelet and bitplane warning cleanup

The wavelet decoder consolidates identical zero outcomes using a short-circuit
condition. It does not call the arithmetic target when the one-count is zero.
The bitplane decoder helper moves before its test module unchanged. The new
wavelet round-trip test exercises the actual encoder and decoder.

Independent source review approved these changes. Focused native checks
passed: four bitplane tests, two final wavelet round-trip/overflow tests, and
two histogram tests. This is functional evidence; it does not qualify
throughput, resource scaling or a whole-profile performance result.

The earlier full-library run was stopped to reduce scope while in the long
chain fixture; its log is retained and is not an all-tests pass. Earlier
intermediate diffs/logs are preserved; `wavelet-bitplane-cleanup-final.diff`
and `wavelet-roundtrip-final.log` describe the final change and focused check.
Final combined release validation and Sonar scan remain required.
