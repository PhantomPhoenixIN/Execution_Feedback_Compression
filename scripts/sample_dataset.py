"""Sample pilot subsets from the Project CodeNet bug-fix JSONL.

The main dataset is large, so this script streams records and uses per-status
reservoir sampling. It writes a JSONL subset plus a manifest for reproducibility.
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
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--language", default="Python")
    parser.add_argument(
        "--statuses",
        nargs="+",
        default=["Runtime Error", "Wrong Answer", "Time Limit Exceeded"],
    )
    parser.add_argument("--per-status", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-code-chars", type=int, default=0)
    parser.add_argument(
        "--require-tests",
        action="store_true",
        help="Only keep records with embedded test_cases.",
    )
    return parser.parse_args()


def record_has_tests(record: dict) -> bool:
    tests = record.get("test_cases")
    if isinstance(tests, dict):
        return bool(tests)
    if isinstance(tests, list):
        return len(tests) > 0
    return False


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    wanted = set(args.statuses)
    reservoirs: dict[str, list[dict]] = defaultdict(list)
    seen = Counter()
    matched = Counter()
    skipped = Counter()

    with args.input.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                skipped["json_decode_error"] += 1
                continue

            if record.get("language") != args.language:
                continue

            status = record.get("status_buggy")
            if status not in wanted:
                continue

            seen[status] += 1
            if args.require_tests and not record_has_tests(record):
                skipped["missing_tests"] += 1
                continue
            if args.max_code_chars:
                if len(record.get("buggy_code", "")) > args.max_code_chars:
                    skipped["buggy_too_long"] += 1
                    continue
                if len(record.get("fixed_code", "")) > args.max_code_chars:
                    skipped["fixed_too_long"] += 1
                    continue

            matched[status] += 1
            bucket = reservoirs[status]
            if len(bucket) < args.per_status:
                bucket.append(record)
            else:
                index = rng.randint(0, matched[status] - 1)
                if index < args.per_status:
                    bucket[index] = record

    args.output.parent.mkdir(parents=True, exist_ok=True)
    selected = []
    for status in args.statuses:
        selected.extend(reservoirs.get(status, []))
    rng.shuffle(selected)

    with args.output.open("w", encoding="utf-8") as handle:
        for record in selected:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "output": str(args.output),
        "language": args.language,
        "statuses": args.statuses,
        "per_status": args.per_status,
        "seed": args.seed,
        "require_tests": args.require_tests,
        "max_code_chars": args.max_code_chars,
        "seen_by_status": dict(seen),
        "matched_by_status": dict(matched),
        "selected_by_status": {k: len(v) for k, v in reservoirs.items()},
        "selected_total": len(selected),
        "skipped": dict(skipped),
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
