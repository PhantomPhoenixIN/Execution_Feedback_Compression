"""Execute Python bug records and generate feedback-compression variants.

This is the first reproducible pipeline for the project. It does not repair
programs yet; it creates the feedback artifacts that later repair models will
consume.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PYTHON_EXE = Path.home() / "AppData/Local/Programs/Python/Python312/python.exe"

DANGEROUS_PATTERNS = [
    r"\bos\.system\b",
    r"\bsubprocess\b",
    r"\bsocket\b",
    r"\brequests\b",
    r"\burllib\b",
    r"\bshutil\.rmtree\b",
    r"\bopen\s*\(",
    r"\bPath\s*\(",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--python", type=Path, default=PYTHON_EXE)
    return parser.parse_args()


def normalize_output(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def is_potentially_unsafe(code: str) -> tuple[bool, str]:
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, code):
            return True, pattern
    return False, ""


def iter_tests(test_cases: object) -> list[dict]:
    if isinstance(test_cases, dict):
        tests = []
        for name, value in sorted(test_cases.items()):
            if isinstance(value, dict) and "input" in value and "output" in value:
                tests.append(
                    {
                        "name": name,
                        "input": str(value.get("input", "")),
                        "output": str(value.get("output", "")),
                        "suspicious": bool(value.get("suspicious", False)),
                    }
                )
        return tests
    if isinstance(test_cases, list):
        tests = []
        for i, value in enumerate(test_cases):
            if isinstance(value, dict) and "input" in value and "output" in value:
                tests.append(
                    {
                        "name": f"TestCase_{i + 1}",
                        "input": str(value.get("input", "")),
                        "output": str(value.get("output", "")),
                        "suspicious": bool(value.get("suspicious", False)),
                    }
                )
        return tests
    return []


def run_code(code: str, stdin: str, timeout: float, python_exe: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="efc_py_") as tmp:
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
            elapsed = time.perf_counter() - start
            return {
                "timeout": False,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "elapsed_seconds": elapsed,
            }
        except subprocess.TimeoutExpired as exc:
            elapsed = time.perf_counter() - start
            return {
                "timeout": True,
                "returncode": None,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "elapsed_seconds": elapsed,
            }


def traceback_error_class(stderr: str) -> str:
    matches = re.findall(r"^([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):", stderr, re.M)
    if matches:
        return matches[-1]
    if "Traceback (most recent call last)" in stderr:
        return "PythonException"
    return ""


def traceback_line(stderr: str) -> int | None:
    matches = re.findall(r'File ".*?Main\.py", line (\d+)', stderr)
    if not matches:
        return None
    return int(matches[-1])


def code_context(code: str, line_number: int | None, radius: int = 2) -> list[str]:
    if line_number is None:
        return []
    lines = code.splitlines()
    start = max(1, line_number - radius)
    end = min(len(lines), line_number + radius)
    return [f"{idx}: {lines[idx - 1]}" for idx in range(start, end + 1)]


def classify_test(run: dict, expected: str) -> tuple[str, str]:
    if run["timeout"]:
        return "Time Limit Exceeded", "timeout"
    if run["returncode"] != 0:
        return "Runtime Error", traceback_error_class(run.get("stderr", "")) or "nonzero_exit"
    if normalize_output(run.get("stdout", "")) == normalize_output(expected):
        return "Accepted", "accepted"
    return "Wrong Answer", "output_mismatch"


def raw_feedback(status: str, detail: str, run: dict, expected: str) -> str:
    if status == "Runtime Error":
        return run.get("stderr", "")
    if status == "Time Limit Exceeded":
        return f"Program exceeded time limit after {run['elapsed_seconds']:.3f} seconds."
    if status == "Wrong Answer":
        return (
            "Output mismatch.\n"
            f"Expected:\n{normalize_output(expected)[:1000]}\n"
            f"Actual:\n{normalize_output(run.get('stdout', ''))[:1000]}"
        )
    return "Program passed the test case."


def build_feedback(record: dict, test: dict, status: str, detail: str, run: dict) -> dict:
    code = record.get("buggy_code", "")
    line = traceback_line(run.get("stderr", ""))
    context = code_context(code, line)
    raw = raw_feedback(status, detail, run, test["output"])
    structured = {
        "feedback_status": status,
        "detail": detail,
        "line": line,
        "test_name": test["name"],
        "elapsed_seconds": round(float(run.get("elapsed_seconds", 0.0)), 6),
        "expected_preview": normalize_output(test["output"])[:300],
        "actual_preview": normalize_output(run.get("stdout", ""))[:300],
        "stderr_preview": run.get("stderr", "")[:500],
    }
    if status == "Runtime Error" and line:
        natural = f"The program raises {detail} near line {line}."
    elif status == "Time Limit Exceeded":
        natural = "The program did not finish within the time limit."
    elif status == "Wrong Answer":
        natural = "The program finishes, but its output does not match the expected answer."
    else:
        natural = "The program passes this test case."

    return {
        "none": "",
        "raw": raw,
        "categorical": f"{status}: {detail}",
        "localized": "\n".join([f"{status}: {detail}", *context]).strip(),
        "structured": structured,
        "natural_language": natural,
    }


def process_record(record: dict, timeout: float, python_exe: Path) -> dict:
    code = record.get("buggy_code", "")
    unsafe, reason = is_potentially_unsafe(code)
    tests = [test for test in iter_tests(record.get("test_cases")) if not test["suspicious"]]
    base = {
        "problem_id": record.get("problem_id"),
        "user_id": record.get("user_id"),
        "language": record.get("language"),
        "buggy_submission_id": record.get("buggy_submission_id"),
        "fixed_submission_id": record.get("fixed_submission_id"),
        "dataset_status_buggy": record.get("status_buggy"),
        "num_tests": len(tests),
        "unsafe_skipped": unsafe,
        "unsafe_reason": reason,
        "test_results": [],
    }
    if unsafe or not tests:
        return base

    for test in tests:
        run = run_code(code, test["input"], timeout, python_exe)
        status, detail = classify_test(run, test["output"])
        result = {
            "test_name": test["name"],
            "observed_status": status,
            "detail": detail,
            "returncode": run["returncode"],
            "elapsed_seconds": round(float(run["elapsed_seconds"]), 6),
            "stdout_chars": len(run.get("stdout", "")),
            "stderr_chars": len(run.get("stderr", "")),
            "feedback": build_feedback(record, test, status, detail, run),
        }
        base["test_results"].append(result)
        if status != "Accepted":
            break
    return base


def summarize(outputs: list[dict]) -> dict:
    record_status = Counter()
    dataset_status = Counter()
    unsafe = 0
    total_tests_run = 0
    for output in outputs:
        dataset_status[output.get("dataset_status_buggy")] += 1
        if output.get("unsafe_skipped"):
            unsafe += 1
            record_status["UnsafeSkipped"] += 1
            continue
        results = output.get("test_results") or []
        total_tests_run += len(results)
        if not results:
            record_status["NoRunnableTests"] += 1
        elif all(result["observed_status"] == "Accepted" for result in results):
            record_status["AcceptedOnSampleTests"] += 1
        else:
            record_status[results[-1]["observed_status"]] += 1
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "records": len(outputs),
        "total_tests_run": total_tests_run,
        "dataset_status": dict(dataset_status),
        "observed_record_status": dict(record_status),
        "unsafe_skipped": unsafe,
    }


def main() -> None:
    args = parse_args()
    outputs = []
    with args.input.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if args.max_records and index > args.max_records:
                break
            record = json.loads(line)
            outputs.append(process_record(record, args.timeout, args.python))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for output in outputs:
            handle.write(json.dumps(output, ensure_ascii=False) + "\n")

    metrics = summarize(outputs)
    args.metrics.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
