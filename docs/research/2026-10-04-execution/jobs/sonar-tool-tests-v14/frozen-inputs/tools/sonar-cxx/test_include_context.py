import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("include_context", Path(__file__).with_name("include_context.py"))
context = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = context
SPEC.loader.exec_module(context)


class IncludeContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.unit = self.source / "unit.c"
        self.unit.write_text("int value;\n")
        self.build = self.root / "kernel-build"
        self.build.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_rebases_relative_symlinked_include_and_forced_file(self):
        sibling = self.root / "headers-common"; (sibling / "uapi").mkdir(parents=True)
        target = self.build / "arch"; target.mkdir()
        (target / "uapi").symlink_to(sibling / "uapi", target_is_directory=True)
        include = self.build / "include"; include.mkdir()
        forced = include / "config.h"; forced.write_text("#define RECORDED 1\n")
        row = {"file": str(self.unit), "directory": str(self.build),
               "arguments": ["cc", "-I./arch/uapi", "-include", "./include/config.h", "-c", str(self.unit)]}
        mapped, mounts, evidence = context.rebase_include_context([row], self.source)
        destination = dict(mounts)[sibling / "uapi"]
        self.assertEqual(mapped[0]["arguments"][1], "-I" + destination)
        forced_entry = next(item for item in evidence if item["flag"] == "-include")
        self.assertEqual(forced_entry["disposition"], "resolved-forced-file")
        self.assertTrue(forced_entry["mapped"].endswith("/config.h"))

    def test_records_absent_include_without_inventing_a_mount(self):
        row = {"file": str(self.unit), "directory": str(self.build),
               "arguments": ["cc", "-iquote", "missing", "-c", str(self.unit)]}
        mapped, mounts, evidence = context.rebase_include_context([row], self.source)
        self.assertEqual(mapped[0]["arguments"][2], "missing")
        self.assertEqual(evidence[0]["disposition"], "absent-ignored-include-directory")
        self.assertIsNone(evidence[0]["mapped"])

    def test_distinguishes_source_inside_from_external_sibling_and_maps_source_operand(self):
        sibling = self.root / "sibling"; sibling.mkdir()
        header = sibling / "header.h"; header.write_text("#define H 1\n")
        relative_unit = "../source/unit.c"
        row = {"file": str(self.unit), "directory": str(self.build),
               "arguments": ["cc", "-I", str(sibling), "-c", str(relative_unit), "-o", str(self.build / "out.o")]}
        mapped, mounts, _ = context.rebase_include_context([row], self.source)
        sibling_destination = dict(mounts)[sibling]
        self.assertEqual(mapped[0]["file"], "/usr/src/unit.c")
        self.assertEqual(mapped[0]["arguments"][4], "/usr/src/unit.c")
        self.assertEqual(mapped[0]["arguments"][2], sibling_destination)
        self.assertTrue(mapped[0]["arguments"][6].startswith("/cix-external/"))

    def test_rejects_absent_forced_file_and_unresolved_sysroot_spelling(self):
        missing = {"file": str(self.unit), "directory": str(self.build),
                   "arguments": ["cc", "-include", "missing.h", "-c", str(self.unit)]}
        with self.assertRaises(context.IncludeContextError):
            context.rebase_include_context([missing], self.source)
        sysroot = {"file": str(self.unit), "directory": str(self.build),
                   "arguments": ["cc", "--sysroot=$SYSROOT", "-c", str(self.unit)]}
        with self.assertRaises(context.IncludeContextError):
            context.rebase_include_context([sysroot], self.source)

    def test_resolves_bare_forced_file_through_a_recorded_include_directory(self):
        headers = self.root / "headers"; headers.mkdir()
        forced = headers / "recorded.h"; forced.write_text("#define RECORDED 1\n")
        row = {"file": str(self.unit), "directory": str(self.build),
               "arguments": ["cc", "-I", str(headers), "-include", "recorded.h", "-c", str(self.unit)]}
        mapped, mounts, evidence = context.rebase_include_context([row], self.source)
        entry = next(item for item in evidence if item["flag"] == "-include")
        self.assertEqual(entry["disposition"], "resolved-forced-file-via-recorded-include-search")
        self.assertEqual(entry["mapped"], dict(mounts)[headers] + "/recorded.h")
        self.assertEqual(mapped[0]["arguments"][4], entry["mapped"])

    def test_keeps_paired_macro_values_opaque_while_mapping_absolute_output(self):
        row = {"file": str(self.unit), "directory": str(self.build),
               "arguments": ["cc", "-D", "ORIGIN=$ORIGIN", "-c", str(self.unit), "-o", str(self.build / "out.o")]}
        mapped, _, _ = context.rebase_include_context([row], self.source)
        self.assertEqual(mapped[0]["arguments"][2], "ORIGIN=$ORIGIN")
        self.assertTrue(mapped[0]["arguments"][6].startswith("/cix-external/"))

    def test_handles_joined_and_two_token_directory_file_and_sysroot_operands(self):
        inc = self.root / "inc"; inc.mkdir()
        after = self.root / "after"; after.mkdir()
        macros = self.root / "forced" / "macros.h"; macros.parent.mkdir(); macros.write_text("#define X 1\n")
        sysroot = self.root / "sysroot"; sysroot.mkdir()
        row = {"file": str(self.unit), "directory": str(self.build), "arguments": [
            "cc", "-I" + str(inc), "-isystem", str(inc), "-idirafter" + str(after),
            "-imacros" + str(macros), "--sysroot=" + str(sysroot), "-c", str(self.unit)]}
        mapped, mounts, evidence = context.rebase_include_context([row], self.source)
        self.assertEqual(len([item for item in evidence if item["mapped"]]), 5)
        self.assertTrue(mapped[0]["arguments"][1].startswith("-I/cix-external/"))
        self.assertTrue(mapped[0]["arguments"][6].startswith("--sysroot=/cix-external/"))
        self.assertTrue(all(host.is_dir() for host, _ in mounts))


if __name__ == "__main__":
    unittest.main()
