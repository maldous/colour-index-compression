# ELF relative-relocation forward-transfer audit

## Purpose and boundary

Portfolio 25’s Mozilla selection used an ECOFF/Alpha-specific section/function
pointer transform followed by PAQ v215 -8. The active P25 wrapper was
`section-constraints-paq-v215-8-mode4`; it checked an already completed
whole-frame artifact and its transformed source hash before admitting that
artifact. The original mechanism used parsed section bounds, relocation-derived
pointer locations, function-address pools and membership flags. Its gain cannot
be assigned wholly to the transform because the selected stream uses a different
PAQ backend from the v216 -8 comparison control.

This audit asks a narrower question on a new input: can a standard ELF relation
be made explicit without external state, and does its complete, charged
representation help the *same* PAQ configuration? It contains no PAQ result.

## New frozen input

The source is the complete installed executable
`/usr/bin/x86_64-linux-gnu-strip`, selected because it is a legitimate
166,568-byte ELF64 PIE, rather than a truncated object or a Silesia member.

| Field | Value |
| --- | --- |
| Debian package | `binutils 2.42-4ubuntu2.10 amd64` |
| ELF class / machine | ELF64 little-endian / x86-64 |
| ELF build ID | `3b7722bf379fc146d44962751f273d1c4e3f0620` |
| source SHA-256 | `0d980587ada7ab12193f39271f060d5663aa2f289b0e80d2a0274ce7306e4e42` |
| immutable project copy | `input/strip-0d980587ada7.bin` |
| copy SHA-256 | identical to source |
| source bytes | 166,568 |

The provenance and transform coverage are machine-generated in
`executable-audit.json`. The adapter copied the input only after checking that
an existing destination could not be silently replaced by different bytes.

## Implemented relation

`benchmarks/domain_executable_adapter.py` accepts only ELF64 little-endian
x86-64. It parses the ELF section-header table and SHT_RELA records. For every
`R_X86_64_RELATIVE` relocation whose addend belongs to a parsed section, the
address variant replaces the signed 64-bit addend with
`addend - section_address`.

The decoder reconstructs the same relocation order from the transformed ELF and
reads a paid membership bit for every relative relocation plus a paid varint
section index for every normalized addend. It restores the original address,
then verifies the original length and CRC. The complete archive-only frame
contains the transformed ELF and metadata; it needs no binary, symbols, linker
state, filename or package data to decode.

The frozen executable has 30 section headers, two RELA sections and 155
relative relocations. All 155 addends map to one of four parsed target sections.
The raw frame is 166,610 bytes (+42); the individual-varint address frame is
166,766 bytes (+198). These are physical frame overheads before PAQ, not
compression results.

### Recoverable section-index packing ablation

The original address variant pays one unsigned varint per selected section
index. For this input every selected ID lies in the known, decoder-parsed table
of 30 section headers. The new `address-packed` variant leaves the transformed
fields and membership flags unchanged, but treats the selected section IDs as a
single exact base-30 mixed-radix integer. The decoder knows both the base and
the number of digits from the same section table and paid membership bitmap, so
it reads the minimal fixed byte width for the exact rank. No palette is implied
or omitted.

On `strip`, 155 individual IDs cost 155 bytes; their exact packed rank costs
95 bytes. The complete `address-packed` frame is 166,706 bytes, 60 bytes below
the existing address frame and 138 bytes above original input. This is only
recoverable metadata packing. PAQ may already model repeated one-byte section
IDs efficiently, so a complete same-PAQ comparison is required to establish
any net effect.

## What transfers and what does not

The transferable part is the reversible relation “a dynamic relative-relocation
addend lies in a declared address interval.” It uses declared in-file metadata
and has an explicit escape/membership representation. The non-transferable
parts of the P25 winner remain non-transferable: ECOFF layout, Alpha function
address conventions, fixed instruction width, function extraction from
`.pdata`, and the historical P25 PAQ v215 selection.

This adapter intentionally does not decode x86 instructions, predict calls,
inspect names, require symbols, assume a generic ELF ABI, or claim support for
other architectures. An ELF input outside its explicit ELF64/x86-64 contract is
rejected instead of being treated as an equivalent object.

## PAQ capacity-sharing test

Root may schedule exactly four whole-input measurements under the shared
resource budget, all with the same pinned PAQ v216 `-4 -simd AVX2` command:

1. original 166,568 source bytes;
2. complete `encode(data, "raw")` frame, which measures container/framing cost;
3. complete `encode(data, "address")` frame, which measures section-relative
   normalization plus all membership/section metadata.
4. complete `encode(data, "address-packed")` frame, which changes only the
   paid section-ID representation.

Each PAQ output must be decoded first by PAQ and then by
`domain_executable_adapter.decode` where applicable, and compared byte-for-byte
to the frozen input. Report raw bytes, complete-frame bytes and PAQ bytes. A
smaller PAQ stream would show only that this representation assists PAQ on this
one ELF; it would not show that the transform owns the saving. A result no
smaller than the raw-frame ablation shows the relation does not repay its
metadata and does not warrant broader ELF work.
