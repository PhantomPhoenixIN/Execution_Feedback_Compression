"""Create LaTeX repair-breakdown tables by normalized error type."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


ERROR_ORDER = ["WA", "CE", "RE", "TLE", "MLE"]


def is_success(row: dict, metric: str) -> bool:
    if metric == "normalized_exact_match":
        return bool(row.get("normalized_exact_match"))
    if metric == "exact_match":
        return bool(row.get("exact_match"))
    if metric == "accepted":
        eval_row = row.get("prediction_eval", {})
        return eval_row.get("final_status") == "Accepted"
    raise ValueError(f"Unsupported metric: {metric}")


def load_condition(path: Path, metric: str) -> dict[str, Counter]:
    buckets: dict[str, Counter] = defaultdict(Counter)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            error_type = row.get("error_type") or "unknown"
            buckets[error_type]["total"] += 1
            buckets[error_type]["success"] += int(is_success(row, metric))
            buckets["Overall"]["total"] += 1
            buckets["Overall"]["success"] += int(is_success(row, metric))
    return buckets


def fmt(counter: Counter) -> str:
    total = counter["total"]
    if not total:
        return "--"
    return f"{100.0 * counter['success'] / total:.1f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conditions", nargs="+", required=True, help="NAME=PATH entries.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--caption", default="Repair effectiveness by normalized error type.")
    parser.add_argument("--label", default="tab:repair-breakdown")
    parser.add_argument("--metric", choices=["accepted", "exact_match", "normalized_exact_match"], default="accepted")
    args = parser.parse_args()

    rows = []
    for entry in args.conditions:
        name, path_text = entry.split("=", 1)
        buckets = load_condition(Path(path_text), args.metric)
        rows.append([name, *[fmt(buckets[error]) for error in ERROR_ORDER], fmt(buckets["Overall"])])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        handle.write("\\begin{table*}[t]\n")
        handle.write("\\centering\n")
        handle.write(f"\\caption{{{args.caption}}}\n")
        handle.write(f"\\label{{{args.label}}}\n")
        handle.write("\\begin{tabular}{lrrrrrr}\n")
        handle.write("\\toprule\n")
        handle.write("Condition & WA & CE & RE & TLE & MLE & Overall \\\\\n")
        handle.write("\\midrule\n")
        for row in rows:
            handle.write(" & ".join(row) + " \\\\\n")
        handle.write("\\bottomrule\n")
        handle.write("\\end{tabular}\n")
        handle.write("\\end{table*}\n")
    print(args.output)


if __name__ == "__main__":
    main()
