# Known better per-member candidates — read-only preflight

## Status

This ledger supplements, and does not modify, [`regression-baseline.md`](regression-baseline.md).  Each item is a certificate-backed historical per-member result that beats the `portfolio26` selected member by the stated amount.  They are not a fresh encode, not an integrated-runtime result, and are **not summed into a new portfolio total**.

## Candidates

| Member | Historical portfolio26 bytes | Better candidate bytes | Difference | Status for the authorised pass |
|---|---:|---:|---:|---|
| dickens | 1,902,345 | 1,862,182 | −40,163 | Must be accounted for as a resource-admitted generic PAQ v215 `-9L` candidate; historical 24–48 MiB LSTM-tier admission excluded it because the input is below that range. |
| mr | 1,671,101 | 1,671,099 | −2 | Preserve the smaller CIXI envelope or its equivalent; payload is already identical. |
| webster | 4,423,086 | 4,390,572 | −32,514 | Reference only under the current 12 GB bound: its historical `-12L` run peaked at 22,838,084 KiB encoding and 23,631,616 KiB decoding. |

### Dickens: PAQ8px v215 `-9L`

[`result.json`](../../../../results/leaderboard/paq-v215-text9L-20260929/dickens/result.json) records a complete 1,862,182-byte archive for the canonical 10,192,446-byte Dickens input.  Its archive SHA-256 is `d42fcac0f53462184003b5b557db272a0a80f93b80a0b5a8002684727f7c364f`; the recorded restored SHA-256 equals the canonical input SHA-256 `b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a`.

The recorded binary is SHA-256 `b982f1e8307d6c38e8febc6415901fafcc2e84a14d51e0af7c5cbbe6322778e7`, built from PAQ8px v215 source tag/commit `e80eed27ae8a673ccb016f1b158cff1b7150fcf6`, source archive SHA-256 `e3a86a08961f90bab73b01cb3db27327471a701b6ac2dde0c972e5b6f78c0737`, with AVX2.  The runner source SHA-256 is `d8a9145220ee55ffb7658d8aa58d631f45ec8e081ac9cc79e3235fb6543c9030`; its recorded revision is `7846eac0cd1251d96013857c0b5e59a4fc2e94ee`.

Recorded physical costs are 3,617.151 seconds encode at 3,794,160 KiB peak RSS and 2,970.500 seconds decode at 3,782,912 KiB.  The old `competitive_prediction_v24.py` LSTM policy placed `-9L` in a 24–48 MiB input-size tier, so it did not admit this 10,192,446-byte input.  That was a portfolio staging rule, not a decoder or input-schema constraint.  This candidate must still meet the frozen current resource policy and standalone decoding requirement; the evidence here does not assert that it will be admitted or selected.

### MR: two bytes of envelope, not a new payload result

[`complete.json`](../../../../results/leaderboard/multiscale-volume-20260928/mr-r0-a0-l0-p0/complete.json) records a 1,671,099-byte complete CIXI stream, input/frame/restoration hashes, and a successful round trip.  It names source revision `1a7b5643044d1ab3285c28ab74e7310fa44283bf`, source hashes for `multiscale_volume.py`, `spatial_image_codec.py`, and the JPEG XL ABI, and imagecodecs 2026.8.16 / libjxl 0.12.0.

Read-only binary comparison with portfolio26’s 1,671,101-byte `mr.cixc` found an exact common suffix of 1,668,279 bytes.  That equals the recorded `band_bytes[0]` of the CIXI result.  The streams first differ in their envelope, and their lengths differ by exactly two bytes.  Therefore the evidence supports **same JXL payload, different framing with two bytes less overhead**, not a distinct two-byte modelling/compression gain.  No archive hashing or decode was rerun for this ledger.

The CIXI record reports 54.661 seconds encoding, 0.659 seconds decoding, and 395,360 KiB peak RSS.  Its frame SHA-256 is `93df5cd94b2bbe0e981bf1863a90334925fb8b472b92f0a10907f78acf343963`; portfolio26’s distinct CIXV frame SHA-256 is `797b8920c951ee007fa0200d146814ea5c33cfcdd5630d6e95077ae35717c868`.

### Webster: resource-excluded high-memory reference

[`result.json`](../../../../results/leaderboard/paq-v215-reference/webster/result.json) records a complete 4,390,572-byte PAQ8px v215 `-12L` AVX2 archive.  Archive SHA-256 is `ed14ac80c2139f91827980626f27f8c493cdf89020f7d2a9c2700d748a48d690`; the restored SHA-256 equals the canonical Webster input SHA-256 `6a68f69b26daf09f9dd84f7470368553194a0b294fcfa80f1604efb11143a383`.

It has the same recorded PAQ source/binary identity as Dickens, with runner revision `76d783bb9a99ab0940fc79b2d4daa283697ceb0b`.  Its recorded costs are 21,847.328 seconds encode, 11,667.622 seconds decode, 22,838,084 KiB encode RSS, and 23,631,616 KiB decode RSS.  Those peak values exceed the approved decimal 12 GB / no-swap bound, so it is a retained quality reference rather than a candidate under that bound.

## Provenance and limits

The two PAQ streams and both result receipts are locally present, and their recorded archive hashes are preserved above.  This preflight did not rehash, re-encode, or re-decode them.  The MR conclusion is based on recorded full certificate fields plus a byte comparison of existing archives; it does not claim a new verification.  No current integrated binary is identified here, no resource estimate has been re-measured, and no candidate has been added to a total.  The next frozen runtime must disclose resource exclusion or independently reproduce a complete archive before using any of these values in a current result.
