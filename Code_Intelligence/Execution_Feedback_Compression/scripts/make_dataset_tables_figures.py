"""Create LaTeX tables and publication figures for sampled repair corpora."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path(".matplotlib_cache").resolve()))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ERROR_ORDER = ["WA", "CE", "RE", "TLE", "MLE"]


def load_rows(sample_dir: Path, split: str) -> list[dict]:
    rows = []
    with (sample_dir / f"{split}.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def latex_table(caption: str, label: str, headers: list[str], rows: list[list[str]], star: bool = False) -> str:
    cols = "l" + "r" * (len(headers) - 1)
    body = "\n".join(" & ".join(row) + r" \\" for row in rows)
    env = "table*" if star else "table"
    return (
        f"\\begin{{{env}}}[t]\n"
        "\\centering\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{{label}}}\n"
        f"\\begin{{tabular}}{{{cols}}}\n"
        "\\toprule\n"
        + " & ".join(headers)
        + r" \\"
        + "\n\\midrule\n"
        + body
        + "\n\\bottomrule\n"
        "\\end{tabular}\n"
        f"\\end{{{env}}}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = args.output_dir / "tables"
    figures_dir = args.output_dir / "figures"
    tables_dir.mkdir(exist_ok=True)
    figures_dir.mkdir(exist_ok=True)

    splits = {split: load_rows(args.sample_dir, split) for split in ["train", "validation", "test"]}
    all_rows = [row for rows in splits.values() for row in rows]
    languages = sorted({row["language"] for row in all_rows})

    split_rows = []
    for split, rows in splits.items():
        split_rows.append([split.title(), f"{len(rows):,}", f"{len({row['problem_id'] for row in rows}):,}"])
    split_rows.append(["Total", f"{len(all_rows):,}", f"{len({row['problem_id'] for row in all_rows}):,}"])
    (tables_dir / "dataset_splits.tex").write_text(
        latex_table("Large-scale corpus by problem-level split.", "tab:dataset-splits", ["Split", "Records", "Problems"], split_rows),
        encoding="utf-8",
    )

    lang_error = Counter((row["language"], row["error_type"]) for row in all_rows)
    matrix_rows = []
    for language in languages:
        counts = [lang_error[(language, error)] for error in ERROR_ORDER]
        matrix_rows.append([language, *[f"{value:,}" for value in counts], f"{sum(counts):,}"])
    totals = [sum(lang_error[(language, error)] for language in languages) for error in ERROR_ORDER]
    matrix_rows.append(["Total", *[f"{value:,}" for value in totals], f"{sum(totals):,}"])
    (tables_dir / "language_error_matrix.tex").write_text(
        latex_table(
            "Large-scale corpus by language and error type.",
            "tab:language-error-matrix",
            ["Language", *ERROR_ORDER, "Total"],
            matrix_rows,
            star=True,
        ),
        encoding="utf-8",
    )

    split_error_rows = []
    for split, rows in splits.items():
        counts = Counter(row["error_type"] for row in rows)
        split_error_rows.append([split.title(), *[f"{counts[error]:,}" for error in ERROR_ORDER], f"{len(rows):,}"])
    (tables_dir / "split_error_matrix.tex").write_text(
        latex_table(
            "Error-type distribution across problem-level splits.",
            "tab:split-error-matrix",
            ["Split", *ERROR_ORDER, "Total"],
            split_error_rows,
            star=True,
        ),
        encoding="utf-8",
    )

    plt.figure(figsize=(7.2, 3.8))
    bottoms = [0] * len(languages)
    for error in ERROR_ORDER:
        values = [lang_error[(language, error)] for language in languages]
        plt.bar(languages, values, bottom=bottoms, label=error)
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]
    plt.ylabel("Records")
    plt.xlabel("Language")
    plt.legend(ncol=5, fontsize=8, frameon=False)
    plt.tight_layout()
    plt.savefig(figures_dir / "language_error_stacked_bar.pdf")
    plt.savefig(figures_dir / "language_error_stacked_bar.png", dpi=250)
    plt.close()

    error_totals = Counter(row["error_type"] for row in all_rows)
    plt.figure(figsize=(6.8, 3.5))
    plt.bar(ERROR_ORDER, [error_totals[error] for error in ERROR_ORDER], color=["#4c78a8", "#f58518", "#54a24b", "#b279a2", "#e45756"])
    plt.ylabel("Records")
    plt.xlabel("Error type")
    plt.tight_layout()
    plt.savefig(figures_dir / "error_type_distribution.pdf")
    plt.savefig(figures_dir / "error_type_distribution.png", dpi=250)
    plt.close()

    fig, ax = plt.subplots(figsize=(11.0, 3.8))
    ax.axis("off")
    boxes = {
        "raw": (0.03, 0.58, "CodeNet-derived\nbug-fix pairs"),
        "sample": (0.20, 0.58, "Balanced sampling\nlanguage x error"),
        "split": (0.38, 0.58, "Problem-level\ntrain/val/test"),
        "feedback": (0.56, 0.58, "Feedback\nnormalization"),
        "full": (0.74, 0.72, "Full-program\nrepair target"),
        "patch": (0.74, 0.42, "Line-patch\nrepair target"),
        "models": (0.88, 0.58, "Models, evaluation,\npaired statistics"),
    }
    for key, (x, y, text) in boxes.items():
        box = FancyBboxPatch(
            (x, y),
            0.12,
            0.17,
            boxstyle="round,pad=0.02,rounding_size=0.018",
            linewidth=1.2,
            edgecolor="#263238",
            facecolor="#f8fafc",
            transform=ax.transAxes,
        )
        ax.add_patch(box)
        ax.text(x + 0.06, y + 0.085, text, ha="center", va="center", fontsize=9, transform=ax.transAxes)

    def arrow(start: str, end: str) -> None:
        sx, sy, _ = boxes[start]
        ex, ey, _ = boxes[end]
        patch = FancyArrowPatch(
            (sx + 0.12, sy + 0.085),
            (ex, ey + 0.085),
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.1,
            color="#263238",
            transform=ax.transAxes,
        )
        ax.add_patch(patch)

    for start, end in [("raw", "sample"), ("sample", "split"), ("split", "feedback"), ("feedback", "full"), ("feedback", "patch"), ("full", "models"), ("patch", "models")]:
        arrow(start, end)
    ax.text(
        0.5,
        0.16,
        "Final reporting is stratified by WA, CE, RE, TLE, and MLE for every repair target and feedback condition.",
        ha="center",
        va="center",
        fontsize=9,
        transform=ax.transAxes,
    )
    plt.tight_layout()
    plt.savefig(figures_dir / "experimental_pipeline.pdf")
    plt.savefig(figures_dir / "experimental_pipeline.png", dpi=250)
    plt.close()

    summary = {
        "records": len(all_rows),
        "problems": len({row["problem_id"] for row in all_rows}),
        "languages": languages,
        "error_types": ERROR_ORDER,
        "by_error_type": dict(error_totals),
        "by_language_error_type": {f"{language}::{error}": lang_error[(language, error)] for language in languages for error in ERROR_ORDER},
    }
    (args.output_dir / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
