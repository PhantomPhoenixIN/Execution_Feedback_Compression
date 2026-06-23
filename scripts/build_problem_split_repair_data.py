"""Build repair datasets from precomputed problem-level train/validation/test splits."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


FORMATS = ["none", "raw", "categorical", "localized", "structured", "natural_language"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-dir", required=True, type=Path, help="Directory containing train/validation/test JSONL samples.")
    parser.add_argument("--feedback-dir", required=True, type=Path, help="Directory containing train/validation/test feedback JSONL files.")
    parser.add_argument("--descriptions", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--builder", choices=["full", "patch"], default="full")
    parser.add_argument("--include-description", action="store_true")
    parser.add_argument("--max-code-chars", type=int, default=5000)
    parser.add_argument("--max-feedback-chars", type=int, default=1200)
    parser.add_argument("--max-patch-chars", type=int, default=2000)
    return parser.parse_args()


def run_builder(args: argparse.Namespace, split: str, temp_dir: Path) -> dict:
    script = "prepare_repair_datasets.py" if args.builder == "full" else "prepare_patch_datasets.py"
    split_out = temp_dir / split
    command = [
        str(Path.home() / "AppData/Local/Programs/Python/Python312/python.exe"),
        str(Path("scripts") / script),
        "--sample",
        str(args.sample_dir / f"{split}.jsonl"),
        "--feedback",
        str(args.feedback_dir / f"{split}.jsonl"),
        "--descriptions",
        str(args.descriptions),
        "--output-dir",
        str(split_out),
        "--split-name",
        split,
        "--max-code-chars",
        str(args.max_code_chars),
        "--max-feedback-chars",
        str(args.max_feedback_chars),
    ]
    if args.include_description:
        command.append("--include-description")
    if args.builder == "patch":
        command.extend(["--max-patch-chars", str(args.max_patch_chars)])
    subprocess.run(command, check=True)
    return json.loads((split_out / "manifest.json").read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = args.output_dir / "_split_parts"
    temp_dir.mkdir(parents=True, exist_ok=True)
    split_manifests = {}

    for split in ["train", "validation", "test"]:
        split_manifests[split] = run_builder(args, split, temp_dir)

    for feedback_format in FORMATS:
        for split in ["train", "validation", "test"]:
            src = temp_dir / split / f"{feedback_format}_{split}.jsonl"
            dst = args.output_dir / f"{feedback_format}_{split}.jsonl"
            shutil.copyfile(src, dst)

    manifest = {
        "builder": args.builder,
        "sample_dir": str(args.sample_dir),
        "feedback_dir": str(args.feedback_dir),
        "include_description": args.include_description,
        "max_code_chars": args.max_code_chars,
        "max_feedback_chars": args.max_feedback_chars,
        "max_patch_chars": args.max_patch_chars if args.builder == "patch" else None,
        "splits": split_manifests,
        "formats": FORMATS,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
