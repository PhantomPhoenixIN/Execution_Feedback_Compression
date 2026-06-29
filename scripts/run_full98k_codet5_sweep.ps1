param(
    [string[]]$Conditions = @("none", "raw", "categorical", "localized", "structured", "natural_language"),
    [int]$PollSeconds = 300
)

$ErrorActionPreference = "Stop"

$SweepLog = "experiments\full_scale_lang_balanced_98k_001\model_runs\FULL98K_CodeT5_Patch_v1_sweep.log"
$Runner = "scripts\run_full98k_codet5_condition.ps1"

function Write-SweepLog {
    param([string]$Message)
    $Stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Line = "$Stamp $Message"
    $Line | Tee-Object -FilePath $SweepLog -Append
}

function Get-RunDir {
    param([string]$Condition)
    return "experiments\full_scale_lang_balanced_98k_001\model_runs\FULL98K_CodeT5_Patch_v1_${Condition}_e1_val"
}

function Get-LatestCheckpoint {
    param([string]$RunDir)
    $CheckpointDir = Join-Path $RunDir "checkpoints"
    if (!(Test-Path $CheckpointDir)) {
        return "none"
    }
    $Latest = Get-ChildItem $CheckpointDir -Directory |
        Where-Object { $_.Name -match '^checkpoint-\d+$' } |
        Sort-Object { [int]($_.Name -replace 'checkpoint-', '') } -Descending |
        Select-Object -First 1
    if ($Latest) {
        return $Latest.Name
    }
    return "none"
}

New-Item -ItemType Directory -Force (Split-Path $SweepLog) | Out-Null
Write-SweepLog "sweep_started conditions=$($Conditions -join ',') poll_seconds=$PollSeconds"

foreach ($Condition in $Conditions) {
    $RunDir = Get-RunDir $Condition
    $Metrics = Join-Path $RunDir "generation_metrics.json"
    $Stdout = Join-Path $RunDir "train_stdout.log"
    $Stderr = Join-Path $RunDir "train_stderr.log"
    $PidFile = Join-Path $RunDir "process.pid"

    New-Item -ItemType Directory -Force $RunDir | Out-Null
    if (Test-Path $Metrics) {
        Write-SweepLog "condition_skipped condition=$Condition reason=metrics_present"
        continue
    }

    Write-SweepLog "condition_started condition=$Condition latest_checkpoint=$(Get-LatestCheckpoint $RunDir)"
    $Proc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $Runner, "-Condition", $Condition `
        -WorkingDirectory (Get-Location) `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -WindowStyle Hidden `
        -PassThru
    $Proc.Id | Set-Content $PidFile

    while ($true) {
        Start-Sleep -Seconds $PollSeconds
        $Current = Get-Process -Id $Proc.Id -ErrorAction SilentlyContinue
        $Checkpoint = Get-LatestCheckpoint $RunDir
        if ($Current) {
            Write-SweepLog "condition_running condition=$Condition pid=$($Proc.Id) cpu=$([math]::Round($Current.CPU, 2)) latest_checkpoint=$Checkpoint"
            continue
        }

        if (Test-Path $Metrics) {
            Write-SweepLog "condition_completed condition=$Condition latest_checkpoint=$Checkpoint"
            break
        }

        Write-SweepLog "condition_restarting condition=$Condition previous_pid=$($Proc.Id) latest_checkpoint=$Checkpoint"
        $Proc = Start-Process -FilePath "powershell.exe" `
            -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $Runner, "-Condition", $Condition `
            -WorkingDirectory (Get-Location) `
            -RedirectStandardOutput $Stdout `
            -RedirectStandardError $Stderr `
            -WindowStyle Hidden `
            -PassThru
        $Proc.Id | Set-Content $PidFile
    }
}

Write-SweepLog "sweep_completed"
