from pathlib import Path

from benchmarks import hutter_selfcontained_package as package


def test_entrypoint_absolutizes_paths_before_runtime_chdir():
    text = package.entrypoint_source()
    assert "source, destination = absolute_existing(args.source), absolute_output(args.destination)" in text
    main = text[text.index("def main():"):]
    assert main.index("source, destination") < main.rindex("setup_runtime()")
    assert "paq.chmod" in text
    assert "PYTHONPATH" in text
    assert 'sys.argv = ["benchmarks.competitive_cli", "--help"]' in text
    help_block = main[main.index("if args.help:"):main.index("if not all")]
    assert help_block.index("setup_runtime()") < help_block.index('sys.argv = ["benchmarks.competitive_cli", "--help"]')
    assert 'OMP_NUM_THREADS="1"' in text


def test_spec_is_onefile_explicit_data_plan(tmp_path):
    entrypoint = tmp_path / "entry.py"
    entrypoint.write_text("pass\n")
    source = tmp_path / "runtime" / "cix" / "codec.py"
    source.parent.mkdir(parents=True)
    source.write_text("pass\n")
    binary = tmp_path / "runtime" / "native.so"
    binary.write_bytes(b"\x7fELFfixture")
    spec = package.spec_source(entrypoint, {"runtime/cix/codec.py": source, "runtime/native.so": binary}, ["cix.codec"], [tmp_path / "runtime"])
    assert "datas=" in spec
    assert "hiddenimports=['cix.codec']" in spec
    assert "COLLECT" not in spec
    assert "upx=False" in spec
    assert "binaries=[" in spec and "native.so" in spec
    assert "pathex=[" in spec
    assert "a.zipfiles" not in spec


def test_prepare_defers_build_when_full_run_is_not_verified(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    freeze = tmp_path / "freeze.json"
    freeze.write_text('{"source_commit":"x","runtime_files":{}}')
    imports = tmp_path / "imports.json"
    imports.write_text('{"local_python_modules":[],"non_stdlib_import_roots":[]}')
    try:
        package.prepare(runtime=runtime, freeze_manifest=freeze, static_imports=imports, vendor_root=tmp_path,
                        paq_roots=[], run=tmp_path / "pending", output=tmp_path / "out")
    except ValueError as exc:
        assert "pending" in str(exc)
    else:
        raise AssertionError("unverified full run must fail closed")
