# Fixed PubChem 2-D SDF batch plan

The CID order is identical to the 3-D batch: 1983, 2244, 2519, 3672, 5793,
5950, 681 and 702. Each official PUG-REST 2-D SDF response is retained as raw
bytes, with failures recorded rather than substituted. The completed source is
literal CID-order concatenation, never mixed with the 3-D batch and never
generated from a different coordinate or hydrogen representation.
