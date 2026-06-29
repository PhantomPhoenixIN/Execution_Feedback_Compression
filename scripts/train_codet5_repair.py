"""Fine-tune CodeT5-small for a feedback-format repair condition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    set_seed,
)


class RepairDataset(Dataset):
    def __init__(self, path: Path, tokenizer, max_source_length: int, max_target_length: int):
        self.rows = [json.loads(line) for line in path.open("r", encoding="utf-8")]
        self.tokenizer = tokenizer
        self.max_source_length = max_source_length
        self.max_target_length = max_target_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict:
        row = self.rows[index]
        model_inputs = self.tokenizer(
            row["input_text"],
            max_length=self.max_source_length,
            truncation=True,
        )
        labels = self.tokenizer(
            text_target=row["target_text"],
            max_length=self.max_target_length,
            truncation=True,
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path)
    parser.add_argument("--test", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", default="Salesforce/codet5-small")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--max-source-length", type=int, default=512)
    parser.add_argument("--max-target-length", type=int, default=512)
    parser.add_argument("--generation-max-length", type=int, default=512)
    parser.add_argument("--num-beams", type=int, default=4)
    parser.add_argument("--repetition-penalty", type=float, default=1.2)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--save-steps", type=int, default=50)
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Training device. 'auto' uses CUDA when the installed PyTorch build exposes it.",
    )
    return parser.parse_args()


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open("r", encoding="utf-8")]


def load_completed_ids(path: Path) -> set[str]:
    completed = set()
    if not path.exists():
        return completed
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("id"):
                completed.add(row["id"])
    return completed


def latest_checkpoint(checkpoint_dir: Path) -> str | None:
    if not checkpoint_dir.exists():
        return None
    checkpoints = []
    for path in checkpoint_dir.glob("checkpoint-*"):
        if not path.is_dir():
            continue
        try:
            step = int(path.name.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            continue
        checkpoints.append((step, path))
    if not checkpoints:
        return None
    return str(max(checkpoints, key=lambda item: item[0])[1])


def write_predictions(
    *,
    model,
    tokenizer,
    test_rows: list[dict],
    output_path: Path,
    max_source_length: int,
    generation_max_length: int,
    num_beams: int,
    repetition_penalty: float,
    overwrite: bool,
) -> None:
    model.eval()
    completed = set() if overwrite else load_completed_ids(output_path)
    mode = "w" if overwrite or not output_path.exists() else "a"
    with output_path.open(mode, encoding="utf-8") as handle:
        for index, row in enumerate(test_rows, start=1):
            if row["id"] in completed:
                continue
            inputs = tokenizer(
                row["input_text"],
                max_length=max_source_length,
                truncation=True,
                return_tensors="pt",
            )
            with torch.no_grad():
                generated = model.generate(
                    **inputs,
                    max_length=generation_max_length,
                    num_beams=num_beams,
                    repetition_penalty=repetition_penalty,
                    early_stopping=True,
                )
            prediction = tokenizer.decode(generated[0], skip_special_tokens=True)
            item = {
                "id": row["id"],
                "problem_id": row["problem_id"],
                "language": row.get("language"),
                "dataset_status": row["dataset_status"],
                "error_type": row.get("error_type"),
                "observed_status": row["observed_status"],
                "detail": row["detail"],
                "prediction": prediction,
                "target_text": row["target_text"],
                "input_chars": len(row["input_text"]),
            }
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            completed.add(row["id"])
            if index % 10 == 0:
                handle.flush()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    set_seed(args.seed)
    use_cpu = args.device == "cpu" or (args.device == "auto" and not torch.cuda.is_available())
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but the installed PyTorch build does not expose CUDA.")

    saved_model_dir = args.output_dir / "model"
    can_reuse_model = saved_model_dir.exists() and (saved_model_dir / "config.json").exists()
    if args.generate_only or (can_reuse_model and not args.overwrite):
        model_source = saved_model_dir
        if not can_reuse_model:
            raise FileNotFoundError(f"Expected saved model at {saved_model_dir}")
    else:
        model_source = args.model

    tokenizer = AutoTokenizer.from_pretrained(str(model_source), local_files_only=args.local_files_only)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_source), local_files_only=args.local_files_only)
    test_rows = load_rows(args.test)

    if args.generate_only or (can_reuse_model and not args.overwrite):
        write_predictions(
            model=model,
            tokenizer=tokenizer,
            test_rows=test_rows,
            output_path=args.output_dir / "predictions.jsonl",
            max_source_length=args.max_source_length,
            generation_max_length=args.generation_max_length,
            num_beams=args.num_beams,
            repetition_penalty=args.repetition_penalty,
            overwrite=args.overwrite,
        )
        metrics = {
            "train_records": None,
            "test_records": len(test_rows),
            "model": str(model_source),
            "seed": args.seed,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "generate_only": args.generate_only,
            "reused_saved_model": can_reuse_model,
        }
        metrics_path = args.output_dir / "train_metrics.json"
        if args.overwrite or not metrics_path.exists():
            metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(json.dumps(metrics, indent=2))
        return

    if args.train is None:
        raise ValueError("--train is required unless --generate-only is set")

    train_dataset = RepairDataset(args.train, tokenizer, args.max_source_length, args.max_target_length)
    eval_dataset = RepairDataset(args.test, tokenizer, args.max_source_length, args.max_target_length)
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(args.output_dir / "checkpoints"),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        num_train_epochs=args.epochs,
        predict_with_generate=True,
        generation_max_length=args.generation_max_length,
        logging_steps=10,
        save_strategy="steps",
        save_steps=args.save_steps,
        save_total_limit=3,
        evaluation_strategy="no",
        report_to=[],
        fp16=False,
        use_cpu=use_cpu,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        data_collator=collator,
    )
    resume_checkpoint = None if args.overwrite else latest_checkpoint(args.output_dir / "checkpoints")
    if resume_checkpoint:
        print(json.dumps({"resuming_from_checkpoint": resume_checkpoint}))
    train_result = trainer.train(resume_from_checkpoint=resume_checkpoint)

    model.save_pretrained(args.output_dir / "model")
    tokenizer.save_pretrained(args.output_dir / "model")

    metrics = {
        "train_loss": train_result.training_loss,
        "train_records": len(train_dataset),
        "test_records": len(eval_dataset),
        "model": args.model,
        "seed": args.seed,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "device": "cpu" if use_cpu else "cuda",
    }
    (args.output_dir / "train_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_predictions(
        model=model,
        tokenizer=tokenizer,
        test_rows=test_rows,
        output_path=args.output_dir / "predictions.jsonl",
        max_source_length=args.max_source_length,
        generation_max_length=args.generation_max_length,
        num_beams=args.num_beams,
        repetition_penalty=args.repetition_penalty,
        overwrite=args.overwrite,
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
