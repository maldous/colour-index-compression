from pathlib import Path
import pytest
from benchmarks import hutter_wikipedia_units_probe as probe


@pytest.mark.parametrize("mode", probe.MODES)
def test_wrapper_all_modes_same_paid_framing_and_exact_bytes(tmp_path, monkeypatch, mode):
    binary = tmp_path / "paq"; binary.write_bytes(b"pinned-test-backend")
    source = tmp_path / "source"
    data = b"".join(b'<page><text xml:space="preserve">'+(b'Local historical records of the settlement. '*15)+b'[[Town '+str(i).encode()+b']] had '+str(i+1000).encode()+b' people.\n\n</text></page>' for i in range(4))
    source.write_bytes(data)
    def backend(_binary, command):
        inp, out = map(Path, command[-2:])
        if command[0] == "-d": out.write_bytes(inp.read_bytes()[6:])
        else: out.write_bytes(b"paq8px"+inp.read_bytes())
    monkeypatch.setattr(probe, "paq", backend)
    archive, restored = tmp_path / "candidate.cixunits", tmp_path / "restored"
    costs = probe.encode(source, archive, binary, probe.digest(binary), mode)
    source.unlink()
    probe.decode(archive, restored, binary, probe.digest(binary))
    assert restored.read_bytes() == data
    assert costs["total_bytes"] == costs["paq_payload_bytes"] + costs["framing_bytes"] + costs["metadata_bytes"]
    assert costs["metadata_bytes"] == len(probe.METADATA)
