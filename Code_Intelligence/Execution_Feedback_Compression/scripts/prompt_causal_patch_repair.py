"""Prompt an instruction-tuned causal code model to generate line patches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-source-chars", type=int, default=5000)
    parser.add_argument("--max-new-tokens", type=int, default=220)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--repetition-penalty", type=float, default=1.15)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def load_rows(path: Path, limit: int | None) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


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


def build_prompt(row: dict, max_source_chars: int) -> list[dict]:
    content = row["input_text"][:max_source_chars]
    return [
        {
            "role": "system",
            "content": (
                "You repair Python programming-contest submissions. "
                "Return only a line patch. The hunk header is one line: "
                "@@ replace START END. Then write replacement Python code lines. "
                "Then close the hunk with one line: @@ end. "
                "Line numbers are zero-based and END is exclusive."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{content}\n\n"
                "Generate the smallest correct patch. Return no explanation."
            ),
        },
    ]


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=args.local_files_only, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        local_files_only=args.local_files_only,
        trust_remote_code=True,
        torch_dtype=torch.float32,
        device_map=None,
    )
    model.eval()

    rows = load_rows(args.test, args.limit)
    completed = set() if args.overwrite else load_completed_ids(args.output)
    mode = "w" if args.overwrite or not args.output.exists() else "a"
    with args.output.open(mode, encoding="utf-8") as handle:
        for index, row in enumerate(rows, start=1):
            if row["id"] in completed:
                continue
            messages = build_prompt(row, args.max_source_chars)
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(text, return_tensors="pt")
            with torch.no_grad():
                generated = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=args.temperature > 0,
                    temperature=args.temperature if args.temperature > 0 else None,
                    repetition_penalty=args.repetition_penalty,
                    pad_token_id=tokenizer.eos_token_id,
                )
            new_tokens = generated[0][inputs["input_ids"].shape[-1] :]
            prediction = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
            item = {
                "id": row["id"],
                "problem_id": row["problem_id"],
                "dataset_status": row["dataset_status"],
                "observed_status": row["observed_status"],
                "detail": row["detail"],
                "prediction": prediction,
                "target_text": row["target_text"],
                "input_chars": len(row["input_text"]),
                "prompt_model": args.model,
                "row_index": index,
            }
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            handle.flush()
            completed.add(row["id"])
            print(json.dumps({"generated": index, "id": row["id"]}))


if __name__ == "__main__":
    main()
