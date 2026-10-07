"""Pure fixture checks for the preservation selection guards; not a job dispatch."""
import importlib.util
from pathlib import Path
import os
import resource
import sys
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("preserve_debug_cache", Path(__file__).with_name("run.py"))
preserve = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preserve
SPEC.loader.exec_module(preserve)


class PreserveDebugCacheGuardTests(unittest.TestCase):
    def test_job_script_derives_the_exact_repository_root(self):
        self.assertEqual(
            preserve.ROOT,
            Path("/home/user/src/colour-index-compression"),
        )

    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        work = Path(temporary.name) / "work"
        target = work / "target/debug"
        target.mkdir(parents=True)
        return temporary, work, target

    def test_accepts_internal_hardlinks_only(self):
        temporary, work, target = self.fixture()
        self.addCleanup(temporary.cleanup)
        (target / "first").write_bytes(b"same")
        os.link(target / "first", target / "second")
        with patch.object(preserve, "WORK", work), patch.object(preserve, "TARGET", target):
            manifest, _ = preserve.collect_manifest()
        regular = [row for row in manifest["entries"] if row["type"] == "file"]
        self.assertEqual(len(regular), 2)
        self.assertEqual({row["link_count"] for row in regular}, {2})

    def test_rejects_hardlink_elsewhere_in_work(self):
        temporary, work, target = self.fixture()
        self.addCleanup(temporary.cleanup)
        (target / "selected").write_bytes(b"selected")
        outside = work / "installed/provider-copy"
        outside.parent.mkdir(parents=True)
        os.link(target / "selected", outside)
        with patch.object(preserve, "WORK", work), patch.object(preserve, "TARGET", target):
            with self.assertRaisesRegex(RuntimeError, "linked elsewhere in work"):
                preserve.collect_manifest()

    def test_rejects_hardlink_outside_work_by_target_link_count(self):
        temporary, work, target = self.fixture()
        self.addCleanup(temporary.cleanup)
        selected = target / "selected"
        selected.write_bytes(b"selected")
        os.link(selected, Path(temporary.name) / "outside-work-copy")
        with patch.object(preserve, "WORK", work), patch.object(preserve, "TARGET", target):
            with self.assertRaisesRegex(RuntimeError, "external hardlink"):
                preserve.collect_manifest()

    def test_rejects_symlink_escape(self):
        temporary, work, target = self.fixture()
        self.addCleanup(temporary.cleanup)
        (target / "outside").symlink_to("../../outside")
        with patch.object(preserve, "WORK", work), patch.object(preserve, "TARGET", target):
            with self.assertRaisesRegex(RuntimeError, "symlink escapes"):
                preserve.collect_manifest()

    def test_archives_and_reopens_file_hardlink_and_safe_symlink(self):
        temporary, work, target = self.fixture()
        self.addCleanup(temporary.cleanup)
        first = target / "first"
        first.write_bytes(b"archive fixture")
        os.link(first, target / "second")
        (target / "alias").symlink_to("first")
        preserved = work / "preserved"
        archive = preserved / "target-debug.tar.gz"
        manifest_file = preserved / "target-debug.manifest.json"
        old_limit = resource.getrlimit(resource.RLIMIT_FSIZE)
        with patch.multiple(
            preserve,
            WORK=work,
            TARGET=target,
            PRESERVED=preserved,
            ARCHIVE=archive,
            MANIFEST=manifest_file,
            ARCHIVE_CAP=1024 * 1024,
        ):
            manifest, links = preserve.collect_manifest()
            preserved.mkdir()
            preserve.write_archive(manifest, links)
            digest = preserve.verify_archive(manifest)
        self.assertTrue(archive.is_file())
        self.assertEqual(len(digest), 64)
        self.assertEqual(resource.getrlimit(resource.RLIMIT_FSIZE), old_limit)


if __name__ == "__main__":
    unittest.main()
