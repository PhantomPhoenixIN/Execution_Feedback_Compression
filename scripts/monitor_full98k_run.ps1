param(
    [Parameter(Mandatory = $true)]
    [string]$Condition
)

$RunDir = "experiments\full_scale_lang_balanced_98k_001\model_runs\FULL98K_CodeT5_Patch_v1_${Condition}_e1_val"
$PidFile = Join-Path $RunDir "process.pid"
$Stdout = Join-Path $RunDir "train_stdout.log"
$Stderr = Join-Path $RunDir "train_stderr.log"
$Checkpoints = Join-Path $RunDir "checkpoints"

Write-Output "Run directory: $RunDir"

if (Test-Path $PidFile) {
    $RunPid = [int](Get-Content $PidFile)
    $Process = Get-Process -Id $RunPid -ErrorAction SilentlyContinue
    if ($Process) {
        Write-Output "Process: running"
        $Process | Select-Object Id, ProcessName, CPU, StartTime
    } else {
        Write-Output "Process: not running"
    }
} else {
    Write-Output "Process: no pid file"
}

Write-Output "`nLatest checkpoints:"
if (Test-Path $Checkpoints) {
    Get-ChildItem $Checkpoints -Directory |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 5 |
        ForEach-Object { Write-Output ("{0} {1}" -f $_.Name, $_.LastWriteTime) }
} else {
    Write-Output "No checkpoint directory."
}

Write-Output "`nStderr tail:"
if (Test-Path $Stderr) {
    Get-Content $Stderr -Tail 12
}

Write-Output "`nStdout tail:"
if (Test-Path $Stdout) {
    Get-Content $Stdout -Tail 8
}
