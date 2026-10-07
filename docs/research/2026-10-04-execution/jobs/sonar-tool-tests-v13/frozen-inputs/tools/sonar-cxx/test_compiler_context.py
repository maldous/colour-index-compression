import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location("compiler_context", Path(__file__).with_name("compiler_context.py"))
context = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(context)


class CompilerContextTests(unittest.TestCase):
    def record(self, arguments):
        return {"arguments": arguments, "directory": "/work", "file": "/work/bridge.cpp"}

    def test_prepares_empty_input_and_preserves_semantic_flags(self):
        argv, receipt = context.prepare_argv(self.record([
            "/usr/bin/c++", "-DNAME=\"quoted value\"", "-UOLD", "-I", "/sdk/include",
            "-isystem", "/system/include", "-std=c++20", "-mavx2", "-include", "/work/config.h",
            "-c", "/work/bridge.cpp", "-o", "/tmp/bridge.o", "-MF", "/tmp/bridge.d", "-MD",
        ]))
        self.assertEqual(argv[-5:], ["-x", "c++", "-E", "-dM", "-v", "-"][-5:])
        self.assertIn('-DNAME="quoted value"', argv)
        self.assertIn("-include", argv)
        self.assertNotIn("/work/bridge.cpp", argv)
        self.assertNotIn("/tmp/bridge.o", argv)
        self.assertTrue(receipt["empty_input"])

    def test_rejects_wrapper_and_ambiguous_source(self):
        with self.assertRaises(context.CompilerContextError):
            context.prepare_argv(self.record(["ccache", "c++", "-c", "/work/bridge.cpp"]))
        with self.assertRaises(context.CompilerContextError):
            context.prepare_argv(self.record(["c++", "-c", "/work/bridge.cpp", "/work/bridge.cpp"]))

    def test_preserves_c_language_and_rejects_extra_tu_or_side_effects(self):
        record = {"arguments": ["cc", "-std", "c11", "-c", "/work/filter.c", "-o", "/tmp/filter.o"],
                  "directory": "/work", "file": "/work/filter.c"}
        argv, receipt = context.prepare_argv(record)
        self.assertIn("c", argv)
        self.assertEqual(receipt["language"], "c")
        for flag in ("-save-temps=obj", "-ftime-trace=file", "-Wp,-MD", "-fplugin=/tmp/p", "-Xclang"):
            with self.assertRaises(context.CompilerContextError):
                context.prepare_argv(self.record(["c++", "-c", "/work/bridge.cpp", flag]))
        with self.assertRaises(context.CompilerContextError):
            context.prepare_argv(self.record(["c++", "-c", "/work/bridge.cpp", "other.cpp"]))

    def test_parser_preserves_raw_cplusplus_and_does_not_forge_header_guards(self):
        parsed = context.parse_compiler_output(
            "#define __cplusplus 202002L\n#define FEATURE(x) (x + 1)\n",
            "#include <...> search starts here:\n /sdk/include\n /usr/include (framework directory)\nEnd of search list.\n",
        )
        self.assertEqual(parsed["macros"][0]["raw"], "#define __cplusplus 202002L")
        self.assertEqual(parsed["system_include_paths"], ["/sdk/include", "/usr/include"])
        self.assertTrue(parsed["does_not_infer_header_guard_macros"])


if __name__ == "__main__":
    unittest.main()
