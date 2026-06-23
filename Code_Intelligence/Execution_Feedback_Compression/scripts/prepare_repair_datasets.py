"""Create paired repair datasets for feedback-format experiments."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


FORMATS = [
    "none",
    "raw",
    "categorical",
    "localized",
    "structured",
    "natural_language",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True, type=Path)
    parser.add_argument("--feedback", required=True, type=Path)
    parser.add_argument("--descriptions", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--split-name", choices=["train", "validation", "test"], help="Write one pre-split dataset instead of random train/test split.")
    parser.add_argument("--formats", nargs="+", default=FORMATS)
    parser.add_argument("--include-description", action="store_true")
    parser.add_argument("--max-code-chars", type=int, default=3500)
    parser.add_argument("--max-feedback-chars", type=int, default=1200)
    return parser.parse_args()


def load_descriptions(path: Path) -> dict[str, str]:
    descriptions = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            descriptions[record["problem_id"]] = record.get("description", "")
    return descriptions


def load_jsonl_by_submission(path: Path, key: str) -> dict[str, dict]:
    records = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            records[record[key]] = record
    return records


def first_failure(feedback_record: dict) -> dict | None:
    for result in feedback_record.get("test_results") or []:
        if result.get("observed_status") != "Accepted":
            return result
    return None


def feedback_to_text(value: object, max_chars: int) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text.strip()[:max_chars]


def build_input(
    record: dict,
    feedback_value: object,
    feedback_format: str,
    description: str,
    include_description: bool,
    max_code_chars: int,
    max_feedback_chars: int,
) -> str:
    code = record.get("buggy_code", "")[:max_code_chars]
    feedback = feedback_to_text(feedback_value, max_feedback_chars)
    parts = [
        f"repair {record.get('language', 'code')} code",
        f"buggy_status: {record.get('status_buggy', '')}",
        f"feedback_format: {feedback_format}",
    ]
    if include_description and description:
        parts.append(f"problem: {description[:800]}")
    if feedback:
        parts.append(f"feedback: {feedback}")
    parts.append(f"buggy_code:\n{code}")
    return "\n".join(parts)


def stratified_split(rows: list[dict], seed: int, test_ratio: float) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        buckets[row["observed_status"]].append(row)
    train, test = [], []
    for bucket in buckets.values():
        rng.shuffle(bucket)
        n_test = max(1, round(len(bucket) * test_ratio)) if len(bucket) > 1 else 0
        test.extend(bucket[:n_test])
        train.extend(bucket[n_test:])
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    descriptions = load_descriptions(args.descriptions)
    sample_records = load_jsonl_by_submission(args.sample, "buggy_submission_id")
    feedback_records = load_jsonl_by_submission(args.feedback, "buggy_submission_id")

    base_rows = []
    for submission_id, feedback_record in feedback_records.items():
        record = sample_records.get(submission_id)
        failure = first_failure(feedback_record)
        if not record or not failure:
            continue
        base_rows.append(
            {
                "buggy_submission_id": submission_id,
                "fixed_submission_id": record.get("fixed_submission_id"),
                "problem_id": record.get("problem_id"),
                "dataset_status": record.get("status_buggy"),
                "error_type": record.get("error_type"),
                "observed_status": failure.get("observed_status"),
                "detail": failure.get("detail"),
                "feedback": failure.get("feedback", {}),
                "buggy_code": record.get("buggy_code", ""),
                "fixed_code": record.get("fixed_code", ""),
                "language": record.get("language", ""),
            }
        )

    if args.split_name:
        split_map = {args.split_name: base_rows}
    else:
        train_base, test_base = stratified_split(base_rows, args.seed, args.test_ratio)
        split_map = {"train": train_base, "test": test_base}
    manifest = {
        "seed": args.seed,
        "test_ratio": args.test_ratio,
        "include_description": args.include_description,
        "formats": args.formats,
        "base_records": len(base_rows),
        "split_name": args.split_name,
        "split_records": {name: len(rows) for name, rows in split_map.items()},
        "observed_status_counts": dict(Counter(row["observed_status"] for row in base_rows)),
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def write_split(split_name: str, rows: list[dict], feedback_format: str) -> None:
        out = args.output_dir / f"{feedback_format}_{split_name}.jsonl"
        with out.open("w", encoding="utf-8") as handle:
            for row in rows:
                description = descriptions.get(row["problem_id"], "")
                item = {
                    "id": row["buggy_submission_id"],
                    "problem_id": row["problem_id"],
                    "language": row.get("language", ""),
                    "dataset_status": row["dataset_status"],
                    "error_type": row.get("error_type"),
                    "observed_status": row["observed_status"],
                    "detail": row["detail"],
                    "input_text": build_input(
                        row,
                        row["feedback"].get(feedback_format, ""),
                        feedback_format,
                        description,
                        args.include_description,
                        args.max_code_chars,
                        args.max_feedback_chars,
                    ),
                    "target_text": row["fixed_code"][: args.max_code_chars],
                }
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    for feedback_format in args.formats:
        for split_name, rows in split_map.items():
            write_split(split_name, rows, feedback_format)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
