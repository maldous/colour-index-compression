"""Pure archive/member fixtures for the v3 target preservation recipe."""
import hashlib
import importlib.util
import os
from pathlib import Path
import resource
import sys
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("preserve_v3_target", Path(__file__).with_name("run.py"))
preserve = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preserve
SPEC.loader.exec_module(preserve)


class PreserveV3TargetTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        work = Path(temporary.name) / "work"
        target = work / "native-final-source-v3/target"
        target.mkdir(parents=True)
        preserved = work / "native-final-source-v3/preserved-target-v1"
        return temporary, work, target, preserved

    def test_xz_round_trip_preserves_top_binary_deps_hardlink_and_symlink(self):
        temporary, work, target, preserved = self.fixture()
        self.addCleanup(temporary.cleanup)
        top = target / "release-lto/cix"
        top.parent.mkdir(parents=True)
        top.write_bytes(b"archive fixture")
        dependency = target / "release-lto/deps/cix-fixture"
        dependency.parent.mkdir(parents=True)
        os.link(top, dependency)
        (target / "alias").symlink_to("release-lto/cix")
        archive = preserved / "target.tar.xz"
        manifest_file = preserved / "target.manifest.json"
        old_limit = resource.getrlimit(resource.RLIMIT_FSIZE)
        with patch.multiple(preserve, WORK=work, TARGET=target, PRESERVED=preserved,
                            ARCHIVE=archive, MANIFEST=manifest_file, ARCHIVE_CAP=1_000_000,
                            RETAINED_BINARIES={"release-lto/cix": hashlib.sha256(b"archive fixture").hexdigest()}):
            manifest, links = preserve.collect_manifest()
            preserved.mkdir()
            preserve.write_archive(manifest, links)
            digest = preserve.verify_archive(manifest)
        self.assertTrue(archive.is_file())
        self.assertEqual(len(digest), 64)
        self.assertEqual(resource.getrlimit(resource.RLIMIT_FSIZE), old_limit)

    def test_receipt_bound_binaries_are_copied_and_verified_separately(self):
        temporary, work, target, preserved = self.fixture()
        self.addCleanup(temporary.cleanup)
        binaries = {}
        for name in ("cix", "cixcat", "uncix"):
            source = target / "release-lto" / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(name.encode())
            binaries["release-lto/" + name] = hashlib.sha256(name.encode()).hexdigest()
        with patch.multiple(preserve, WORK=work, TARGET=target, PRESERVED=preserved,
                            RETAINED_BINARIES=binaries):
            manifest, _ = preserve.collect_manifest()
            preserved.mkdir()
            copied = preserve.copy_and_verify_binaries(manifest)
        self.assertEqual(set(copied), set(binaries))
        self.assertTrue(all(Path(item["preserved_path"]).is_file() for item in copied.values()))

    def test_terminal_job_raw_and_in_work_phase_receipts_are_required(self):
        temporary, work, target, preserved = self.fixture()
        self.addCleanup(temporary.cleanup)
        required = ("copy-retained-lto-cache", "clippy", "release-lto-binaries",
                    "test-cli-program-aliases", "test-cli_smoke",
                    "test-full_engine_constraints", "test-zpaq_backend")
        binaries = {"release-lto/cix": "a", "release-lto/cixcat": "b", "release-lto/uncix": "c"}
        phases = {name: {"returncode": 0} for name in required}
        job = work / "job.json"
        work_receipt = work / "v3/receipt.json"
        raw = work / "raw.json"
        alias = work / "alias.json"
        alias_stdout = work / "alias.stdout"
        work_receipt.parent.mkdir(parents=True)
        job.write_text(__import__("json").dumps({"schema": "cix-native-final-source-v3", "status": "pass", "phases": phases,
                                                   "release_lto_binaries": {Path(key).name: {"sha256": value} for key, value in binaries.items()}}))
        work_receipt.write_text(__import__("json").dumps({"schema": "cix-native-final-source-v3", "status": "running", "phases": phases}))
        raw.write_text(__import__("json").dumps({"exit_code": 0, "child_status": {"child_exit_code": 0}}))
        alias.write_text(__import__("json").dumps({"status": "pass", "exit_code": 0, "test": preserve.ALIAS_TEST}))
        alias_stdout.write_text("running 1 test\ntest " + preserve.ALIAS_TEST + " ... ok\n1 passed; 0 failed\n")
        with patch.multiple(preserve, V3_JOB_RECEIPT=job, V3_WORK_RECEIPT=work_receipt,
                            V3_RAW_RESULT=raw, ALIAS_RECEIPT=alias, ALIAS_STDOUT=alias_stdout,
                            RETAINED_BINARIES=binaries):
            evidence = preserve.terminal_quality_gates()
        self.assertEqual(set(evidence), {"v3_job_receipt", "v3_work_phase_receipt", "v3_outer_raw_result", "alias_receipt", "alias_stdout"})


if __name__ == "__main__":
    unittest.main()
