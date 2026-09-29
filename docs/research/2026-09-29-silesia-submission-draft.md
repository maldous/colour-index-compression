# Prepared submission — not sent

Recipient: Matt Mahoney, mattmahoneyfl@gmail.com
Recipient source: https://mattmahoney.net/index.html

Subject: Silesia submission: CIX portfolio 20, 26,402,526 bytes

Hello Matt,

I would like to submit CIX portfolio 20 for your Silesia open-source compression benchmark.

The complete locally measured total is 26,402,526 bytes. All 12 canonical files were compressed independently and independently restored byte for byte. Input MD5 values match your published corpus. All physical framing and selectors are included.

| File | Compressed bytes |
| --- | ---: |
| dickens | 1,902,345 |
| mozilla | 6,477,226 |
| mr | 1,671,101 |
| nci | 447,748 |
| ooffice | 1,267,529 |
| osdb | 1,698,992 |
| reymont | 746,894 |
| samba | 1,625,132 |
| sao | 2,159,749 |
| webster | 4,626,898 |
| x-ray | 3,531,428 |
| xml | 247,484 |

CIX is a heterogeneous research compressor using PAQ8px v215/v216, Brotli and JPEG XL backends, together with reversible structural modelling for chemical records, database counts and scientific/image data. PAQ is explicitly credited; this is not a claim that a new enumerative entropy coder alone beats PAQ.

A fixed input-driven encoder policy chooses the smallest complete candidate. There is no filename/hash lookup, embedded Silesia payload, external shared corpus or decoder access to the original input. The ordinary CLI does not require benchmark caches. Completed benchmark artifacts were reused during research only after matching input, frame, source and backend identities and independent full-restoration evidence.

Source: [PUBLIC RELEASE URL TO BE FILLED ONLY AFTER AUTHORIZED PUBLICATION].
Prepared source archive SHA256: d53c5509318620249da31a2cf5299c2b6f5497a7043f7bcc7788021bc35c7637.
Source revision: 6e704a3ae38a8438c3db441f3b1e212d8f089464.

Reproduction: build the included native sources using the supplied instructions, then run `python -m benchmarks.competitive_cli encode input.bin output.cix` and `python -m benchmarks.competitive_cli decode output.cix restored.bin` for each file independently. The documented environment is Linux x86-64 with AVX2, Python 3.12 and GCC 13.3; exact qualified backend builds are currently enforced. Encoding is slow, and the full uncached portfolio has not been timed end to end. Recorded per-candidate times, peak memory, output sizes and hashes are available. The research measurements ran locally under concurrent load, so no uniform speed ranking is claimed.

Your leaderboard currently lists PAQ8px v215 -12L at 27,825,511 bytes; this result is 1,422,985 bytes smaller. I understand that the equivalent numerical position is not an official listing until you assess it. Please let me know whether any additional qualification or presentation is needed.

Matthew Aldous

## Publication plan — awaiting explicit authorization

- Publish only the prepared source package and its result/build documentation in a new public repository, proposed `maldous/cix-silesia`.
- Keep `maldous/colour-index-compression` and its existing history private.
- Include no workflow files; do not trigger or use GitHub Actions.
- Verify an unauthenticated download of the exact published source archive before sending this submission.
- Send only this reviewed submission, after publication and explicit authorization to contact the maintainer. No message has been sent.
