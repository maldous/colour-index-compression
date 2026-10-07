# Context-conditioned fixed-point mixer diagnostic

The experimental CIXQ1 frame includes a context-width selector, source length,
CRC32 and complete existing arithmetic payload. All 21 candidate frames restored
exactly. Mixer weights are selected only by low bits of the preceding decoded
byte; all predictors/count tables remain generic. Learning rate is fixed at 6.
0, 2 and 4 context bits were tested uniformly on four generated inputs and three
4 KiB prerequisite prefixes. These are diagnostics, not corpus scores.

Complete CIX, bounded PPM and framed mixer outputs were compared by physical
size. Mixer wins include: periodic 73 → 49 bytes (global weights), Alice prefix
1770 → 1729, kennedy prefix 1020 → 811, obj2 prefix 1840 → 1751. The latter three
use four weight contexts. Existing CIX retains biased and switching inputs;
bounded PPM wins random. All winning frames carry their decoding selector.

Most of the gain over level-3 CIX comes from enabling the existing mixer at all,
not merely the new weight contexts: global mixer sizes on those three prefixes
are 1752, 819 and 1765. Thus quantify both effects separately. Sixteen contexts
are often worse, so do not assume wider context selection helps. The next useful
step is a larger-block diagnostic and faster exact execution before any broad
mixer benchmark. No canonical source or active Silesia policy was changed.
