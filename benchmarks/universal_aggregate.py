#!/usr/bin/env python3
"""Aggregate isolated universal CIX member benchmark results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

AGGREGATE_CORPORA = {"canterbury", "calgary"}
ORDER = ("canterbury", "calgary", "artificial", "large")


def ratio(size: int, original: int) -> float:
    return 100.0 * size / original if original else 100.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="universal-members")
    parser.add_argument("--output", default="universal-results.md")
    args = parser.parse_args()

    root = Path(args.input)
    rows = [json.loads(path.read_text()) for path in sorted(root.rglob("*.json"))]
    if not rows:
        raise RuntimeError("no universal member results found")

    lines = [
        "# Universal CIX benchmark",
        "",
        "Every member uses the same format-agnostic CIX encoder policy.",
        "All CIX sizes are physical streams and were round-trip verified.",
        "",
    ]

    summary = {}

    for corpus in ORDER:
        subset = sorted(
            (row for row in rows if row["corpus"] == corpus),
            key=lambda row: row["file"],
        )
        if not subset:
            continue

        lines += [
            f"## {corpus}",
            "",
            "| file | CIX | gzip-9 | bzip2-9 | xz-9 | Brotli-11 | zstd-19 | enc s | dec s |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in subset:
            original = row["original"]
            lines.append(
                f"| {row['file']} | {ratio(row['cix'],original):.2f}% | "
                f"{ratio(row['gzip'],original):.2f}% | "
                f"{ratio(row['bzip2'],original):.2f}% | "
                f"{ratio(row['xz'],original):.2f}% | "
                f"{ratio(row['brotli'],original):.2f}% | "
                f"{ratio(row['zstd'],original):.2f}% | "
                f"{row['cix_seconds']:.2f} | {row['cix_decode_seconds']:.2f} |"
            )

        if corpus in AGGREGATE_CORPORA:
            total = sum(row["original"] for row in subset)
            aggregates = {
                codec: ratio(sum(row[codec] for row in subset), total)
                for codec in ("cix", "gzip", "bzip2", "xz", "brotli", "zstd")
            }
            summary[corpus] = aggregates
            lines += [
                "",
                f"- Aggregate CIX: {aggregates['cix']:.2f}%",
                f"- Aggregate gzip-9: {aggregates['gzip']:.2f}%",
                f"- Aggregate bzip2-9: {aggregates['bzip2']:.2f}%",
                f"- Aggregate xz-9: {aggregates['xz']:.2f}%",
                f"- Aggregate Brotli-11: {aggregates['brotli']:.2f}%",
                f"- Aggregate zstd-19: {aggregates['zstd']:.2f}%",
            ]
        else:
            lines += [
                "",
                "- No aggregate claim: pathological members are evaluated individually.",
            ]

        lines += ["", "### Winning CIX block models"]
        for row in subset:
            model_counts = {}
            for model in row["models"]:
                model_counts[model] = model_counts.get(model, 0) + 1
            compact = ", ".join(
                f"{name}×{count}"
                for name, count in sorted(
                    model_counts.items(), key=lambda item: (-item[1], item[0])
                )
            )
            lines.append(f"- {row['file']}: {compact}")
        lines.append("")

    Path(args.output).write_text("\n".join(lines) + "\n")
    Path("universal-summary.json").write_text(
        json.dumps({"aggregates": summary, "members": rows}, indent=2)
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
