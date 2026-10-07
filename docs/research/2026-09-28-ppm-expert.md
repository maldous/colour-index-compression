# Generic byte-level PPM expert inside the bit mixer

CIXQ5 extends the rounded, longer-context mixer with one byte-distribution
expert. An order-six PPM-C-style model uses only already decoded bytes, update
without exclusion, and count rescaling at 16,384. Its distribution is represented
with fixed 24-bit mass and a one-unit support floor. Conditional bit probability
is obtained from integer cumulative sums over the known byte prefix. The same
learned logistic mixer combines this expert with all retained bit predictors.
No filename, format, language, corpus or ISA information enters prediction.

The versioned frame stores context-bank selection, source length, checksum and
arithmetic payload. Initial qualification passed 36 native/Python byte-identical
frames with Python round trips, covering lengths 0/1/32/512, alphabets 1/7/256,
and bank widths 0/2/4. Paired 64 KiB probes are running. This is exploratory;
there is no corpus result or Silesia rank for this policy. The active CIXT1
Silesia benchmark remains frozen and unaffected.
