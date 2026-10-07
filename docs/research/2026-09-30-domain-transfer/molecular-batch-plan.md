# Fixed PubChem 3-D SDF batch plan

The predeclared CID order is: 1983, 2244, 2519, 3672, 5793, 5950, 681 and 702.
Each CID uses the official PUG-REST `record/SDF/?record_type=3d` response. Every
successful response is retained as received; an unavailable CID is recorded as
unavailable rather than replaced. Successful files are concatenated in that
declared order without SDF reserialization, filtering or artificial hydrogen
generation. The batch is small transfer evidence, not a representative domain
benchmark. No PAQ execution is authorized by this plan.
