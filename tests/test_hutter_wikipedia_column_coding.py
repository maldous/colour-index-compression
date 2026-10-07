from benchmarks.hutter_wikipedia_column_coding import decode, encode


def test_all_modes_round_trip_and_paid_modes_share_counts():
    values = [b"title", b"id", b"title", b"date", b"title", b"id"]
    rows = {}
    for mode in ("raw", "remaining", "rank"):
        blob, stats = encode(values, mode); assert decode(blob, len(values)) == values; rows[mode] = stats
        assert sum(stats[key] for key in ("literal_payload_bytes", "palette_bytes", "count_bytes", "order_bytes", "framing_bytes")) == len(blob)
    assert rows["remaining"]["palette_bytes"] == rows["rank"]["palette_bytes"]
    assert rows["remaining"]["count_bytes"] == rows["rank"]["count_bytes"]
    assert rows["remaining"]["order_bytes"] != 0 and rows["rank"]["order_bytes"] != 0
    assert rows["remaining"]["order_kind"] == 2


def test_guards_fall_back_to_self_describing_raw():
    values = [i.to_bytes(2, "big") for i in range(257)]
    blob, stats = encode(values, "remaining")
    assert stats["actual_mode"] == "raw" and stats["fallback_reason"] == "too_many_distinct"
    assert decode(blob, 257) == values
    blob, stats = encode([b"x"] * 3, "rank")
    assert stats["actual_mode"] == "raw" and decode(blob, 3) == [b"x"] * 3


def test_rejects_bad_length_and_trailing_bytes():
    blob, _ = encode([b"a"] * 4, "remaining")
    try: decode(blob, 3)
    except ValueError as error: assert "length" in str(error)
    else: assert False
    try: decode(blob + b"x", 4)
    except ValueError as error: assert "trailing" in str(error)
    else: assert False
