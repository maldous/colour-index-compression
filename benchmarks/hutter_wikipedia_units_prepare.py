"""Freeze paragraph-unit ablations; preparation never starts compression."""
from __future__ import annotations
import json
from pathlib import Path
from benchmarks.hutter_wikipedia_matrix import ROOT, REL, CORPUS_SHA, immutable, sha, event
from benchmarks.hutter_experiment_registry import Registry, digest
from benchmarks.hutter_bounded_runner import build_identity, load_manifest

BUILD = ["benchmarks/hutter_bounded_runner.py", "benchmarks/hutter_wikipedia_units_probe.py",
         "benchmarks/hutter_wikipedia_body_units.py", "benchmarks/hutter_wikipedia_unit_profile.py",
         "benchmarks/hutter_wikipedia_body_lines.py", "benchmarks/hutter_structure_probe.py",
         "cix/__init__.py", "cix/multinomial.py"]


def fixture():
    area = ROOT / REL
    literal = b"Local history records the settlement and its changing population. " * 11
    source = b"boundary &amp;\x00\n" + b"".join(
        b"<page><title>Town" + str(i).encode() + b"</title><revision><text xml:space=\"preserve\">" +
        literal + b"[[Town " + str(i).encode() + b"]] had " + str(1000+i*17).encode() +
        b" residents and " + str(i+20).encode() + b" houses.\n\n" +
        b"This literal record has different prose "+str(i).encode()+b" &lt;ref&gt; exact bytes.\n" +
        b"</text></revision></page>\n" for i in range(40)) + b"<page><text>unfinished tail"
    path = area / "unit-fixtures/paragraph-v1.bin"; path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != source: raise ValueError("fixture changed")
    if not path.exists(): path.write_bytes(source)
    return {"path": str(path), "offset": 0, "length": len(source), "sha256": sha(path)}


def prepare(name, source, mode, cpu, *, stratum="synthetic", budget=300, control=None, owner="/root/paragraph_trials", opportunity="repeated_body_families"):
    if mode not in ("original", "paragraph-16384", "line-4096") or cpu not in (4, 6): raise ValueError("invalid bounded unit trial")
    root = ROOT; area = root / REL
    registry = Registry(area / "registry")
    input_id = registry.register_input(CORPUS_SHA if Path(source["path"]).name == "enwik9" else source["sha256"], source["offset"], source["length"], source["sha256"])
    classification = registry.record_classification(input_id, {"name": name, "opportunity_class": opportunity,
        "evidence_stratum": stratum, "expected_mechanism": "shared complete paragraph skeleton plus exact number/link substitutions; all other bytes literal"},
        {"preparation_source": "benchmarks/hutter_wikipedia_units_prepare.py", "preparation_sha256": sha(Path(__file__)),
         "selection_evidence": str(REL / "revised-priorities.json") if stratum != "synthetic" else "deterministic 40-page fixture in preparation source"})
    event(registry, input_id, "development", [str(REL / "registry/classifications" / (classification + ".json"))])
    m = json.loads((root / "docs/research/2026-09-30-wikipedia-body/manifests/synthetic-original.json").read_text())
    m["input"] = source; m["build_paths"] = BUILD
    m["budget"] = {"cpu": cpu, "max_rss_bytes": 3000000000, "max_temp_bytes": 1000000000, "wall_seconds": budget}
    m["artifacts"]["archive"] = "{workdir}/candidate.cixunits"
    for key in ("encode_command", "decode_command"):
        m[key][1] = str(root / "benchmarks/hutter_wikipedia_units_probe.py")
        m[key] = [value.replace("candidate.cixstr", "candidate.cixunits") for value in m[key]]
    m["encode_command"][m["encode_command"].index("--mode")+1] = mode
    m["configuration"].update(mode=mode, evidence_stratum=stratum, opportunity_class=opportunity,
        matrix_input_id=input_id, strength="correctness" if stratum == "synthetic" else "structurally_selected",
        source_filename="candidate.source.bin", framing_policy="identical 29-byte header and fixed metadata across original/paragraph/line",
        outer_magic="CIXWUNT1", context_policy="empty_initial_preserve_contiguous", selector="NONE")
    m["initial_state"] = "empty predictor per contiguous input, state preserved within input; no warm-up/training/external data; identical policy across ablations"
    m["hypothesis"] = "Complete paragraph units may amortize paid dictionaries better than many line families while preserving surrounding source order. Longer-line mode is the simplest boundary ablation."
    m["mechanism"] = "raw original-byte PAQ control" if mode == "original" else mode+": shared skeletons, exact holes and literal exceptions; no rank coding claim"
    m["matched_control"] = "Identical bytes, pinned PAQv216 -4 AVX2, filename, empty initial state and exactly equal outer framing; raw control and two unit modes use the same wrapper."
    m["promotion_criteria"] = "Finished physical archive, all reconstruction costs, independent archive-only exact SHA. A gain must then pass representative/held-out/scaling gates; no full-enwik9. Size-rejected completed archives may skip decode only using a verified matching control."
    m["stage"] = "screening" if budget <= 300 else "moderate_contiguous"
    if budget > 300: m["longer_budget_justification"] = "Predeclared 4MiB comparison; existing same-backend trials require about400s per phase. Shared encode/decode deadline1200s, no extrapolated full score."
    if control:
        r = json.loads(Path(control).read_text())
        m["decode_size_gate"] = {"control_receipt": str(Path(control).resolve()), "archive_sha256": r["archive_sha256"], "control_bytes": r["archive_bytes"],
                                "matching_configuration_keys": ["paq_binary_sha256", "paq_options", "source_filename", "framing_policy", "context_policy"]}
    build = build_identity(m, root); key = "units-"+digest({"manifest":m,"build":build})[:24]
    path = area / "manifests" / (key+".json"); immutable(path,m)
    _, manifest_hash = load_manifest(path)
    cell = {"cell_id": key,"owner":owner,"input_id":input_id,"input_name":name,"mode":mode,"wave":1 if stratum=="synthetic" else 2,
            "manifest_path":str(path),"expected_manifest_sha256":manifest_hash,"expected_build_sha256":build,
            "output_dir":str(area / "runs" / key),"resource_lease":m["budget"]}
    immutable(area / "cells" / (key+".json"),cell)
    return cell
