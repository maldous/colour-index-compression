"""Control-flow tests with tiny fake commands; no compression quality evidence."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("confirmation_fixture", HERE / "confirm.py")
confirm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(confirm)

FAKE_CLI = '''#!/usr/bin/python3
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--fast',action='store_true');p.add_argument('--best',action='store_true')
p.add_argument('--threads');p.add_argument('--memory');p.add_argument('--max-output',type=int)
p.add_argument('--report');p.add_argument('-f',action='store_true');p.add_argument('-o',required=True)
p.add_argument('source');a=p.parse_args();data=Path(a.source).read_bytes()
if a.max_output is not None and len(data)>a.max_output:raise SystemExit(2)
Path(a.o).write_bytes(data)
if a.report:Path(a.report).write_text(json.dumps({'status':'completed','selected':'fixture-copy','trials':[]}))
'''
FAKE_SCHEDULER = '''import json,os,subprocess,sys
s=json.load(open(sys.argv[1]));env=os.environ.copy()
env.update(x.split('=',1) for x in s.get('env',[]))
raise SystemExit(subprocess.run(s['command'],env=env).returncode)
'''


def fixture(root: Path) -> argparse.Namespace:
    stage = root / "stage"
    stage.mkdir()
    for name in ("cix", "uncix"):
        path = stage / name
        path.write_text(FAKE_CLI)
        path.chmod(0o755)
    source_export = root / "source-export"
    source_export.mkdir()
    (source_export / "source.txt").write_text("fixture source only")
    policy, references = root / "policy.json", root / "references.json"
    policy.write_text('{"fixture_only":true}')
    references.write_text('{"fixture_only":true}')
    inputs = root / "inputs"
    inputs.mkdir()
    for number, name in enumerate(confirm.MEMBERS):
        (inputs / name).write_bytes(bytes([number]) + b"fixture bytes")
    scheduler = root / "schedule.py"
    scheduler.write_text(FAKE_SCHEDULER)
    return argparse.Namespace(area=root / "run", cix=stage / "cix", uncix=stage / "uncix",
        policy=policy, references=references, source_export=source_export, stage_root=stage,
        silesia=inputs, schedule=scheduler)


class ConfirmationHarnessFixture(unittest.TestCase):
    def test_complete_pass_resume_and_mutation_detection(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = fixture(Path(temporary))
            confirm.prepare(args)
            confirm.run(args)
            summary = confirm.read(args.area / "summary.json")
            self.assertEqual(summary["verified_cells"], 36)
            for total in summary["totals"].values():
                self.assertEqual(total["verified_cells"], 12)
                self.assertEqual(total["archive_percent_of_source"], 100)
                self.assertGreater(total["encode_wall_seconds"], 0)
                self.assertGreater(total["decode_kernel_memory_peak_bytes_max"], 0)
            result_paths = sorted((args.area / "results").glob("*/result.json"))
            original = {path: path.stat().st_mtime_ns for path in result_paths}
            confirm.run(args)
            self.assertEqual(original, {path: path.stat().st_mtime_ns for path in result_paths})
            args.cix.write_text(FAKE_CLI + "\n# changed\n")
            with self.assertRaisesRegex(RuntimeError, "frozen"):
                confirm.run(args)

    def test_started_and_failed_cells_cannot_retry_implicitly(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = fixture(Path(temporary))
            confirm.prepare(args)
            (args.silesia / confirm.MEMBERS[0]).write_bytes(b"changed source")
            with self.assertRaisesRegex(RuntimeError, "frozen"):
                confirm.run(args)
            with self.assertRaisesRegex(RuntimeError, "no implicit retry"):
                confirm.run(args)
            state = args.area / "results" / "confirm-fast-dickens" / "state.json"
            self.assertEqual(json.loads(state.read_text())["status"], "FAILED")

    def test_scheduler_mutation_and_incomplete_plan_fail_before_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = fixture(Path(temporary))
            confirm.prepare(args)
            original = args.schedule.read_text()
            args.schedule.write_text(original + "\n# mutated\n")
            with self.assertRaisesRegex(RuntimeError, "frozen file changed"):
                confirm.run(args)
            args.schedule.write_text(original)
            plan = confirm.read(args.area / "plan.json")
            plan["cells"].pop()
            confirm.write(args.area / "plan.json", plan)
            with self.assertRaisesRegex(RuntimeError, "canonical 36"):
                confirm.run(args)
            self.assertFalse((args.area / "results").exists())

    def test_nonarchive_evidence_counts_toward_temporary_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "report.json").write_bytes(b"r" * 11)
            active = root / "active"
            active.mkdir()
            (active / "scratch.bin").write_bytes(b"s" * 13)
            self.assertEqual(confirm.retained_bytes(root), 24)
            self.assertEqual(confirm.retained_bytes(root, exclude=active), 11)


if __name__ == "__main__":
    unittest.main()
