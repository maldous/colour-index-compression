# ECOFF relation parity fixture

`generate_ecoff_relation_fixture.py` builds a 1,200-byte synthetic Alpha ECOFF
object from explicit offsets. It contains a relocation-backed pointer for the
active `ECRD1` mode-5 route, a relocation-backed section pointer, two repeated
`.text` symbol names for mode-2 frequency ranking, a GP-relative dynamic-GOT
load, and one `.pdata` entry. It invokes only reference raw
transforms, asserts their event counters are nonzero, verifies each inverse,
and writes exact hex vectors for native tests. It does not invoke compression.

Root schedules generation with:

```sh
PYTHONPATH=runtime python3 docs/research/2026-10-04-native-rc/address-completion/generate_ecoff_relation_fixture.py --output docs/research/2026-10-04-native-rc/address-completion/ecoff-relation-v1.json
```
