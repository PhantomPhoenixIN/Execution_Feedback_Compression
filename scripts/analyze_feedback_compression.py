"""Analyze input/feedback length differences across feedback representations."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


FORMATS = ["none", "raw", "categorical", "localized", "structured", "natural_language"]


def token_count(text: str) -> int:
    return len(text.split())


def extract_feedback(input_text: str) -> str:
    start_marker = "feedback:"
    end_marker = "\nbuggy_code:"
    if start_marker not in input_text:
        return ""
    feedback = input_text.split(start_marker, 1)[1]
    if end_marker in feedback:
        feedback = feedback.split(end_marker, 1)[0]
    return feedback.strip()


def summarize(values: list[int]) -> dict:
    if not values:
        return {"count": 0, "mean": 0.0, "median": 0.0, "min": 0, "max": 0}
    return {
        "count": len(values),
        "mean": mean(values),
        "median": median(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--split", default="validation", choices=["train", "validation", "test"])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--latex", required=True, type=Path)
    args = parser.parse_args()

    rows = {}
    for feedback_format in FORMATS:
        path = args.data_dir / f"{feedback_format}_{args.split}.jsonl"
        feedback_tokens = []
        input_tokens = []
        target_tokens = []
        by_error_type = defaultdict(list)
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                feedback = extract_feedback(row["input_text"])
                ftoks = token_count(feedback)
                feedback_tokens.append(ftoks)
                input_tokens.append(token_count(row["input_text"]))
                target_tokens.append(token_count(row["target_text"]))
                by_error_type[row.get("error_type", "unknown")].append(ftoks)
        rows[feedback_format] = {
            "feedback_tokens": summarize(feedback_tokens),
            "input_tokens": summarize(input_tokens),
            "target_tokens": summarize(target_tokens),
            "feedback_tokens_by_error_type": {
                error_type: summarize(values) for error_type, values in sorted(by_error_type.items())
            },
        }

    raw_mean = rows["raw"]["feedback_tokens"]["mean"] or 1.0
    for feedback_format, stats in rows.items():
        current = stats["feedback_tokens"]["mean"]
        stats["compression_vs_raw"] = raw_mean / current if current else None
        stats["mean_feedback_tokens"] = current

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.latex.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    labels = {
        "none": "None",
        "raw": "Raw",
        "categorical": "Categorical",
        "localized": "Localized",
        "structured": "Structured",
        "natural_language": "Natural language",
    }
    with args.latex.open("w", encoding="utf-8") as handle:
        handle.write("\\begin{table*}[t]\n")
        handle.write("\\centering\n")
        handle.write("\\caption{Feedback length statistics on the validation split.}\n")
        handle.write("\\label{tab:feedback-length}\n")
        handle.write("\\begin{tabular}{lrrr}\n")
        handle.write("\\toprule\n")
        handle.write("Condition & Mean tokens & Median tokens & Raw/condition \\\\\n")
        handle.write("\\midrule\n")
        for feedback_format in FORMATS:
            stats = rows[feedback_format]["feedback_tokens"]
            compression = rows[feedback_format]["compression_vs_raw"]
            compression_text = "--" if compression is None else f"{compression:.2f}x"
            handle.write(
                f"{labels[feedback_format]} & {stats['mean']:.1f} & {stats['median']:.1f} & {compression_text} \\\\\n"
            )
        handle.write("\\bottomrule\n")
        handle.write("\\end{tabular}\n")
        handle.write("\\end{table*}\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
