# Bounded source reader packet

Commits `025ddfbae` and `174016b3a` add an unintegrated generic reader and
tests only. The reader has no format, selector, filename, or backend policy.

`conservative_allowance(total_read_budget)` returns `(budget - 64 KiB) / 2`.
An integrating caller must use that value for the retained source allocation:
the stack read chunk plus a transient old-and-new Vec reallocation then fit the
declared accounting model. Before every growth the helper checks
`old_capacity + target_capacity <= 2 * allowance`, and after it checks actual
capacity is between required length and allowance. Rust's portable `Vec` API
does not provide a platform RSS guarantee; this is conservative allocator
capacity accounting and must be measured at the integrated call site.

The helper reads once, retries `Interrupted`, propagates other read errors,
uses a stack one-byte overflow probe, never seeks or spools, and does not grow
the retained Vec for the max-plus-one byte. See `test-log.txt` for the raw
local receipt.
