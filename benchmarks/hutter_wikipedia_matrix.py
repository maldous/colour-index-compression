#!/usr/bin/env python3
"""Shared input registry, owned trial preparation and live Wikipedia evidence.

Preparation is separate from execution. No command launches full enwik9,
publishes anything, or exposes held-out content to a model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from benchmarks.hutter_experiment_registry import Registry, canonical, digest
from benchmarks.hutter_experiment_cache import Cache
from benchmarks.hutter_bounded_runner import build_identity, load_manifest

ROOT = Path(__file__).resolve().parents[1]
REL = Path("docs/research/2026-09-30-wikipedia-matrix")
CORPUS = Path("/home/user/src/cix-baseline-data/inputs/enwik9")
CORPUS_SHA = "159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc"
DEV = [(0, "5ba647fec2ba51b0383cbe7147e15a478d85613245b7131c41764dbdd5062f77"),
       (100000000, "fd30602741222df957545a821556c8428bb8c3e4ed45634367ae8470d901c6ec"),
       (400000000, "a07035d4de761fc30cee70f4528156e8128abf7430222cfd63c2311168ea7f17")]
MODES = ("original", "body-lines-v1", "raw", "remaining", "rank")
INPUT_SET = "input-set-v2.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def immutable(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical(value) + b"\n"
    try:
        with path.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        if path.read_bytes() != payload:
            raise ValueError(f"immutable record changed: {path}")


def event(registry, input_id, kind, evidence):
    return registry.record_exposure(input_id, {
        "kind": kind, "evidence_refs": evidence,
        "userdirective_refs": ["Wikipedia shared ranked matrix and explicit opportunity-class directive, 2026-09-30"],
    })


def initialize(root=ROOT):
    from benchmarks.hutter_opportunity_inputs import default_specs, generate, provenance, CLASSES, one_factor_sweep_specs
    area = root / REL; registry = Registry(area / "registry")
    inputs = []
    generator_source = root / "benchmarks/hutter_opportunity_inputs.py"
    generator_copy = area / "generators" / (sha(generator_source) + ".py")
    generator_copy.parent.mkdir(parents=True, exist_ok=True)
    if not generator_copy.exists(): generator_copy.write_bytes(generator_source.read_bytes())
    for spec in default_specs():
        prov = provenance(spec); data = generate(spec)
        identifier = registry.register_input(prov["input_sha256"], 0, len(data), prov["input_sha256"])
        path = area / "inputs" / f"{prov['input_sha256']}.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and sha(path) != prov["input_sha256"]:
            raise ValueError("synthetic artifact changed")
        if not path.exists():
            with path.open("xb") as stream: stream.write(data)
            path.chmod(0o444)
        label = {"opportunity_class": spec["opportunity"], "strength": spec["strength"],
                 "evidence_stratum": "synthetic", "scale": "correctness",
                 "expected_mechanism": spec["opportunity"], "eligible_comparisons": list(MODES),
                 "name": spec["opportunity"] + "-" + spec["strength"]}
        classification = registry.record_classification(identifier, label, prov)
        event(registry, identifier, "development", [str(REL / "registry" / "classifications" / (classification + ".json"))])
        inputs.append({"input_id": identifier, "classification_id": classification, "path": str(path), **label})
    for offset, expected in DEV:
        with CORPUS.open("rb") as stream:
            stream.seek(offset); data = stream.read(4194304)
        if hashlib.sha256(data).hexdigest() != expected: raise ValueError("development input changed")
        identifier = registry.register_input(CORPUS_SHA, offset, len(data), expected)
        label = {"name": f"dev{offset}", "opportunity_class": "mixed_observed", "strength": "observed",
                 "evidence_stratum": "representative_development", "scale": "dev4MiB",
                 "classification_note": "fixed disjoint development ranges, not a probability sample; targeted features have a separate view",
                 "opportunity_classes": list(CLASSES), "eligible_comparisons": list(MODES)}
        provenance_ref = {"source": str(CORPUS), "source_sha256": CORPUS_SHA,
                          "profile": str(REL / "real-opportunity-locations.json"),
                          "profile_sha256": sha(area / "real-opportunity-locations.json")}
        classification = registry.record_classification(identifier, label, provenance_ref)
        event(registry, identifier, "profile", [provenance_ref["profile"]])
        event(registry, identifier, "historical_full_read", ["docs/research/2026-09-30-wikipedia-structure/plan.json"])
        inputs.append({"input_id": identifier, "classification_id": classification, "path": str(CORPUS), **label})
    immutable(area / INPUT_SET, {"schema": 2, "inputs": inputs,
              "holdouts": {"offsets": [600000000, 900000000], "status": "RESERVED_NOT_PROFILED",
                           "note": "Historical whole-corpus reads exist. Withheld from adaptive structural tuning only; no full-enwik9 or holdout execution."}})
    immutable(area / "input-set-v1-supersession.json", {"status": "SUPERSEDED_BEFORE_EXECUTION", "replacement": INPUT_SET,
        "reason": "v2 fixes census line values to vary within a family, adds actual codec-eligibility diagnostics and corrects distance documentation. No v1 PAQ trial was run; immutable v1 records/source preserved."})
    sweeps = one_factor_sweep_specs()
    immutable(area / "parameter-sweeps-v2.json", {"generator_sha256": sha(generator_source), "status": "PLANNED_NOT_EXECUTED", "specifications": sweeps,
        "policy": "one-factor contrasts, same seed within each class; every selected input must be registered/hashed before execution. No large inputs automatically materialized."})
    return inputs


def prepare(input_name, mode, owner, cpu, root=ROOT):
    if mode not in MODES: raise ValueError("unknown implementation")
    if not owner.startswith("/root/"): raise ValueError("explicit worker owner is required")
    if cpu not in (4, 6): raise ValueError("new matrix lanes are CPU4/6; CPU0/2 remain reserved for preserved trials")
    area = root / REL; registry = Registry(area / "registry")
    entry = next(x for x in json.loads((area / INPUT_SET).read_text())["inputs"] if x["name"] == input_name)
    identity = registry.get_input(entry["input_id"])
    if entry["evidence_stratum"] != "synthetic":
        raise ValueError("real trials require separate frozen promotion plan; existing real trials are preserved")
    body = root / "docs/research/2026-09-30-wikipedia-body/manifests"
    template = body / ("synthetic-body.json" if mode == "body-lines-v1" else "synthetic-original.json")
    if mode in ("raw", "remaining", "rank"):
        template = root / "docs/research/2026-09-30-wikipedia-columns/manifests" / f"small-{mode}.json"
    manifest = json.loads(template.read_text())
    manifest["input"] = {"path": entry["path"], "offset": identity["offset"], "length": identity["length"], "sha256": identity["range_sha256"]}
    manifest["budget"] = {"cpu": cpu, "max_rss_bytes": 3000000000, "max_temp_bytes": 1000000000, "wall_seconds": 300}
    manifest.pop("decode_size_gate", None)
    manifest["stage"] = "screening"
    manifest["configuration"].update({"matrix_input_id": entry["input_id"], "opportunity_class": entry["opportunity_class"],
        "evidence_stratum": entry["evidence_stratum"], "strength": entry["strength"], "experiment_phase": "opportunity_correctness",
        "execution_boundary": "one physical core, max2 new jobs while2 preserved moderate jobs run; aggregate max4/12GB/4GBtemp",
        "selector": "NONE: every candidate physical cost reported", "mode": mode})
    manifest["hypothesis"] = f"{entry['opportunity_class']}/{entry['strength']}: {mode} may expose the declared relation to pinned PAQ; weak/absent controls test mechanism specificity."
    manifest["mechanism"] = f"{mode}; opportunity={entry['opportunity_class']}; strength={entry['strength']}"
    manifest["initial_state"] = "empty predictor per complete input, preserved throughout that input; no training, warm-up, external dictionary, state sharing or prediction trace reuse"
    manifest["matched_control"] = "Exact same immutable input and original-byte PAQv216 -4 -simd AVX2, candidate.source.bin basename; same initial state. All representation bytes and wrapper overhead charged."
    manifest["promotion_criteria"] = "Complete physical archive + independent archive-only exact SHA decode. Synthetic win establishes mechanism evidence only; retain weak/absent failures. Before real holdout freeze on disjoint development evidence; no full-enwik9 authorised."
    build = build_identity(manifest, root)
    key = digest({"input_id": entry["input_id"], "mode": mode, "build": build,
                  "configuration": {k:v for k,v in manifest["configuration"].items() if k != "execution_boundary"},
                  "initial_state": manifest["initial_state"]})
    trial = "op-" + key[:24]
    path = area / "manifests" / (trial + ".json")
    immutable(path, manifest)
    _, manifest_sha = load_manifest(path)
    cell = {"cell_id": trial, "owner": owner, "input_id": entry["input_id"], "input_name": input_name,
            "mode": mode, "wave": 1, "manifest_path": str(path), "expected_manifest_sha256": manifest_sha,
            "expected_build_sha256": build, "output_dir": str(area / "runs" / trial),
            "resource_lease": manifest["budget"]}
    immutable(area / "cells" / (trial + ".json"), cell)
    return cell


def register_sweeps(root=ROOT):
    """Materialize bounded cross-cutting controls; never launch compression."""
    from benchmarks.hutter_opportunity_inputs import one_factor_sweep_specs, generate, provenance, CLASSES
    area = root / REL; registry = Registry(area / "registry")
    specs = one_factor_sweep_specs()
    baselines = []
    for index, opportunity in enumerate(CLASSES):
        baseline = {"opportunity": opportunity, "strength": "strong", "target_bytes": 32768,
                    "repetition": 8, "variation": 3, "distance": 5, "noise": 2,
                    "dictionary_cardinality": 7, "frequency": "uniform", "variation_type": "mixed",
                    "exception_rate_permille": 25, "prose_mixture_permille": 150, "seed": 7000 + index}
        baselines.append(baseline)
    rows, by_opportunity = [], {}
    for is_base, spec in [(True, spec) for spec in baselines] + [(False, spec) for spec in specs]:
        prov = provenance(spec); data = generate(spec)
        identifier = registry.register_input(prov["input_sha256"], 0, len(data), prov["input_sha256"])
        path = area / "inputs" / (prov["input_sha256"] + ".bin")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and sha(path) != prov["input_sha256"]: raise ValueError("changed sweep input")
        if not path.exists():
            with path.open("xb") as stream: stream.write(data)
            path.chmod(0o444)
        if is_base: by_opportunity[spec["opportunity"]] = {"input_id": identifier, "spec": spec}
        control = by_opportunity[spec["opportunity"]]
        changed = [key for key in spec if spec[key] != control["spec"][key]]
        if (is_base and changed) or (not is_base and len(changed) != 1):
            raise ValueError("sweep is not a matched one-factor contrast")
        label = {"opportunity_class": spec["opportunity"], "evidence_stratum": "synthetic",
                 "strength": "strong", "scale": "correctness", "suite": "one_factor_sweep",
                 "expected_mechanism": spec["opportunity"], "base_input_id": control["input_id"],
                 "changed_parameters": changed, "eligible_comparisons": list(MODES), "compression_status": "NOT_RUN"}
        classification = registry.record_classification(identifier, label, prov)
        event(registry, identifier, "development", [str(REL / "registry/classifications" / (classification + ".json"))])
        rows.append({"input_id": identifier, "classification_id": classification, "path": str(path), **label})
    immutable(area / "input-sweeps-v2.json", {"schema": 2, "inputs": rows,
          "note": "Synthetic bytes and diagnostics materialized and hashed; no compression measurement is implied."})
    return rows


def report(root=ROOT):
    from benchmarks.hutter_experiment_matrix import define_matrix, opportunity_cells
    from benchmarks.hutter_matrix_evidence import collect
    area = root / REL; area.mkdir(parents=True, exist_ok=True)
    evidence = collect(root)
    registry = Registry(area / "registry")
    cache = Cache(area / "cache")
    for row in evidence:
        source = row["input"]
        identifier = registry.register_input(CORPUS_SHA if Path(source["path"]).name == "enwik9" else source["sha256"],
                  source["offset"], source["length"], source["sha256"])
        row["input_id"] = identifier
        event(registry, identifier, "holdout_test" if row["evidence_stratum"] == "untouched_holdout" else "development", [row["receipt_path"]])
        if row.get("status") == "VERIFIED_SCREENING" and row.get("configuration", {}).get("mode") == "original":
            receipt = row.get("receipt_path", row.get("receipt"))
            if receipt:
                key = cache.put_control(root / receipt); cache.get_control(key)
                row["verified_control_cache_key"] = key
    grouped = defaultdict(list)
    for row in evidence:
        config = row["configuration"]
        key = (row["evidence_stratum"], config.get("opportunity_class", "legacy_mixed"), config.get("strength", "unspecified"),
               row["input_id"], config.get("paq_binary_sha256"), config.get("paq_options"), config.get("source_filename"), row["initial_state"])
        grouped[key].append(row)
    rankings = []
    for key, rows in sorted(grouped.items(), key=lambda pair: str(pair[0])):
        eligible = [r for r in rows if r["verification"] and r["archive"] and r["matched_raw_paq_control"]]
        eligible.sort(key=lambda r: (r["archive"]["total_bytes"], r["evidence_id"]))
        rankings.append({"stratum": key[0], "opportunity_class": key[1], "strength": key[2], "input_id": key[3],
                         "backend": list(key[4:]), "verified_size_order": [r["evidence_id"] for r in eligible],
                         "unranked": [r["evidence_id"] for r in rows if r not in eligible],
                         "promotion": "NONE_AUTOMATIC: requires consistent disjoint real development, frozen holdouts, bounded scaling and practical resources"})
    trials = []
    for path in sorted((area / "cells").glob("*.json")):
        cell = json.loads(path.read_text())
        prefix = str(Path(cell["output_dir"]).relative_to(root)) + "/"
        matched = [row for row in evidence if row["receipt_path"].startswith(prefix)]
        current = None
        for progress in sorted(Path(cell["output_dir"]).glob("*/progress.jsonl")):
            records = progress.read_text().splitlines()
            if records:
                try: current = json.loads(records[-1])
                except json.JSONDecodeError: pass  # writer may be appending
        trials.append({**cell, "status": matched[0]["status"] if matched else "RUNNING_OR_UNFINISHED" if current else "DECLARED_NOT_STARTED",
                       "evidence_ids": [row["evidence_id"] for row in matched], "last_progress": current})
    content = {"schema": 1, "input_registry": str(REL / "registry"), "coverage": opportunity_cells(),
               "research_backlog_cells": define_matrix(), "results": evidence, "rankings": rankings, "owned_trials": trials,
               "limits": {"full_enwik9_score": None, "holdout_status": "NOT_RUN",
                          "program_runtime_closure": "INCOMPLETE; not a Prize package size",
                          "interpretation": "Synthetic mechanism, targeted application, representative holdout are separate evidence strata. Regional wins are never added into a full-file score."}}
    (area / "live-results.json").write_text(json.dumps(content, indent=2) + "\n")
    lines = ["# Wikipedia opportunity experiment matrix", "", "Generated by `python -m benchmarks.hutter_wikipedia_matrix report`. Every physical candidate is shown before selection. Lower delta is better; missing values remain missing.", "",
             "Ranks are only within the same input, opportunity strength, evidence stratum and pinned backend. Fixed development offsets are not a probability sample. No full-enwik9 or Prize score is implied.", ""]
    for stratum in sorted({r["evidence_stratum"] for r in evidence} | {"synthetic", "targeted_real", "fixed_development", "untouched_holdout"}):
        if not any(r["evidence_stratum"] == stratum for r in evidence):
            lines += [f"## {stratum}", "", "**NOT MEASURED.** This evidence stratum cannot be substituted by synthetic or targeted wins.", ""]
            continue
        lines += [f"## {stratum}", "", "| Candidate / input | Complete bytes | vs matched PAQ | Independent SHA decode | Encode / decode seconds | Cgroup memory sampled high-water | Next decision |", "|---|---:|---:|---|---:|---:|---|"]
        for row in [r for r in evidence if r["evidence_stratum"] == stratum]:
            cfg, archive, phases = row["configuration"], row["archive"], row["phases"]
            times = [next((p["elapsed_seconds"] for p in phases if p["phase"].endswith("-" + phase)), None) for phase in ("encode", "decode")]
            memory = max((p.get("sampled_cgroup_memory_high_water_bytes") or 0 for p in phases), default=0)
            delta = row["difference_vs_matched_raw_paq_bytes"]
            decision = "retain negative" if delta is not None and delta >= 0 and cfg.get("mode") != "original" else "matched control" if cfg.get("mode") == "original" else "development/holdout gate required" if row["verification"] else "unqualified"
            name = f"{cfg.get('mode', '?')} / {cfg.get('opportunity_class', 'legacy')} {cfg.get('strength', '')} / {row['input']['offset']}+{row['input']['length']}"
            link = Path("../../..") / row["receipt_path"]
            lines.append(f"| [{name}]({link}) | {archive['total_bytes'] if archive else 'NOT COMPLETE'} | {delta if delta is not None else 'MISSING'} | {'PASS' if row['verification'] else row['status']} | {' / '.join('—' if t is None else format(t,'.2f') for t in times)} | {memory or 'MISSING'} | {decision} |")
        lines.append("")
    lines += ["## Declared worker cells", "", "| Input | Candidate | Owner | State |", "|---|---|---|---|"]
    for cell in trials:
        lines.append(f"| {cell['input_name']} | {cell['mode']} | {cell['owner']} | {cell['status']} |")
    lines.append("")
    lines += ["## Cost and qualification boundaries", "", "`live-results.json` includes each archive's payload, outer metadata and framing; transform rules, dictionaries, boundaries, counts, holes and literals are charged inside that payload. Diagnostic transform costs are pre-PAQ and are not added twice. Program source and binary inventory is separate; runtime/model package closure remains incomplete.", "", "Memory is a sampled cgroup high-water lower bound, not exact process peak RSS. Research timings are single bounded trials, with declared concurrency; they are not Prize qualification timings.", "", "Synthetic mechanism evidence, targeted Wikipedia application evidence and representative/withheld validation are separate. No current structural configuration has cleared the full promotion funnel.", ""]
    (area / "LIVE-RESULTS.md").write_text("\n".join(lines))
    return content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("initialize"); sub.add_parser("report"); sub.add_parser("register-sweeps")
    p = sub.add_parser("prepare")
    p.add_argument("input_name"); p.add_argument("mode", choices=MODES); p.add_argument("--owner", required=True); p.add_argument("--cpu", type=int, required=True)
    p = sub.add_parser("run-wave"); p.add_argument("cells", nargs="+")
    args = parser.parse_args()
    if args.command == "initialize": result = {"input_count": len(initialize())}
    elif args.command == "register-sweeps": result = {"input_count": len(register_sweeps())}
    elif args.command == "prepare": result = prepare(args.input_name, args.mode, args.owner, args.cpu)
    elif args.command == "report": result = {"result_count": len(report()["results"])}
    else:
        from benchmarks.hutter_experiment_scheduler import WaveScheduler
        cells = [json.loads(Path(path).read_text()) for path in args.cells]
        if any(json.loads(Path(cell["manifest_path"]).read_text())["budget"]["cpu"] not in (4, 6) for cell in cells):
            raise ValueError("dispatcher allows only the two shared matrix lanes CPU4/6")
        result = WaveScheduler(ROOT, max_jobs=2, max_memory_bytes=6000000000, max_temp_bytes=2000000000).run_wave(cells)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__": main()
