import hashlib
import importlib.util
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


if __name__ == "__main__":
    unittest.main()
