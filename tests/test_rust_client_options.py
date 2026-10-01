from pathlib import Path

from benchmarks.silesia_rust_client import build_command, normalize_profile


BIN = Path("/snapshot/cix")
UNBIN = Path("/snapshot/uncix")
SOURCE = Path("/input/source.bin")
DESTINATION = Path("/output/archive.cix")


def command(profile: str, **overrides: object) -> list[str]:
    return build_command("encode", BIN, UNBIN, SOURCE, DESTINATION, profile, **overrides)


def test_default_profile_measures_the_ordinary_auto_cli_without_strategy_flags():
    actual = command("default")
    assert actual == [str(BIN), "-f", "-o", str(DESTINATION), str(SOURCE)]
    forbidden = {"--fast", "--best", "--format", "--route", "--backend", "--block-size", "--memory", "--threads", "--stream"}
    assert forbidden.isdisjoint(actual)


def test_fast_and_best_add_only_their_effort_request():
    assert command("fast") == [str(BIN), "--fast", "-f", "-o", str(DESTINATION), str(SOURCE)]
    assert command("best") == [str(BIN), "--best", "-f", "-o", str(DESTINATION), str(SOURCE)]


def test_legacy_profile_labels_normalize_to_the_canonical_names():
    assert normalize_profile("current") == "default"
    assert normalize_profile("size") == "best"
    assert command("current") == command("default")
    assert command("size") == command("best")


def test_explicit_expert_controls_are_honored_without_adding_implicit_settings():
    actual = command(
        "default",
        format_name="cixg2",
        threads=3,
        memory="768MiB",
        block_size="1MiB",
        route="predictor",
        backend="huffman",
        stream=True,
    )
    assert actual == [
        str(BIN), "--format", "cixg2", "--route", "predictor", "--backend", "huffman",
        "--block-size", "1MiB", "--memory", "768MiB", "--threads", "3", "--stream",
        "-f", "-o", str(DESTINATION), str(SOURCE),
    ]


def test_decode_ignores_encode_only_effort_and_strategy_overrides():
    actual = build_command(
        "decode", BIN, UNBIN, SOURCE, DESTINATION, "best",
        format_name="cixm6", block_size="64KiB", route="predictor", backend="huffman", threads=4,
    )
    assert actual == [str(UNBIN), "-f", "-o", str(DESTINATION), str(SOURCE)]
