"""Evaluate generated Python repairs against embedded tests."""

from __future__ import annotations

import argparse
import json
import tempfile
import subprocess
import time
from collections import Counter
from pathlib import Path


PYTHON_EXE = Path.home() / "AppData/Local/Programs/Python/Python312/python.exe"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--python", type=Path, default=PYTHON_EXE)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def normalize_output(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def iter_tests(test_cases: object) -> list[dict]:
    if isinstance(test_cases, dict):
        return [
            {
                "name": name,
                "input": str(value.get("input", "")),
                "output": str(value.get("output", "")),
                "suspicious": bool(value.get("suspicious", False)),
            }
            for name, value in sorted(test_cases.items())
            if isinstance(value, dict) and "input" in value and "output" in value
        ]
    return []


def run_code(code: str, stdin: str, timeout: float, python_exe: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="efc_eval_") as tmp:
        script = Path(tmp) / "Main.py"
        script.write_text(code, encoding="utf-8", errors="replace")
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [str(python_exe), "-I", str(script)],
                input=stdin,
                text=True,
                capture_output=True,
                timeout=timeout,
                cwd=tmp,
            )
            return {
                "timeout": False,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "elapsed_seconds": time.perf_counter() - start,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "timeout": True,
                "returncode": None,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "elapsed_seconds": time.perf_counter() - start,
            }


def classify(run: dict, expected: str) -> str:
    if run["timeout"]:
        return "Time Limit Exceeded"
    if run["returncode"] != 0:
        return "Runtime Error"
    if normalize_output(run.get("stdout", "")) == normalize_output(expected):
        return "Accepted"
    return "Wrong Answer"


def evaluate_code(code: str, tests: list[dict], timeout: float, python_exe: Path) -> dict:
    statuses = []
    for test in tests:
        if test.get("suspicious"):
            continue
        run = run_code(code, test["input"], timeout, python_exe)
        status = classify(run, test["output"])
        statuses.append(
            {
                "test_name": test["name"],
                "status": status,
                "elapsed_seconds": round(float(run["elapsed_seconds"]), 6),
                "stderr_preview": run.get("stderr", "")[:300],
                "stdout_preview": run.get("stdout", "")[:300],
            }
        )
        if status != "Accepted":
            break
    final = "Accepted" if statuses and all(item["status"] == "Accepted" for item in statuses) else (
        statuses[-1]["status"] if statuses else "NoRunnableTests"
    )
    return {"final_status": final, "test_results": statuses}


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
    mode = "w" if args.overwrite or not args.output.exists() else "a"
    out_handle = args.output.open(mode, encoding="utf-8")
    with args.predictions.open("r", encoding="utf-8") as handle:
        for line in handle:
            pred = json.loads(line)
            if pred["id"] in outputs_by_id:
                continue
            source = sample[pred["id"]]
            tests = iter_tests(source.get("test_cases"))
            repair_eval = evaluate_code(pred["prediction"], tests, args.timeout, args.python)
            target_eval = evaluate_code(pred["target_text"], tests, args.timeout, args.python)
            item = {
                **pred,
                "prediction_eval": repair_eval,
                "target_eval": target_eval,
                "prediction_chars": len(pred["prediction"]),
                "target_chars": len(pred["target_text"]),
            }
            outputs_by_id[pred["id"]] = item
            out_handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            out_handle.flush()
    out_handle.close()

    for item in outputs_by_id.values():
        counters[item["prediction_eval"]["final_status"]] += 1
        target_counters[item["target_eval"]["final_status"]] += 1

    total = len(outputs_by_id)
    metrics = {
        "records": total,
        "prediction_status": dict(counters),
        "target_status": dict(target_counters),
        "pass_at_1": counters["Accepted"] / total if total else 0.0,
        "target_pass_at_1": target_counters["Accepted"] / total if total else 0.0,
    }
    args.metrics.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
