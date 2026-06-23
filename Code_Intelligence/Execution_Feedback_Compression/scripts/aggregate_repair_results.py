"""Aggregate repair experiment metrics and paired statistical comparisons."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from scipy.stats import binomtest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", nargs="+", required=True, help="NAME=RUN_DIR entries")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--mode",
        choices=["execution", "text"],
        default="execution",
        help="execution expects eval_outputs.jsonl; text expects generation_eval.jsonl.",
    )
    parser.add_argument(
        "--text-metric",
        choices=["exact_match", "normalized_exact_match"],
        default="normalized_exact_match",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_outputs(path: Path) -> dict[str, dict]:
    rows = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def is_correct(row: dict, mode: str, text_metric: str) -> bool:
    if mode == "execution":
        return row["prediction_eval"]["final_status"] == "Accepted"
    return bool(row.get(text_metric))


def row_error_type(row: dict) -> str:
    return row.get("error_type") or "unknown"


def mcnemar_exact(a_rows: dict[str, dict], b_rows: dict[str, dict], mode: str, text_metric: str, error_type: str | None = None) -> dict:
    shared_ids = sorted(set(a_rows) & set(b_rows))
    b_only = 0
    c_only = 0
    both = 0
    neither = 0
    used = 0
    for row_id in shared_ids:
        if error_type is not None and row_error_type(a_rows[row_id]) != error_type:
            continue
        used += 1
        a_ok = is_correct(a_rows[row_id], mode, text_metric)
        b_ok = is_correct(b_rows[row_id], mode, text_metric)
        if a_ok and b_ok:
            both += 1
        elif a_ok and not b_ok:
            b_only += 1
        elif not a_ok and b_ok:
            c_only += 1
        else:
            neither += 1
    discordant = b_only + c_only
    p_value = binomtest(min(b_only, c_only), discordant, 0.5).pvalue if discordant else 1.0
    return {
        "shared_records": used,
        "both_correct": both,
        "first_only_correct": b_only,
        "second_only_correct": c_only,
        "neither_correct": neither,
        "exact_mcnemar_p": p_value,
    }


def summarize_outputs(name: str, outputs: dict[str, dict], mode: str, text_metric: str, metrics: dict | None = None) -> dict:
    total = len(outputs)
    successes = sum(1 for row in outputs.values() if is_correct(row, mode, text_metric))
    ci_low, ci_high = wilson_ci(successes, total)
    by_error_type = {}
    for error_type in sorted({row_error_type(row) for row in outputs.values()}):
        rows = [row for row in outputs.values() if row_error_type(row) == error_type]
        err_total = len(rows)
        err_successes = sum(1 for row in rows if is_correct(row, mode, text_metric))
        err_low, err_high = wilson_ci(err_successes, err_total)
        by_error_type[error_type] = {
            "records": err_total,
            "successes": err_successes,
            "rate": err_successes / err_total if err_total else 0.0,
            "wilson_95_ci": [err_low, err_high],
        }
    summary = {
        "run": name,
        "records": total,
        "successes": successes,
        "rate": successes / total if total else 0.0,
        "wilson_95_ci": [ci_low, ci_high],
        "by_error_type": by_error_type,
    }
    if mode == "execution" and metrics:
        status_counter = Counter(row["prediction_eval"]["final_status"] for row in outputs.values())
        summary.update(
            {
                "accepted": successes,
                "pass_at_1": metrics.get("pass_at_1", summary["rate"]),
                "status_counts": dict(status_counter),
                "target_pass_at_1": metrics.get("target_pass_at_1"),
            }
        )
    return summary


def main() -> None:
    args = parse_args()
    runs = {}
    summaries = []
    for item in args.runs:
        name, raw_dir = item.split("=", 1)
        run_dir = Path(raw_dir)
        if args.mode == "execution":
            metrics = load_json(run_dir / "eval_metrics.json")
            outputs = load_outputs(run_dir / "eval_outputs.jsonl")
        else:
            metrics = load_json(run_dir / "generation_metrics.json") if (run_dir / "generation_metrics.json").exists() else None
            outputs = load_outputs(run_dir / "generation_eval.jsonl")
        runs[name] = {"metrics": metrics, "outputs": outputs}
        summaries.append(summarize_outputs(name, outputs, args.mode, args.text_metric, metrics))

    names = list(runs)
    paired = {}
    paired_by_error_type = {}
    for i, first in enumerate(names):
        for second in names[i + 1 :]:
            paired[f"{first}_vs_{second}"] = mcnemar_exact(
                runs[first]["outputs"],
                runs[second]["outputs"],
                args.mode,
                args.text_metric,
            )
            error_types = sorted(
                {row_error_type(row) for row in runs[first]["outputs"].values()}
                & {row_error_type(row) for row in runs[second]["outputs"].values()}
            )
            paired_by_error_type[f"{first}_vs_{second}"] = {
                error_type: mcnemar_exact(
                    runs[first]["outputs"],
                    runs[second]["outputs"],
                    args.mode,
                    args.text_metric,
                    error_type,
                )
                for error_type in error_types
            }

    result = {
        "mode": args.mode,
        "text_metric": args.text_metric if args.mode == "text" else None,
        "summaries": summaries,
        "paired_tests": paired,
        "paired_tests_by_error_type": paired_by_error_type,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
