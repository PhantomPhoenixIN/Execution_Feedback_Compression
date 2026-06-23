"""Create a compact qualitative repair-analysis report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True, type=Path)
    parser.add_argument("--runs", nargs="+", required=True, help="NAME=EVAL_OUTPUTS_JSONL")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-examples", type=int, default=3)
    return parser.parse_args()


def load_jsonl(path: Path, key: str) -> dict[str, dict]:
    rows = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row[key]] = row
    return rows


def status(row: dict) -> str:
    return row["prediction_eval"]["final_status"]


def short(text: str, limit: int = 700) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "\n..."


def main() -> None:
    args = parse_args()
    sample = load_jsonl(args.sample, "buggy_submission_id")
    runs = {}
    for item in args.runs:
        name, path = item.split("=", 1)
        runs[name] = load_jsonl(Path(path), "id")

    names = list(runs)
    shared = sorted(set.intersection(*(set(rows) for rows in runs.values())))
    correct_by_id = {
        row_id: {name for name in names if status(runs[name][row_id]) == "Accepted"}
        for row_id in shared
    }
    buckets = {
        "all_correct": [row_id for row_id, ok in correct_by_id.items() if len(ok) == len(names)],
        "none_only": [row_id for row_id, ok in correct_by_id.items() if ok == {"none"}],
        "feedback_only": [row_id for row_id, ok in correct_by_id.items() if ok and "none" not in ok],
        "mixed": [row_id for row_id, ok in correct_by_id.items() if ok and ok != {"none"} and "none" in ok and len(ok) < len(names)],
        "none_correct": [row_id for row_id, ok in correct_by_id.items() if not ok],
    }

    lines = [
        "# Qualitative Repair Analysis",
        "",
        f"Shared records: {len(shared)}",
        "",
        "## Outcome Buckets",
        "",
    ]
    for bucket, ids in buckets.items():
        lines.append(f"- {bucket}: {len(ids)}")

    lines.extend(["", "## Representative Examples", ""])
    for bucket, ids in buckets.items():
        if not ids:
            continue
        lines.append(f"### {bucket}")
        for row_id in ids[: args.max_examples]:
            source = sample[row_id]
            lines.append("")
            lines.append(f"#### {row_id} / {source.get('problem_id')} / {source.get('status_buggy')}")
            lines.append("")
            lines.append("Statuses: " + ", ".join(f"{name}={status(runs[name][row_id])}" for name in names))
            for name in names:
                row = runs[name][row_id]
                lines.append("")
                lines.append(f"`{name}` prediction:")
                lines.append("```python")
                lines.append(short(row.get("prediction", "")))
                lines.append("```")
            lines.append("")
            lines.append("Target preview:")
            lines.append("```python")
            lines.append(short(source.get("fixed_code", "")))
            lines.append("```")
        lines.append("")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({bucket: len(ids) for bucket, ids in buckets.items()}, indent=2))


if __name__ == "__main__":
    main()
