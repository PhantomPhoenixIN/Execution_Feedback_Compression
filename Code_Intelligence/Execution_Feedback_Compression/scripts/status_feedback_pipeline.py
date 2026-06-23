"""Generate language-agnostic feedback variants from judge status and diffs.

This is a fallback for languages whose compiler/runtime is unavailable on the
current machine. It does not replace execution feedback; it creates comparable
status/diff-conditioned artifacts so multilingual training data can be prepared
while execution-grade Java/C++ evaluation is pending toolchain setup.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metrics", required=True, type=Path)
    return parser.parse_args()


def diff_summary(record: dict) -> dict:
    diffs = record.get("diffs") or []
    return {
        "num_hunks": len(diffs),
        "ops": [item.get("change") for item in diffs[:10]],
        "spans": [
            {
                "op": item.get("change"),
                "buggy_start": item.get("i1"),
                "buggy_end": item.get("i2"),
                "fixed_start": item.get("j1"),
                "fixed_end": item.get("j2"),
            }
            for item in diffs[:5]
        ],
    }


def build_feedback(record: dict) -> dict:
    status = record.get("status_buggy", "")
    language = record.get("language", "")
    summary = diff_summary(record)
    ops = ", ".join(op for op in summary["ops"] if op) or "unknown"
    raw = f"Online judge status: {status}\nLanguage: {language}\nDiff operations: {ops}"
    localized_lines = [raw]
    for span in summary["spans"]:
        if span["buggy_start"] is not None:
            localized_lines.append(
                f"{span['op']} buggy lines {span['buggy_start']}:{span['buggy_end']}"
            )
    structured = {
        "feedback_status": status,
        "language": language,
        "judge_label_only": True,
        "diff_summary": summary,
    }
    natural = f"The online judge labeled this {language} submission as {status}."
    if summary["num_hunks"]:
        natural += f" The accepted fix changes {summary['num_hunks']} diff hunk(s)."
    return {
        "none": "",
        "raw": raw,
        "categorical": status,
        "localized": "\n".join(localized_lines),
        "structured": structured,
        "natural_language": natural,
    }


def process_record(record: dict) -> dict:
    status = record.get("status_buggy", "")
    return {
        "problem_id": record.get("problem_id"),
        "user_id": record.get("user_id"),
        "language": record.get("language"),
        "buggy_submission_id": record.get("buggy_submission_id"),
        "fixed_submission_id": record.get("fixed_submission_id"),
        "dataset_status_buggy": status,
        "num_tests": len(record.get("test_cases") or []),
        "unsafe_skipped": False,
        "unsafe_reason": "",
        "test_results": [
            {
                "test_name": "JudgeStatus",
                "observed_status": status,
                "detail": "judge_label_only",
                "returncode": None,
                "elapsed_seconds": 0.0,
                "stdout_chars": 0,
                "stderr_chars": 0,
                "feedback": build_feedback(record),
            }
        ],
    }


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    counters = Counter()
    total = 0
    with args.input.open("r", encoding="utf-8") as src, args.output.open("w", encoding="utf-8") as dst:
        for line in src:
            record = json.loads(line)
            total += 1
            counters[f"{record.get('language')}::{record.get('status_buggy')}"] += 1
            dst.write(json.dumps(process_record(record), ensure_ascii=False) + "\n")
    metrics = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "records": total,
        "language_status": dict(counters),
        "feedback_source": "judge_status_and_diff_metadata",
    }
    args.metrics.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
