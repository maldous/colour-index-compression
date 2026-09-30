"""Run frozen Track A feedback codec on one predeclared contiguous region."""
import argparse
import hashlib
import json
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from benchmarks import hutter_track_a_feedback as codec


def sha(data): return hashlib.sha256(data).hexdigest()


def run(receipt, input_path, offset, size, label, budget_seconds=300):
    receipt = Path(receipt).resolve()
    if receipt.exists(): raise FileExistsError("immutable receipt exists")
    if not 0 < size <= 8 << 20 or not 0 < budget_seconds <= 300: raise ValueError("invalid bounded scale request")
    plan = {"hypothesis": "The frozen paid composition-feedback benefit persists on a longer contiguous Wikipedia region after all count metadata is charged.",
            "matched_control": "Unchanged causal range codec with the same high-nibble predecessor context.",
            "configuration": "Frozen Track A feedback encoder; no parameter changes after development/holdout validation.",
            "resource_budget": {"wall_seconds": budget_seconds, "cpu": "logical CPU 2", "ram_bytes": 2147483648, "swap_bytes": 0, "temporary_disk_bytes": 1073741824, "warmup": "none"},
            "promotion_criteria": "Both physical streams independently decode and feedback is smaller; 8 MiB only if the 1 MiB observed elapsed time makes it feasible within its separately predeclared 300-second budget."}
    source_path = Path(input_path)
    with source_path.open("rb") as handle:
        handle.seek(offset); source = handle.read(size)
    if len(source) != size: raise ValueError("canonical input shorter than requested range")
    artifacts = receipt.parent / (receipt.stem + "-frames"); artifacts.mkdir(parents=True, exist_ok=False)
    began = time.monotonic(); row, frames = codec._one(label, source)
    for method, frame in frames.items():
        packed = artifacts / f"{method}.cixtf"; restored = packed.with_suffix(".restored"); packed.write_bytes(frame)
        subprocess.run([sys.executable, str(Path(codec.__file__).resolve()), "--decode", str(packed), "--output", str(restored)], check=True)
        if restored.read_bytes() != source: raise AssertionError("independent decoder mismatch")
        next(x for x in row["rows"] if x["method"] == method)["independent_decode_sha256"] = sha(restored.read_bytes())
    elapsed = time.monotonic() - began
    causal = next(x for x in row["rows"] if x["method"] == "causal")["physical_bytes"]
    feedback = next(x for x in row["rows"] if x["method"] == "feedback")["physical_bytes"]
    output = {"schema": "cix-bounded-track-a-feedback-scale-v1", "phase": "completed", "hypothesis": plan,
              "frozen_codec_sha256": sha(Path(codec.__file__).read_bytes()), "input": {"path": str(source_path), "offset": offset, "bytes": size, "sha256": sha(source)},
              "result": row, "elapsed_seconds": elapsed, "throughput_mib_s": size / 1048576 / elapsed,
              "causal_bytes": causal, "feedback_bytes": feedback, "feedback_minus_causal_bytes": feedback - causal,
              "verification": "independent child decoder SHA-256 equals input for both physical streams", "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    receipt.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n"); return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--receipt", required=True); p.add_argument("--input", required=True); p.add_argument("--offset", type=int, required=True); p.add_argument("--bytes", type=int, required=True); p.add_argument("--label", required=True); p.add_argument("--budget-seconds", type=int, default=300)
    a = p.parse_args(); print(json.dumps(run(a.receipt, a.input, a.offset, a.bytes, a.label, a.budget_seconds), sort_keys=True))


if __name__ == "__main__": main()
