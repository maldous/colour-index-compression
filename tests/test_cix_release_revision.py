import unittest

from benchmarks.cix_rust_perf_audit import release_revision


class ReleaseRevisionTests(unittest.TestCase):
    def test_both_schemas(self):
        revision = "a" * 40
        for value in ({"source_revision": revision},
                      {"source": {"revision": revision}},
                      {"source_revision": revision, "source": {"revision": revision}}):
            with self.subTest(value=value):
                self.assertEqual(release_revision(value), revision)

    def test_missing_invalid_and_conflicting(self):
        for value in ({}, {"source": []}, {"source_revision": "short"},
                      {"source_revision": False}, {"source_revision": "g" * 40},
                      {"source_revision": "a" * 40, "source": {"revision": "b" * 40}}):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                release_revision(value)


if __name__ == "__main__":
    unittest.main()
