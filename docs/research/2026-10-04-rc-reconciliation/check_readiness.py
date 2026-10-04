"""Read-only consistency check; actual receipts must still be reviewed by RC51."""
import argparse
import json
import re
from pathlib import Path

EXPECTED_PRE = {f"RC{n:02d}" for n in range(1, 56)} - {
    "RC42", "RC51", "RC52", "RC53", "RC54"
}
EXPECTED_EXTERNAL = {"RC42-owned", "RC54-sdk-runners", "RC54-identities"}


def receipt_bound(receipt, identity):
    return (
        bool(identity)
        and isinstance(receipt, dict)
        and receipt.get("rc_identity") == identity
        and bool(receipt.get("path"))
        and re.fullmatch(r"[0-9a-f]{64}", receipt.get("sha256", "")) is not None
    )


def accepted(row, identity):
    return (
        row.get("status") == "accepted"
        and any(receipt_bound(e, identity) for e in row.get("current_rc_evidence", []))
    )


def evaluate(document):
    """Check declared evidence bindings, not files, test outcomes or authorization."""
    blockers = []
    rows = document.get("requirements", [])
    by_id = {r["id"]: r for r in rows}
    if len(by_id) != len(rows) or set(by_id) != {f"RC{n:02d}" for n in range(1, 56)}:
        blockers.append("requirement inventory differs from the reconciled 55 IDs")
    declared = document.get("pre_benchmark_prerequisites", [])
    if set(declared) != EXPECTED_PRE or len(declared) != len(EXPECTED_PRE):
        blockers.append("pre-benchmark source prerequisite set changed")
    ext_declared = document.get("pre_benchmark_external_obligations", [])
    if set(ext_declared) != EXPECTED_EXTERNAL or len(ext_declared) != len(EXPECTED_EXTERNAL):
        blockers.append("required external owned obligations changed")
    readiness = document.get("readiness", {})
    identity = readiness.get("rc_identity")
    if not identity:
        blockers.append("current RC identity missing")
    for identifier in sorted(EXPECTED_PRE):
        if not accepted(by_id.get(identifier, {}), identity):
            blockers.append(f"{identifier}: current-RC acceptance evidence missing")
    obligations = document.get("external_obligations", [])
    external = {r["id"]: r for r in obligations}
    if len(external) != len(obligations):
        blockers.append("duplicate external obligation")
    for identifier in sorted(EXPECTED_EXTERNAL):
        if not accepted(external.get(identifier, {}), identity):
            blockers.append(f"{identifier}: owned work or qualification missing")
    claims = document.get("support_claims", {})
    for identifier, claim in (
        ("RC42-upstream", "stock_format_extensions"),
        ("RC54-registry-stock", "registered_stock_interoperability"),
    ):
        if claims.get(claim, False) and not accepted(external.get(identifier, {}), identity):
            blockers.append(f"{identifier}: stock-support claim lacks acceptance")
    gate_blockers = []
    if not accepted(by_id.get("RC51", {}), identity):
        gate_blockers.append("RC51 independent readiness acceptance missing")
    for field in ("freeze_manifest", "benchmark_plan", "independent_review"):
        if not receipt_bound(readiness.get(field), identity):
            gate_blockers.append(f"readiness {field} is not bound to current RC")
    if readiness.get("transition_accepted") is not True:
        gate_blockers.append("readiness transition has not been accepted")
    if document.get("benchmark_gate") != "READY":
        gate_blockers.append("benchmark gate is not READY")
    return {
        "source_prerequisites_ready": not blockers,
        "benchmark_ready": not blockers and not gate_blockers,
        "prerequisite_blockers": blockers,
        "gate_blockers": gate_blockers,
        "scope": "Declared ledger consistency only; no receipt authentication or execution.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    result = evaluate(json.loads(args.ledger.read_text()))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["benchmark_ready"] else 1)
