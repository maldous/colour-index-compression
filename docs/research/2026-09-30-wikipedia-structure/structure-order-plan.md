# Bounded structure-order PAQ screen

Predeclared before execution. The candidate uses the existing CIXV3 text-safe
stack transform only on lexically complete, balanced XML-like fragments. It
replaces an expected close tag with a marker while retaining every other byte in
order. Comments, CDATA, entities, attributes, whitespace and numeric text are
carried byte-for-byte. A malformed quote, literal unrecognized `<`, mismatched
close or unclosed stack selects a byte-identical literal fallback.

Both arms use PAQ8PX v215 with `-4`. The control consumes original bytes. The
candidate consumes the reversible transformed byte stream. The completed outer
frames include source length, CRC, transform selection and the PAQ archive; the
smaller completed frame is selected, raw on a tie. This is a representational
predictor test, not a PAQ model modification and not a same-prediction
entropy-coder comparison.

The first screen is one balanced synthetic XML stream and fixed 32 KiB enwik9
development offsets 0, 100,000,000 and 400,000,000. It has no warm-up, a
300-second hard tree limit, CPU 2, 2 GiB RAM, no swap and 1 GiB temporary disk.
Reserved holdouts 600,000,000 and 900,000,000 remain unread unless completed
transformed frames beat raw on two development regions with exact child-process
SHA-256 restoration.
