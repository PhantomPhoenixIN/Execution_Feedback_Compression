"""Print reproducible CodeT5 sweep commands from a JSON config."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PYTHON = r"& \"$env:LOCALAPPDATA\Programs\Python\Python312\python.exe\""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("experiments/full_scale_lang_balanced_98k_001/model_runs"), type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    dataset = Path(config["dataset"])
    train_dir = dataset / config["train_subdir"] if config.get("train_subdir") else dataset
    run_prefix = config.get("run_prefix", "codet5_patch")
    for condition in config["feedback_conditions"]:
        run_dir = args.output_dir / f"{run_prefix}_{condition}_e{config['epochs']}_val"
        train = train_dir / f"{condition}_train.jsonl"
        validation = dataset / f"{condition}_validation.jsonl"
        cmd = (
            f"{PYTHON} scripts\\train_codet5_repair.py "
            f"--train {train} "
            f"--test {validation} "
            f"--output-dir {run_dir} "
            f"--model {config['model']} "
            f"--epochs {config['epochs']} "
            f"--batch-size {config['batch_size']} "
            f"--learning-rate {config['learning_rate']} "
            f"--local-files-only "
            f"--num-beams {config['num_beams']} "
            f"--repetition-penalty {config['repetition_penalty']} "
            f"--max-source-length {config['max_source_length']} "
            f"--max-target-length {config['max_target_length']} "
            f"--generation-max-length {config['generation_max_length']} "
            f"--save-steps {config['save_steps']}"
        )
        eval_cmd = (
            f"{PYTHON} scripts\\evaluate_generation_text.py "
            f"--predictions {run_dir / 'predictions.jsonl'} "
            f"--output {run_dir / 'generation_eval.jsonl'} "
            f"--metrics {run_dir / 'generation_metrics.json'}"
        )
        print(f"# {condition}")
        print(cmd)
        print(eval_cmd)
        print()


if __name__ == "__main__":
    main()
