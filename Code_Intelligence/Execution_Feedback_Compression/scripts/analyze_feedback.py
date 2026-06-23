"""Analyze feedback artifacts for compression statistics and status crosstabs."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def token_count(value: object) -> int:
    if isinstance(value, str):
        return len(value.split())
    return len(json.dumps(value, ensure_ascii=False).split())


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    args = parse_args()
    crosstab = Counter()
    observed = Counter()
    dataset = Counter()
    lengths: dict[str, list[int]] = defaultdict(list)
    ratios: dict[str, list[float]] = defaultdict(list)
    examples = []

    with args.input.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            ds = record.get("dataset_status_buggy")
            dataset[ds] += 1
            results = record.get("test_results") or []
            final_status = "NoRunnableTests"
            if record.get("unsafe_skipped"):
                final_status = "UnsafeSkipped"
            elif results and all(result["observed_status"] == "Accepted" for result in results):
                final_status = "AcceptedOnSampleTests"
            elif results:
                final_status = results[-1]["observed_status"]
            observed[final_status] += 1
            crosstab[(ds, final_status)] += 1

            for result in results:
                feedback = result.get("feedback", {})
                raw_len = max(1, token_count(feedback.get("raw", "")))
                for name, value in feedback.items():
                    count = token_count(value)
                    lengths[name].append(count)
                    if name != "raw":
                        ratios[name].append(count / raw_len)
                if len(examples) < 5 and result["observed_status"] != "Accepted":
                    examples.append(
                        {
                            "problem_id": record.get("problem_id"),
                            "dataset_status": ds,
                            "observed_status": result["observed_status"],
                            "detail": result["detail"],
                            "feedback": feedback,
                        }
                    )
                    break

    summary = {
        "records": sum(dataset.values()),
        "dataset_status": dict(dataset),
        "observed_status": dict(observed),
        "crosstab": {
            f"{dataset_status} -> {observed_status}": count
            for (dataset_status, observed_status), count in sorted(crosstab.items())
        },
        "feedback_token_lengths": {
            name: {
                "n": len(values),
                "mean": round(mean(values), 3),
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
            }
            for name, values in sorted(lengths.items())
        },
        "compression_ratio_vs_raw": {
            name: {
                "n": len(values),
                "mean": round(mean(values), 4),
                "min": round(min(values), 4) if values else 0,
                "max": round(max(values), 4) if values else 0,
            }
            for name, values in sorted(ratios.items())
        },
        "examples": examples,
    }
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
