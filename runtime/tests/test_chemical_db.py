import datetime

from runtime.cix_runtime.legacy import chemical_db
from runtime.cix_runtime.legacy import mysql_fixed_columns as fixed
from runtime.cix_runtime.legacy import mysql_record_constraints as records
from runtime.cix_runtime.legacy import sdf_geometry as geometry


def _sdf() -> bytes:
    counts = b"  1  0  0  0  0  0            999 V2000\n"
    atom = b"    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n"
    return b"CIX\n  runtime\n\n" + counts + atom + b"M  END\n$$$$\n"


def _record(seed: int) -> bytes:
    date = datetime.date(2020, 1, 1 + seed).toordinal().to_bytes(4, "little")
    row = [
        (seed + 1).to_bytes(4, "little"), (seed + 10).to_bytes(4, "little"),
        seed.to_bytes(4, "little"), (seed * 100).to_bytes(4, "little"),
        b"\0\0\0\0\x031.0", date, b"CODE".ljust(10), b"name".ljust(20), b"address".ljust(80),
    ]
    return records.wrap(records.join_fields(row))


def test_geometry_transform_is_exact_and_catalogued():
    source = _sdf()
    transformed, _ = geometry.encode(source, 2, 2)
    assert geometry.decode(transformed) == source
    candidates, evidence = chemical_db.catalog(source)
    assert {candidate.id for candidate in candidates} >= {
        "bonded-coordinate-palette-paq-v215-8", "chemical-hydrogen-paq-v215-8",
    }
    assert evidence[0]["recognizer"].startswith("sdf-v2000-marker")


def test_database_remaining_counts_and_fixed_columns_are_exact():
    source = b"".join(_record(index) for index in range(4))
    for mode in range(5):
        transformed, _ = records.transform(source, mode)
        assert records.inverse(transformed) == source
    transformed, _ = fixed.transform(source, 1)
    assert fixed.inverse(transformed) == source
    candidates, evidence = chemical_db.catalog(source)
    assert "database-remaining-count-paq-v215-8" in {candidate.id for candidate in candidates}
    assert any(row["family"] == "database" for row in evidence)


def test_malformed_input_has_no_legacy_admission_or_decode_fallback():
    candidates, evidence = chemical_db.catalog(b"not an sdf or myisam record")
    assert not candidates
    assert not evidence
    # Dispatch recognition identifies an archive family, not its validity.
    assert chemical_db.recognizes_frame(b"CIXG\x01\x80")
    try:
        chemical_db.decode_geometry(b"CIXG\x01\x80", 1024, 5_000_000_000)
    except ValueError:
        pass
    else:
        raise AssertionError("truncated known-family archive was accepted")
    for decoder in chemical_db.DECODERS.values():
        try:
            decoder(b"truncated", 1024, 1024)
        except ValueError:
            pass
        else:
            raise AssertionError("malformed specialist frame was accepted")
