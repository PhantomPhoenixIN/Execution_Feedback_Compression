"""Evaluate generated line patches by applying them to buggy Python code."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from evaluate_predictions import evaluate_code, iter_tests
from patch_utils import PatchError, apply_patch_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--python", type=Path, default=Path.home() / "AppData/Local/Programs/Python/Python312/python.exe")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def load_existing_outputs(path: Path) -> dict[str, dict]:
    rows = {}
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("id"):
                rows[row["id"]] = row
    return rows


def main() -> None:
    args = parse_args()
    sample = {}
    with args.sample.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            sample[row["buggy_submission_id"]] = row

    outputs_by_id = {} if args.overwrite else load_existing_outputs(args.output)
    counters = Counter()
    target_counters = Counter()
    parse_counters = Counter()
    mode = "w" if args.overwrite or not args.output.exists() else "a"
    out_handle = args.output.open(mode, encoding="utf-8")
    with args.predictions.open("r", encoding="utf-8") as handle:
        for line in handle:
            pred = json.loads(line)
            if pred["id"] in outputs_by_id:
                continue
            source = sample[pred["id"]]
            tests = iter_tests(source.get("test_cases"))
            try:
                repaired = apply_patch_text(source["buggy_code"], pred["prediction"])
                repair_eval = evaluate_code(repaired, tests, args.timeout, args.python)
            except PatchError as exc:
                repaired = ""
                repair_eval = {"final_status": "InvalidPatch", "error": str(exc), "test_results": []}

            try:
                target_repaired = apply_patch_text(source["buggy_code"], pred["target_text"])
                target_eval = evaluate_code(target_repaired, tests, args.timeout, args.python)
            except PatchError as exc:
                target_repaired = ""
                target_eval = {"final_status": "InvalidPatch", "error": str(exc), "test_results": []}

            item = {
                **pred,
                "prediction_eval": repair_eval,
                "target_eval": target_eval,
                "prediction_chars": len(pred["prediction"]),
                "target_chars": len(pred["target_text"]),
                "repaired_code_preview": repaired[:1000],
                "target_repaired_code_preview": target_repaired[:1000],
            }
            outputs_by_id[pred["id"]] = item
            out_handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            out_handle.flush()
    out_handle.close()

    for item in outputs_by_id.values():
        counters[item["prediction_eval"]["final_status"]] += 1
        target_counters[item["target_eval"]["final_status"]] += 1
        if item["prediction_eval"]["final_status"] == "InvalidPatch":
            parse_counters["prediction_patch_invalid"] += 1
        else:
            parse_counters["prediction_patch_valid"] += 1
        if item["target_eval"]["final_status"] == "InvalidPatch":
            parse_counters["target_patch_invalid"] += 1
        else:
            parse_counters["target_patch_valid"] += 1

    total = len(outputs_by_id)
    metrics = {
        "records": total,
        "prediction_status": dict(counters),
        "target_status": dict(target_counters),
        "patch_parse": dict(parse_counters),
        "pass_at_1": counters["Accepted"] / total if total else 0.0,
        "target_pass_at_1": target_counters["Accepted"] / total if total else 0.0,
    }
    args.metrics.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
