param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("none", "raw", "categorical", "localized", "structured", "natural_language")]
    [string]$Condition,

    [int]$IntervalMinutes = 10
)

$ErrorActionPreference = "Stop"

$RunDir = "experiments\full_scale_lang_balanced_98k_001\model_runs\FULL98K_CodeT5_Patch_v1_${Condition}_e1_val"
$PidFile = Join-Path $RunDir "process.pid"
$MonitorLog = Join-Path $RunDir "supervisor.log"
$ModelConfig = Join-Path $RunDir "model\config.json"
$Runner = "scripts\run_full98k_codet5_condition.ps1"

function Write-Log {
    param([string]$Message)
    $Stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Stamp $Message" | Tee-Object -FilePath $MonitorLog -Append
}

function Get-LatestCheckpoint {
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

function Get-RunProcess {
    if (!(Test-Path $PidFile)) {
        return $null
    }
    $RunPid = [int](Get-Content $PidFile)
    return Get-Process -Id $RunPid -ErrorAction SilentlyContinue
}

function Start-Training {
    New-Item -ItemType Directory -Force $RunDir | Out-Null
    $Stdout = Join-Path $RunDir "train_stdout.log"
    $Stderr = Join-Path $RunDir "train_stderr.log"
    $Proc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $Runner, "-Condition", $Condition `
        -WorkingDirectory (Get-Location) `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -WindowStyle Hidden `
        -PassThru
    $Proc.Id | Set-Content $PidFile
    Write-Log "restarted pid=$($Proc.Id) latest_checkpoint=$(Get-LatestCheckpoint)"
}

New-Item -ItemType Directory -Force $RunDir | Out-Null
Write-Log "supervisor_started condition=$Condition interval_minutes=$IntervalMinutes"

while ($true) {
    $LatestCheckpoint = Get-LatestCheckpoint
    if (Test-Path $ModelConfig) {
        Write-Log "completed model_config_present latest_checkpoint=$LatestCheckpoint"
        break
    }

    $Proc = Get-RunProcess
    if ($Proc) {
        Write-Log "running pid=$($Proc.Id) cpu=$([math]::Round($Proc.CPU, 2)) latest_checkpoint=$LatestCheckpoint"
    } else {
        Write-Log "not_running latest_checkpoint=$LatestCheckpoint action=restart"
        Start-Training
    }

    Start-Sleep -Seconds ($IntervalMinutes * 60)
}
