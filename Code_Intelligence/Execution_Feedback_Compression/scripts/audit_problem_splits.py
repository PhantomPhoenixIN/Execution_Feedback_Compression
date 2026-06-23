"""Audit problem-level splits for leakage and balance."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def load_split(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def summarize(rows: list[dict]) -> dict:
    return {
        "records": len(rows),
        "problems": len({row.get("problem_id") for row in rows}),
        "language": dict(Counter(row.get("language") for row in rows)),
        "status": dict(Counter(row.get("status_buggy") for row in rows)),
        "error_type": dict(Counter(row.get("error_type", row.get("status_buggy")) for row in rows)),
        "language_status": dict(
            Counter(f"{row.get('language')}::{row.get('status_buggy')}" for row in rows)
        ),
        "language_error_type": dict(
            Counter(f"{row.get('language')}::{row.get('error_type', row.get('status_buggy'))}" for row in rows)
        ),
    }


def main() -> None:
    args = parse_args()
    splits = {name: load_split(args.sample_dir / f"{name}.jsonl") for name in ["train", "validation", "test"]}
    problem_sets = {name: {row.get("problem_id") for row in rows} for name, rows in splits.items()}
    overlaps = {}
    names = list(problem_sets)
    for i, first in enumerate(names):
        for second in names[i + 1 :]:
            overlaps[f"{first}_vs_{second}"] = sorted(problem_sets[first] & problem_sets[second])

    audit = {
        "sample_dir": str(args.sample_dir),
        "splits": {name: summarize(rows) for name, rows in splits.items()},
        "problem_overlap_counts": {name: len(values) for name, values in overlaps.items()},
        "problem_overlaps": overlaps,
        "leakage_free": all(len(values) == 0 for values in overlaps.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
