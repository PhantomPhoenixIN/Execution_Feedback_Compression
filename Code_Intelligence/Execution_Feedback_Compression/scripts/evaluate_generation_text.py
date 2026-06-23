"""Language-agnostic text-generation diagnostics for repair predictions."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def load_rows(path: Path) -> dict[str, dict]:
    rows = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metrics", required=True, type=Path)
    args = parser.parse_args()

    outputs = []
    counters = Counter()
    by_language = defaultdict(Counter)
    by_status = defaultdict(Counter)
    by_error_type = defaultdict(Counter)
    with args.predictions.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            prediction = row.get("prediction", "")
            target = row.get("target_text", "")
            exact = prediction == target
            normalized_exact = normalize_text(prediction) == normalize_text(target)
            language = row.get("language") or "unknown"
            error_type = row.get("error_type") or "unknown"
            status = row.get("dataset_status") or row.get("observed_status") or "unknown"
            item = {
                "id": row["id"],
                "problem_id": row.get("problem_id"),
                "language": language,
                "error_type": error_type,
                "status": status,
                "exact_match": exact,
                "normalized_exact_match": normalized_exact,
                "prediction_chars": len(prediction),
                "target_chars": len(target),
                "input_chars": row.get("input_chars"),
            }
            outputs.append(item)
            counters["records"] += 1
            counters["exact_match"] += int(exact)
            counters["normalized_exact_match"] += int(normalized_exact)
            by_language[language]["records"] += 1
            by_language[language]["exact_match"] += int(exact)
            by_language[language]["normalized_exact_match"] += int(normalized_exact)
            by_status[status]["records"] += 1
            by_status[status]["exact_match"] += int(exact)
            by_status[status]["normalized_exact_match"] += int(normalized_exact)
            by_error_type[error_type]["records"] += 1
            by_error_type[error_type]["exact_match"] += int(exact)
            by_error_type[error_type]["normalized_exact_match"] += int(normalized_exact)

    def rates(counter: Counter) -> dict:
        records = counter["records"]
        return {
            "records": records,
            "exact_match": counter["exact_match"],
            "normalized_exact_match": counter["normalized_exact_match"],
            "exact_match_rate": counter["exact_match"] / records if records else 0.0,
            "normalized_exact_match_rate": counter["normalized_exact_match"] / records if records else 0.0,
        }

    metrics = {
        **rates(counters),
        "by_language": {key: rates(value) for key, value in sorted(by_language.items())},
        "by_status": {key: rates(value) for key, value in sorted(by_status.items())},
        "by_error_type": {key: rates(value) for key, value in sorted(by_error_type.items())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in outputs:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    args.metrics.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
