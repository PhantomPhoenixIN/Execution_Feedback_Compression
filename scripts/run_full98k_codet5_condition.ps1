param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("none", "raw", "categorical", "localized", "structured", "natural_language")]
    [string]$Condition
)

$ErrorActionPreference = "Stop"

$Python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$Dataset = "experiments\full_scale_lang_balanced_98k_001\repair_patch_status_no_desc"
$RunDir = "experiments\full_scale_lang_balanced_98k_001\model_runs\FULL98K_CodeT5_Patch_v1_${Condition}_e1_val"

& $Python scripts\train_codet5_repair.py `
    --train "$Dataset\${Condition}_train.jsonl" `
    --test "$Dataset\${Condition}_validation.jsonl" `
    --output-dir $RunDir `
    --model Salesforce/codet5-small `
    --epochs 1 `
    --batch-size 4 `
    --learning-rate 5e-5 `
    --local-files-only `
    --num-beams 4 `
    --repetition-penalty 1.2 `
    --max-source-length 512 `
    --max-target-length 256 `
    --generation-max-length 256 `
    --save-steps 100

& $Python scripts\evaluate_generation_text.py `
    --predictions "$RunDir\predictions.jsonl" `
    --output "$RunDir\generation_eval.jsonl" `
    --metrics "$RunDir\generation_metrics.json"
