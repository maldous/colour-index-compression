# Molecular forward-transfer plan

This is a separate domain-transfer check for the existing SDF geometry and
hydrogen-slot mechanism.  It does not reuse NCI/Silesia bytes and does not run
PAQ.  The fixed proposed asset is PubChem CID 2519 (caffeine), fetched as the
official PUG-REST 3-D SDF response without reformatting:

`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2519/record/SDF/?record_type=3d`

The adapter must be self-contained, retain unsupported records literally, and
charge every flag, skeleton, candidate-choice, coordinate residual, length and
framing byte.  A future matched PAQ comparison must give original and adapter
the same fixed backend and account for the complete adapter frame.  This plan
does not authorize that execution.
