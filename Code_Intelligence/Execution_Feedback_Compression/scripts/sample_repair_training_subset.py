"""Create a balanced repair-training subset from a prebuilt repair JSONL file."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--per-language-error", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260623)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    reservoirs: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen = Counter()
    matched = Counter()

    with args.input.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            key = (row.get("language", "unknown"), row.get("error_type", "unknown"))
            seen[key] += 1
            matched[key] += 1
            bucket = reservoirs[key]
            if len(bucket) < args.per_language_error:
                bucket.append(row)
            else:
                index = rng.randint(0, matched[key] - 1)
                if index < args.per_language_error:
                    bucket[index] = row

    selected = []
    for key in sorted(reservoirs):
        selected.extend(reservoirs[key])
    rng.shuffle(selected)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in selected:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    counts = Counter(f"{row.get('language')}::{row.get('error_type')}" for row in selected)
    manifest = {
        "input": str(args.input),
        "output": str(args.output),
        "seed": args.seed,
        "per_language_error": args.per_language_error,
        "selected_records": len(selected),
        "selected_by_language_error": dict(sorted(counts.items())),
        "available_by_language_error": {
            f"{language}::{error_type}": count for (language, error_type), count in sorted(seen.items())
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
