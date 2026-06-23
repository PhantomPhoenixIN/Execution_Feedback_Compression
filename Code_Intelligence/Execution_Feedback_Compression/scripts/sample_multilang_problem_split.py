"""Create a balanced multilingual sample with problem-level splits.

This script is intentionally independent of execution. It streams the large
CodeNet-derived JSONL once, samples a balanced fraction per language/status,
and then assigns train/dev/test by problem_id so no problem leaks across splits.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--languages", nargs="+", required=True)
    parser.add_argument("--statuses", nargs="+", required=True)
    parser.add_argument("--per-cell", type=int, default=2500)
    parser.add_argument("--cell-targets", type=Path, help="Optional JSON mapping language -> status/error type -> target.")
    parser.add_argument(
        "--normalize-error-types",
        action="store_true",
        help="Treat --statuses and --cell-targets keys as WA/CE/RE/TLE/MLE normalized error types.",
    )
    parser.add_argument("--seed", type=int, default=20260622)
    parser.add_argument("--require-tests", action="store_true")
    parser.add_argument("--max-buggy-code-chars", type=int, default=0)
    parser.add_argument("--max-fixed-code-chars", type=int, default=0)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--validation-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    return parser.parse_args()


def has_tests(record: dict) -> bool:
    tests = record.get("test_cases")
    return bool(tests) if isinstance(tests, (dict, list)) else False


def normalize_error_type(status: str) -> str:
    status = (status or "").strip().lower()
    if status == "wrong answer" or status.startswith("wa:"):
        return "WA"
    if status == "compile error":
        return "CE"
    if status == "runtime error":
        return "RE"
    if status == "time limit exceeded":
        return "TLE"
    if status == "memory limit exceeded":
        return "MLE"
    return "OTHER"


def load_targets(args: argparse.Namespace) -> dict[tuple[str, str], int]:
    targets = {}
    if args.cell_targets:
        raw = json.loads(args.cell_targets.read_text(encoding="utf-8"))
        for language, status_map in raw.items():
            for status, target in status_map.items():
                targets[(language, status)] = int(target)
        return targets
    for language in args.languages:
        for status in args.statuses:
            targets[(language, status)] = args.per_cell
    return targets


def keep_record(record: dict, args: argparse.Namespace, wanted_languages: set[str], wanted_statuses: set[str]) -> tuple[bool, str]:
    if record.get("language") not in wanted_languages:
        return False, "language"
    status_key = normalize_error_type(record.get("status_buggy", "")) if args.normalize_error_types else record.get("status_buggy")
    if status_key not in wanted_statuses:
        return False, "status"
    if args.require_tests and not has_tests(record):
        return False, "missing_tests"
    if args.max_buggy_code_chars and len(record.get("buggy_code", "")) > args.max_buggy_code_chars:
        return False, "buggy_too_long"
    if args.max_fixed_code_chars and len(record.get("fixed_code", "")) > args.max_fixed_code_chars:
        return False, "fixed_too_long"
    if not record.get("problem_id"):
        return False, "missing_problem_id"
    return True, ""


def assign_problem_splits(problem_ids: list[str], args: argparse.Namespace) -> dict[str, str]:
    rng = random.Random(args.seed)
    ids = sorted(set(problem_ids))
    rng.shuffle(ids)
    total = len(ids)
    n_train = round(total * args.train_ratio)
    n_validation = round(total * args.validation_ratio)
    split = {}
    for problem_id in ids[:n_train]:
        split[problem_id] = "train"
    for problem_id in ids[n_train : n_train + n_validation]:
        split[problem_id] = "validation"
    for problem_id in ids[n_train + n_validation :]:
        split[problem_id] = "test"
    return split


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    wanted_languages = set(args.languages)
    wanted_statuses = set(args.statuses)
    targets = load_targets(args)

    reservoirs: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen = Counter()
    matched = Counter()
    skipped = Counter()

    with args.input.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                skipped["json_decode_error"] += 1
                continue
            keep, reason = keep_record(record, args, wanted_languages, wanted_statuses)
            if not keep:
                if reason not in {"language", "status"}:
                    skipped[reason] += 1
                continue
            status_key = normalize_error_type(record.get("status_buggy", "")) if args.normalize_error_types else record["status_buggy"]
            key = (record["language"], status_key)
            seen[key] += 1
            target = targets.get(key, 0)
            if target <= 0:
                continue
            matched[key] += 1
            record["error_type"] = status_key
            bucket = reservoirs[key]
            if len(bucket) < target:
                bucket.append(record)
            else:
                index = rng.randint(0, matched[key] - 1)
                if index < target:
                    bucket[index] = record

    selected = []
    for language in args.languages:
        for status in args.statuses:
            selected.extend(reservoirs.get((language, status), []))
    rng.shuffle(selected)

    problem_splits = assign_problem_splits([row["problem_id"] for row in selected], args)
    split_rows: dict[str, list[dict]] = {"train": [], "validation": [], "test": []}
    for row in selected:
        split_rows[problem_splits[row["problem_id"]]].append(row)

    for split, rows in split_rows.items():
        with (args.output_dir / f"{split}.jsonl").open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (args.output_dir / "all.jsonl").open("w", encoding="utf-8") as handle:
        for row in selected:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "languages": args.languages,
        "statuses": args.statuses,
        "targets": {f"{language}::{status}": target for (language, status), target in targets.items()},
        "seed": args.seed,
        "split_unit": "problem_id",
        "split_ratios": {
            "train": args.train_ratio,
            "validation": args.validation_ratio,
            "test": args.test_ratio,
        },
        "filters": {
            "require_tests": args.require_tests,
            "max_buggy_code_chars": args.max_buggy_code_chars,
            "max_fixed_code_chars": args.max_fixed_code_chars,
        },
        "selected_total": len(selected),
        "selected_by_language_status": {
            f"{language}::{status}": len(reservoirs.get((language, status), []))
            for language in args.languages
            for status in args.statuses
        },
        "selected_by_error_type": dict(Counter(row.get("error_type", row.get("status_buggy", "")) for row in selected)),
        "split_records": {split: len(rows) for split, rows in split_rows.items()},
        "split_problems": {
            split: len({row["problem_id"] for row in rows}) for split, rows in split_rows.items()
        },
        "skipped": dict(skipped),
        "seen": {f"{language}::{status}": count for (language, status), count in seen.items()},
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
