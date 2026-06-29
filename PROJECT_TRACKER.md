# Execution Feedback Compression Project Tracker

This file is the persistent handoff point for the project. Update it whenever an experiment, design decision, dataset change, or manuscript update is made.

## Goal

Complete a strong research project on execution feedback compression for neural program repair, including dataset construction, feedback compression methods, model baselines, evaluation, statistical validation, external benchmark/model analysis, and manuscript updates.

## Current Status

- Project folder created.
- LaTeX manuscript scaffold created and compiled with Tectonic.
- Project CodeNet-derived dataset discovered under `Code_Intelligence/Datasets/Project_CodeNet`.
- Dataset inventory created in `notes/dataset_inventory.md`.
- Manuscript dataset section updated with observed dataset statistics.
- Python short-code pilot is running as the first controlled neural repair study.
- Full-code CodeT5-small baselines are producing very low Pass@1, so the next research pivot is patch/diff-oriented repair plus stronger model baselines.
- Manuscript policy updated: pilot numeric values are internal development evidence only and must not be reported in the paper; paper tables should contain only full-scale study results.
- Full-scale multilingual balanced corpus upgraded to 98,000 records across Python, Java, C++, and C with exactly 24,500 records per language and explicit WA/CE/RE/TLE/MLE error-type strata.
- Full-code and line-patch repair datasets have been generated for six feedback conditions using status/diff-based multilingual feedback.
- Paper artifacts now include generated LaTeX dataset tables, error-distribution figures, and an experimental pipeline block diagram.

## System Constraints

- CPU: Intel Core i7-12700
- RAM: 64 GB
- GPU: NVIDIA RTX A400, 4 GB VRAM, but previously detected with uncertain Windows status
- Practical implication: prioritize dataset engineering, execution-based evaluation, compact models, PEFT/QLoRA where feasible, and API/external-model evaluation when necessary.

## Core Research Hypothesis

Raw execution feedback is verbose and noisy. Compressed feedback representations can preserve repair-relevant information while reducing context length and improving or maintaining repair effectiveness.

## Planned Experimental Layers

1. Dataset pilot
   - Select one language first, likely Java.
   - Sample 1,000-5,000 bug-fix records.
   - Include compile errors, runtime errors, and wrong answers.

2. Feedback generation
   - No feedback
   - Raw feedback
   - Categorical feedback
   - Localized feedback
   - Structured feedback
   - Natural-language compressed feedback

3. Repair generation
   - Start with deterministic or lightweight baselines.
   - Add compact local model prompting/fine-tuning if feasible.
   - Add external model analysis later.

4. Evaluation
   - Compile success
   - Test pass rate / Pass@1
   - Feedback token length
   - Compression ratio
   - Edit distance to accepted fix
   - Performance by error category

5. Statistical validation
   - Multiple random samples/seeds where feasible.
   - Paired tests between feedback variants.
   - Confidence intervals and effect sizes.

6. External validation
   - External benchmark or held-out benchmark slice.
   - External model comparison if available and appropriate.

## Run Log

| Date | Run ID | Action | Outcome |
|---|---|---|---|
| 2026-06-18 | setup-001 | Created project folder, manuscript, references, and README | Complete |
| 2026-06-18 | data-audit-001 | Streamed main CodeNet bug-fix JSONL for counts | 2,223,631 records; 2,156,595 with embedded tests |
| 2026-06-18 | pilot-python-001 | Sampled balanced Python pilot subset | 300 records: 100 each for Runtime Error, Wrong Answer, Time Limit Exceeded |
| 2026-06-18 | feedback-python-001 | Ran Python feedback extraction on pilot subset after installing common scientific packages | 648 test executions; 157 accepted on sample tests, 54 wrong answer, 83 runtime error, 6 timeout |
| 2026-06-19 | q1-review-001 | Added Q1 publication readiness review | Saved in `notes/q1_publication_review.md` |
| 2026-06-20 | pilot-python-short-001 | Sampled shorter Python programs for feasible local neural repair | 600 records: 200 each Runtime Error, Wrong Answer, Time Limit Exceeded; max accepted-code length 1600 chars |
| 2026-06-20 | feedback-python-short-001 | Executed short Python pilot and generated feedback variants | 287 locally failing repair records; train/test split 230/57 |
| 2026-06-20 | codet5-none-e3 | Fine-tuned CodeT5-small on no-feedback full-code repair | Pass@1 2/57 = 0.035; reference targets pass 49/57 = 0.860 |
| 2026-06-20 | codet5-categorical-e3 | Fine-tuned CodeT5-small with categorical feedback | Pass@1 2/57 = 0.035; exact McNemar vs none p=1.0 |
| 2026-06-20 | codet5-raw-e3 | Fine-tuned CodeT5-small with raw feedback | Pass@1 1/57 = 0.018 |
| 2026-06-20 | codet5-localized-e3 | Fine-tuned CodeT5-small with localized feedback | Pass@1 0/57 = 0.000 |
| 2026-06-20 | codet5-structured-e3 | Fine-tuned CodeT5-small with structured feedback | Pass@1 3/57 = 0.053 |
| 2026-06-20 | codet5-natural-language-e3 | Fine-tuned CodeT5-small with natural-language compressed feedback | Pass@1 3/57 = 0.053 |
| 2026-06-20 | stats-aggregate-e3 | Added paired statistical aggregation script | Writes Wilson CIs and exact McNemar tests to `experiments/pilot_python_short_001/repair_aggregate_e3.json` |
| 2026-06-20 | patch-target-builder-001 | Added line-patch target builder and evaluator | 285 usable records; all target patches exactly reconstruct accepted solutions; 2 records skipped for long patches |
| 2026-06-20 | codet5-patch-none-e5 | Fine-tuned CodeT5-small on no-feedback line-patch repair | 55/57 generated patches parse, but Pass@1 0/57 |
| 2026-06-20 | codet5-patch-structured-e5 | Fine-tuned CodeT5-small on structured-feedback line-patch repair | 54/57 generated patches parse, but Pass@1 0/57 |
| 2026-06-20 | qwen-0.5b-download | Downloaded public `Qwen/Qwen2.5-Coder-0.5B-Instruct` for external/local model analysis | Cached locally; CPU inference is slow but feasible on 57-record pilots |
| 2026-06-20 | qwen-full-none-zs | Zero-shot Qwen full-code repair without feedback on no-description split | Pass@1 8/57 = 0.140 |
| 2026-06-20 | qwen-full-feedback-sweep-zs | Zero-shot Qwen full-code repair across all feedback formats on same no-description split | None 8/57; raw/categorical/structured/natural-language 7/57; localized 6/57; no paired feedback condition significantly beats none |
| 2026-06-22 | manuscript-policy-001 | Removed pilot values from `manuscript.tex` | Manuscript now describes full-scale study design and reserves results for large-scale analysis only |
| 2026-06-22 | resume-safety-001 | Made training, generation, and evaluation scripts resume-safe | CodeT5 training resumes from latest checkpoint; prediction/evaluation scripts append missing IDs; use `--overwrite` to intentionally rerun |
| 2026-06-22 | full-scale-sample-001 | Stream-sampled a balanced multilingual subset with problem-level splits | 27,500 records across Python, Java, and C++; train/validation/test contain 22,081/2,537/2,882 records and 1,603/200/201 problems |
| 2026-06-22 | split-audit-001 | Audited problem-level split leakage | Leakage-free; zero overlapping problem IDs across train, validation, and test |
| 2026-06-22 | status-feedback-001 | Generated multilingual status/diff feedback artifacts | Feedback generated for all full-scale train, validation, and test records |
| 2026-06-22 | full-repair-data-001 | Built multilingual full-code repair datasets | Six feedback formats; train/validation/test contain 22,081/2,537/2,882 instances |
| 2026-06-22 | patch-repair-data-001 | Built multilingual line-patch repair datasets | Six feedback formats; train/validation/test contain 21,498/2,476/2,790 instances after excluding empty or overlong patches |
| 2026-06-22 | full-scale-100k-sample-001 | Stream-sampled publication-scale multilingual corpus with normalized error types | 98,236 records across C, C++, Java, and Python; explicit WA/CE/RE/TLE/MLE strata; problem split train/validation/test = 79,178/10,921/8,137 |
| 2026-06-22 | full-scale-100k-audit-001 | Audited 100k-style problem-level splits | Leakage-free; zero overlapping problem IDs across train, validation, and test |
| 2026-06-22 | full-scale-100k-artifacts-001 | Generated paper tables and figures | LaTeX tables plus PDF/PNG plots and pipeline diagram saved under `experiments/full_scale_multilang_100k_001/paper_artifacts` |
| 2026-06-22 | full-scale-100k-feedback-001 | Generated multilingual status/diff feedback artifacts | Feedback generated for 98,236 records |
| 2026-06-22 | full-scale-100k-repair-data-001 | Built full-code and patch repair datasets with `error_type` metadata | Full-code: 79,178/10,921/8,137; patch: 77,171/10,578/7,904 train/validation/test |
| 2026-06-22 | manuscript-100k-update-001 | Updated manuscript for 98k corpus and error-type analyses | Added generated dataset tables, error-distribution figure, pipeline block diagram, and repair-breakdown table scaffold; PDF compiles |
| 2026-06-22 | lang-balanced-98k-sample-001 | Created language-balanced publication corpus | 98,000 records; exactly 24,500 per language across C, C++, Java, and Python; WA/CE/RE/TLE/MLE preserved |
| 2026-06-22 | lang-balanced-98k-audit-001 | Audited language-balanced problem-level split | Leakage-free; train/validation/test contain 80,031/9,517/8,452 records and 1,991/249/249 problems |
| 2026-06-22 | manuscript-no-graphs-001 | Removed graph figures from manuscript | Manuscript now contains tables only; figures can be added after final results |
| 2026-06-22 | lang-balanced-98k-repair-data-001 | Built balanced full-code and line-patch repair datasets | Full-code: 80,031/9,517/8,452; line-patch: 78,069/9,299/8,171 train/validation/test |
| 2026-06-22 | manuscript-feedback-table-001 | Added explicit feedback-representation table and completed repair-breakdown scaffold | Manuscript now shows all six conditions: None, Raw, Categorical, Localized, Structured, Natural Language |
| 2026-06-22 | stats-by-error-001 | Generalized aggregation scripts for execution and text diagnostics | Supports Wilson CIs and exact McNemar tests overall and by WA/CE/RE/TLE/MLE |
| 2026-06-22 | codet5-sweep-config-001 | Added reproducible CodeT5 line-patch feedback sweep config | Saved in `configs/codet5_patch_feedback_sweep_balanced_98k.json`; commands are printed by `scripts/print_codet5_sweep_commands.py` |
| 2026-06-22 | feedback-length-001 | Added feedback length analysis table | Validation feedback lengths saved in `experiments/full_scale_lang_balanced_98k_001/feedback_compression_patch_validation.json`; manuscript compiles with table |
| 2026-06-22 | codet5-patch-none-resume-001 | Started no-feedback CodeT5 line-patch baseline on balanced corpus | CPU run reached step 77 before timeout; latest saved checkpoint is `experiments/full_scale_lang_balanced_98k_001/model_runs/codet5_patch_none_e1_val/checkpoints/checkpoint-70`; rerun resumes from there |
| 2026-06-23 | full98k-run-name-001 | Named the full line-patch CodeT5 sweep | Official run group: `FULL98K_CodeT5_Patch_FeedbackSweep_v1`; condition run folders use `FULL98K_CodeT5_Patch_v1_<condition>_e1_val` |
| 2026-06-23 | full98k-train-policy-001 | Switched CodeT5 sweep config back to full training | Training uses the full line-patch training split of 78,069 instances, not the `balanced_train_500` slice; validation uses all 9,299 instances |
| 2026-06-23 | full98k-local-data-001 | Copied ignored full line-patch JSONL files into flattened repo layout | Full JSONL files exist locally under `experiments/full_scale_lang_balanced_98k_001/repair_patch_status_no_desc` and remain ignored by Git |
| 2026-06-23 | full98k-none-training-001 | Launched full no-feedback CodeT5 line-patch run | Run name `FULL98K_CodeT5_Patch_v1_none_e1_val`; resumed from `checkpoint-70`; background PID recorded in ignored `process.pid`; logs written to ignored `train_stdout.log` and `train_stderr.log` |
| 2026-06-29 | full98k-none-complete-001 | Completed the full no-feedback CodeT5 line-patch run | Validation generation completed for 9,299 records; exact patch match is 5/9,299, confirming this is a difficult low-resource baseline |
| 2026-06-29 | full98k-sweep-runner-001 | Added a resume-safe sequential runner for the remaining feedback conditions | `scripts/run_full98k_codet5_sweep.ps1` skips completed conditions, restarts interrupted ones from checkpoints, and logs sweep progress |
| 2026-06-29 | codet5-device-policy-001 | Made training device explicit and automatic | `scripts/train_codet5_repair.py` now supports `--device auto/cpu/cuda`; current PyTorch install is CPU-only (`torch 2.5.1+cpu`) |

## Decisions

| Date | Decision | Rationale |
|---|---|---|
| 2026-06-18 | Use Project CodeNet-derived bug-fix pairs as primary dataset | Contains real user errors paired with first accepted solution, status labels, diffs, and tests |
| 2026-06-18 | Start with Java or Python pilot | Best balance of diagnostics, execution support, and manageable evaluation |
| 2026-06-18 | Use Python for first pilot | JDK installation failed due certificate/network issue; Python runtime is available and suitable for traceback feedback compression |
| 2026-06-18 | Install `numpy`, `scipy`, `networkx`, `sympy` | Several sampled Python submissions rely on common competitive-programming scientific packages |
| 2026-06-19 | Reframe the work as an empirical study of feedback as an information channel | Stronger Q1 positioning than a simple prompt-format comparison |
| 2026-06-20 | Treat full-code CodeT5-small as a low-resource baseline, not the main contribution | Even on short programs, Pass@1 is 0--3.5%; most predictions fail at runtime, suggesting weak syntax/control-flow preservation |
| 2026-06-20 | Add a patch/diff-oriented repair formulation next | Editing a smaller target is theoretically better aligned with small local models and will support stronger ablations of feedback information |
| 2026-06-20 | Do not assume execution feedback helps by default | Qwen zero-shot no-feedback slightly outperformed structured feedback on the first 57-record split; feedback may need better integration, filtering, or retrieval-aware prompting |
| 2026-06-20 | Separate problem-description effects from feedback effects | Qwen patch prompting copied problem prose when descriptions were included, so no-description splits are needed for clean feedback ablations |
| 2026-06-22 | Do not include pilot values in the final paper | Pilot experiments are useful for engineering and design decisions, but Q1 journal claims should be based on full-scale statistically powered analysis |
| 2026-06-22 | Large-scale scripts must be resume-safe by default | CPU runs are expensive; interrupted work should resume from saved checkpoints or completed record IDs instead of retraining/regenerating from scratch |
| 2026-06-22 | Use problem-level splits for the full-scale study | Prevents the same programming problem from appearing in both training and evaluation, reducing problem-template leakage |
| 2026-06-22 | Use four languages in the publication-scale corpus: C, C++, Java, and Python | Strengthens multilingual scope and provides more CE/MLE coverage while satisfying the at-least-three-language requirement |
| 2026-06-22 | Normalize online-judge labels into WA/CE/RE/TLE/MLE | Makes dataset tables and repair breakdowns reviewer-readable and prevents compilation/runtime errors from being merged |
| 2026-06-22 | Use status/diff feedback for the first multilingual corpus | Java and C++ compiler toolchains are not currently installed; execution-grade Java/C++ feedback will require toolchain setup or containerized execution |

## Resume-Safety Contract

- `scripts/train_codet5_repair.py` saves rolling checkpoints under `<output-dir>/checkpoints/checkpoint-*` every `--save-steps` steps, default 50.
- If training is interrupted before the final model is saved, rerunning the same command resumes from the latest checkpoint automatically.
- If `<output-dir>/model/config.json` already exists, rerunning the same command reuses the saved model and only completes missing predictions.
- `--overwrite` intentionally disables resume behavior and starts fresh.
- `scripts/run_full98k_codet5_sweep.ps1` runs the six feedback conditions sequentially, skips conditions with `generation_metrics.json`, and restarts interrupted conditions from their latest checkpoints.
- Qwen prompting scripts append only missing prediction IDs unless `--overwrite` is passed.
- Full-code and patch evaluation scripts append only missing evaluated IDs and recompute metrics over all accumulated outputs.

## Full-Scale Corpus Snapshot

- Config: `configs/full_scale_language_balanced_config.json`
- Explicit balanced cell targets: `configs/full_scale_language_balanced_targets.json`
- Sample directory: `experiments/full_scale_lang_balanced_98k_001/samples`
- Feedback directory: `experiments/full_scale_lang_balanced_98k_001/feedback_status`
- Full-code repair data: `experiments/full_scale_lang_balanced_98k_001/repair_full_status_no_desc`
- Patch repair data: `experiments/full_scale_lang_balanced_98k_001/repair_patch_status_no_desc`
- Paper artifacts: `experiments/full_scale_lang_balanced_98k_001/paper_artifacts`
- Selected records: 98,000
- Languages: C, C++, Java, Python
- Language balance: exactly 24,500 records per language
- Error types: WA 25,231; CE 17,173; RE 25,229; TLE 25,231; MLE 5,136
- Problem-level split: train 1,991 problems / 80,031 records; validation 249 problems / 9,517 records; test 249 problems / 8,452 records
- Split audit: leakage-free with zero overlapping problem IDs
- Full-code instances: train 80,031; validation 9,517; test 8,452
- Patch instances: train 78,069; validation 9,299; test 8,171
- Manuscript compiles with Tectonic; current PDF: `manuscript.pdf`

## Open Questions

- Should Java and C++ compiler toolchains be installed locally, or should execution-grade multilingual evaluation use a container/CI environment?
- Should natural-language compressed feedback be rule-based first or generated by a small model/API?
- Which external benchmark best matches the study without becoming too heavy?

## Next Immediate Steps

1. Train resume-safe multilingual CodeT5 baselines on full-code and patch targets.
2. Evaluate no-feedback, raw, structured, and natural-language feedback first; add categorical/localized after the main run is stable.
3. Add same-token-budget raw truncation baseline.
4. Add statistical aggregation over paired full-scale predictions.
5. Add external benchmark/model analysis.
6. Continue updating `manuscript.tex` with large-scale results only.

## Current Immediate Tasks

1. Run raw/categorical/localized/structured/natural-language line-patch baselines using the sequential full-sweep runner.
2. Aggregate full validation metrics across the six feedback conditions.
3. Decide whether the very low exact-match baseline requires a smaller edit-target variant, execution-based validation, or a stronger model before paper-facing claims.
4. Add external benchmark analysis, preferably QuixBugs Python, for a recognizable validation set.
