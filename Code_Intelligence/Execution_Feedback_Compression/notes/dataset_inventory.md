# Dataset Inventory

Dataset location:

`F:\Deepak_Research\Code_Intelligence\Datasets\Project_CodeNet`

Files:

- `final_codenet_bugfix_pairs_alllangs_with_diffs.jsonl`
- `problem_tests.json`
- `problem_description_en.jsonl`

## Main JSONL Schema

Observed fields include:

- `problem_id`
- `user_id`
- `language`
- `buggy_submission_id`
- `fixed_submission_id`
- `status_buggy`
- `status_fixed`
- `buggy_code`
- `fixed_code`
- `test_cases`
- `diffs`
- `_diff_summary`

Each record pairs a user error submission with the user's first accepted solution for the same problem trajectory.

## Streamed Statistics

Computed on 2026-06-18 by streaming `final_codenet_bugfix_pairs_alllangs_with_diffs.jsonl`.

- Total bug-fix records: 2,223,631
- Records with embedded test cases: 2,156,595

Top languages:

| Language | Records |
|---|---:|
| C++ | 1,293,708 |
| Python | 510,007 |
| C | 130,164 |
| Java | 123,534 |
| C# | 37,845 |
| Ruby | 36,697 |
| Rust | 17,646 |
| Go | 14,203 |
| JavaScript | 9,249 |
| Haskell | 7,304 |
| Kotlin | 7,009 |
| PHP | 6,490 |

Buggy status distribution:

| Status | Records |
|---|---:|
| Wrong Answer | 1,484,958 |
| Runtime Error | 291,601 |
| Time Limit Exceeded | 230,856 |
| Compile Error | 181,255 |
| WA: Presentation Error | 27,294 |
| Memory Limit Exceeded | 7,229 |
| Output Limit Exceeded | 315 |

Diff operation counts:

| Operation | Count |
|---|---:|
| replace | 5,838,360 |
| insert | 1,264,680 |
| delete | 885,073 |

## Usefulness for Execution Feedback Compression

This dataset is highly suitable for the project because it already provides:

- buggy code,
- accepted repair target,
- execution/error status labels,
- language metadata,
- code diffs,
- problem-level tests for most records,
- problem descriptions in a separate metadata file.

The strongest pilot subset is likely Java or Python. Java is useful for compiler diagnostics and structured feedback extraction. Python is useful for runtime tracebacks and exception compression. C++ has the largest scale but requires more careful sandboxing and compiler-output normalization.

## Recommended Pilot

Start with Java compile errors and runtime errors:

- language: Java
- statuses: `Compile Error`, `Runtime Error`, `Wrong Answer`
- sample size: 1,000 to 5,000 records
- feedback variants: none, raw, categorical, localized, structured, natural-language compressed

This gives a clean first experiment without processing the entire 7.8 GB JSONL repeatedly.
