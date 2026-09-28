# Optional larger byte-expert learning windows

CIXR6 tests fixed 262,144-byte blocks using Q5 bank widths 0 and 2 plus raw.
It compares its complete framed stream against the existing CIXR5 output and
returns the old bytes unchanged whenever the larger-window stream is not
strictly smaller. Decoder dispatch uses the stored R5/R6 magic. No additional
selector is needed because each representation already identifies itself.

The small qualification is running before the full prerequisite gate. Empty,
one-byte and 3,700-byte periodic cases passed exact decoding, nonregression,
and truncation/trailing-byte rejection. The 262,150-byte random boundary case
is still pending at this checkpoint. No corpus run has been launched for R6.
Existing Silesia encoder policies and sources remain unchanged.

Qualification completed successfully: the 262,150-byte random boundary case
selected R6 at 262,168 physical bytes and passed exact decoding, nonregression
against R5, and damage rejection. All four initial cases passed. The 29-member
prerequisite run has now started locally with three workers. Its outputs are
in results/leaderboard/mixer-ppm-large-tier1; it has no Silesia score yet.
