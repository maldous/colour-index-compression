# ZPAQ instruction-watchdog checkpoint

The CIX-owned wrapper previously decremented its unsigned instruction budget even when it was zero. The caller stopped on the resulting false return, but another charge could then use the wrapped counter. It now checks zero first, keeping exhaustion stable until output progress resets the budget.

`jobs/zpaq-watchdog-v2` compiled the original wrapper and the corrected wrapper against the same unchanged pinned libzpaq interpreter. The original failed the specific repeated-exhaustion assertion. The corrected version passed one million admitted charges, repeated rejection, progress reset, cancellation polling at the existing cadence, an exact 8 KiB round trip and trailing-byte rejection. The private contract includes the wrapper directly; it adds no public ABI. Compiler settings retain NOJIT and the product's optimization/aliasing policy.

The earlier v1 attempt failed at compilation because warnings from an unchanged external header were treated as owned-source errors. Its evidence is preserved. The v2 owned contract keeps warnings as errors while classifying the libzpaq header search as external system headers; upstream source is untouched and its separately reported analysis findings remain open.

This establishes the wrapper correction. A current whole-product optimized build and final source analysis remain required. No archive-size or throughput improvement is claimed.
