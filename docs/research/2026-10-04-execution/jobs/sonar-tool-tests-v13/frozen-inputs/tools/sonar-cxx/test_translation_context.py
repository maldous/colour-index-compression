import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("translation_context", Path(__file__).with_name("translation_context.py"))
context = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = context
SPEC.loader.exec_module(context)


class TranslationContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.inputs = {}

    def tearDown(self):
        self.temp.cleanup()

    def file(self, relative, content="input"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        self.inputs[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    def row(self, relative, arguments, directory=None):
        source = self.file(relative, "int bridge;\n")
        return {"file": str(source), "directory": str(directory or self.root), "arguments": arguments(str(source))}

    def test_all_six_reviewed_contexts_admit_only_with_bound_inputs(self):
        root = self.root
        macro = self.file("qualified/overlay-source.c")
        include_a = self.file("kernel/include/a.h")
        include_b = self.file("kernel/include/b.h")
        include_c = self.file("kernel/include/c.h")
        records = [
            self.row("rust/cix-native/adapters/gstreamer/src/gstcixstream.c", lambda s: ["cc", "-c", s]),
            self.row("rust/cix-native/adapters/blosc2/src/cix_blosc2_adapter.c", lambda s: ["cc", "-c", s]),
            self.row("rust/cix-native/adapters/squashfs/kernel/cix_profile_portable.c", lambda s: ["gcc-13", "-nostdinc", "-D__KERNEL__", "-include", str(include_a), "-include", str(include_b), "-include", str(include_c), "-DCIX_PORTABLE_PROFILE_SOURCE=\"" + str(macro) + "\"", "-c", s]),
            self.row("rust/cix-native/adapters/squashfs/userspace/squashfuse/cix_squashfuse_decode.c", lambda s: ["gcc", "-DCIX_SQUASHFUSE_DECOMPRESS_SOURCE=\"" + str(macro) + "\"", "-c", s]),
            self.row("rust/cix-native/adapters/squashfs/userspace/libsquashfs/cix_sqfsng_compressor.c", lambda s: ["cc", "-DCIX_SQFSNG_COMPRESSOR_SOURCE=\"" + str(macro) + "\"", "-c", s]),
            self.row("rust/cix-native/adapters/squashfs/userspace/libsquashfs/cix_sqfsng_read_super.c", lambda s: ["cc", "-DCIX_SQFSNG_READ_SUPER_SOURCE=\"" + str(macro) + "\"", "-c", s]),
        ]
        for record in records:
            received = context.validate_translation_context(record, root, self.inputs)
            self.assertIn(received.relative_source, context.PROJECTABLE_RELATIVES)

    def test_sqfsng_double_slash_source_matches_by_identity_without_rewriting_argv(self):
        macro = self.file("qualified/compressor.c")
        source = self.file("rust/cix-native/adapters/squashfs/userspace/libsquashfs/cix_sqfsng_compressor.c")
        doubled = str(source.parent) + "//" + source.name
        record = {"file": str(source), "directory": str(self.root), "arguments": ["/usr/bin/cc", "-DCIX_SQFSNG_COMPRESSOR_SOURCE=\"" + str(macro) + "\"", "-c", doubled]}
        received = context.validate_translation_context(record, self.root, self.inputs)
        self.assertEqual(received.source_operand.recorded_path, doubled)
        self.assertEqual(received.source_operand.resolved_path, str(source.resolve()))
        self.assertEqual(record["arguments"][-1], doubled)

    def test_rejects_unreviewed_source_and_unbound_or_tampered_inputs(self):
        other = self.row("rust/cix-native/adapters/other.c", lambda s: ["cc", "-c", s])
        with self.assertRaises(context.TranslationContextError):
            context.validate_translation_context(other, self.root, self.inputs)
        macro = self.file("qualified/source.c")
        record = self.row("rust/cix-native/adapters/squashfs/userspace/squashfuse/cix_squashfuse_decode.c", lambda s: ["gcc", "-DCIX_SQUASHFUSE_DECOMPRESS_SOURCE=\"" + str(macro) + "\"", "-c", s])
        with self.assertRaises(context.TranslationContextError):
            context.validate_translation_context(record, self.root, {})
        macro.write_text("changed")
        with self.assertRaises(context.TranslationContextError):
            context.validate_translation_context(record, self.root, self.inputs)

    def test_kernel_requires_recorded_forced_headers_and_kernel_flags(self):
        macro = self.file("qualified/profile.c")
        record = self.row("rust/cix-native/adapters/squashfs/kernel/cix_profile_portable.c", lambda s: ["gcc-13", "-DCIX_PORTABLE_PROFILE_SOURCE=\"" + str(macro) + "\"", "-c", s])
        with self.assertRaises(context.TranslationContextError):
            context.validate_translation_context(record, self.root, self.inputs)

    def test_loads_only_historically_recorded_reader_macro_digest(self):
        work = self.root / "benchmark-work/native-rc-check-v1/squashfs-readers-v3"
        macro = self.file("benchmark-work/native-rc-check-v1/squashfs-readers-v3/sqfsng-src/lib/sqfs/read_super.c", "upstream")
        source = self.file("rust/cix-native/adapters/squashfs/userspace/libsquashfs/cix_sqfsng_read_super.c")
        argument = "-DCIX_SQFSNG_READ_SUPER_SOURCE=\"" + str(macro) + "\""
        record = {"file": str(source), "directory": str(self.root), "arguments": ["cc", argument, "-c", str(source)]}
        manifest = work / "pinned-source-before.sha256.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"sqfsng": {"lib/sqfs/read_super.c": self.inputs[str(macro.resolve())]}}))
        receipt = self.root / "benchmark-work/native-rc-check-v1/compiler-capture-host-v3/receipt.json"
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps({"commands": [{"returncode": 0}], "compiler_invocations": [{"argv": [argument]}]}))
        loaded = context.load_recorded_inputs(self.root, record)
        self.assertEqual(loaded.gaps, ())
        self.assertEqual(loaded.qualified_inputs[str(macro.resolve())], self.inputs[str(macro.resolve())])
        self.assertIsNotNone(loaded.receipt_sha256)
        self.assertIsNotNone(loaded.manifest_sha256)

    def test_kernel_loader_reports_gap_without_hashing_current_stage_or_headers(self):
        macro = self.file("benchmark-work/native-rc-check-v1/kernel-module-v4/stage/profile/src/cix_squashfs_profile.c")
        source = self.file("rust/cix-native/adapters/squashfs/kernel/cix_profile_portable.c")
        record = {"file": str(source), "directory": str(self.root), "arguments": ["gcc-13", "-DCIX_PORTABLE_PROFILE_SOURCE=\"" + str(macro) + "\"", "-c", str(source)]}
        loaded = context.load_recorded_inputs(self.root, record)
        self.assertEqual(loaded.qualified_inputs, {})
        self.assertEqual(len(loaded.gaps), 2)

    def test_preprocess_command_suppresses_only_recorded_wp_dependency_output(self):
        record = {"arguments": ["gcc-13", "-Wp,-MMD,/old/unit.o.d", "-DVALUE=1", "-c", "/work/unit.c", "-o", "/old/unit.o"]}
        command = context.preprocess_command(record, Path("/evidence/unit.i"))
        self.assertEqual(command.argv, ("gcc-13", "-DVALUE=1", "/work/unit.c", "-E", "-o", "/evidence/unit.i"))
        self.assertEqual(command.removed_dependency_outputs, ("-Wp,-MMD,/old/unit.o.d",))


if __name__ == "__main__":
    unittest.main()
