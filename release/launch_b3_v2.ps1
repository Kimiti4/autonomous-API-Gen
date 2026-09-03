# launch_b3_v2.ps1 — start the B3-v2 Campaign B wave (Windows).
#
# See release/launch_b3_v2.sh for the full explanation. This is the
# Windows PowerShell equivalent.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
$EvidenceDir = Join-Path $RepoRoot "release/evidence"
$LogDir      = Join-Path $EvidenceDir "b3-v2-logs"
$null = New-Item -ItemType Directory -Force -Path $EvidenceDir
$null = New-Item -ItemType Directory -Force -Path $LogDir

$LaunchMarker = Join-Path $EvidenceDir ".b3-v2-launch-marker"
$Timestamp    = (Get-Date -AsUTC).ToString("yyyyMMddTHHmmssZ")
$LogFile      = Join-Path $LogDir "b3-v2-$Timestamp.log"

Set-Location $RepoRoot

Write-Host "=== B3-v2 launch preflight ==="
Write-Host "Repo root: $RepoRoot"
Write-Host "Evidence:  $EvidenceDir"
Write-Host "Log:       $LogFile"
Write-Host ""

# 1. Sanity: B3-v1 ledger is preserved (unmodified).
$B3V1Ledger = Join-Path $EvidenceDir "cbc1-b-B3-ledger.jsonl"
if (-not (Test-Path $B3V1Ledger)) {
    Write-Error "FATAL: B3-v1 ledger not found at $B3V1Ledger"
    exit 2
}
$B3V1Lines = (Get-Content $B3V1Ledger).Count
Write-Host "B3-v1 ledger:  $B3V1Ledger ($B3V1Lines records)"
if ($B3V1Lines -ne 149) {
    Write-Warning "B3-v1 ledger line count is $B3V1Lines, expected 149. Continuing."
}
$B3V1Agg = Join-Path $EvidenceDir "cbc1-b-B3-aggregate.json"
if (Test-Path $B3V1Agg) {
    Write-Host "B3-v1 aggregate: present"
} else {
    Write-Host "B3-v1 aggregate: MISSING (interrupted before aggregate was written)"
}

# 2. Verify infra-storm code is in place.
$infraCheck = python -c "from certification.evidence.infra_storm import InfraStormLedger; print('OK')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "FATAL: certification.evidence.infra_storm not importable. Commit 80a67b8 missing?"
    exit 2
}
Write-Host "Infra-storm module: OK"

# 3. Docker.
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "FATAL: docker daemon is not reachable."
    exit 2
}
Write-Host "Docker: OK"

# 4. Wave config sanity.
python -c "
from certification.campaign.waves import WAVES, BUDGETS
w = WAVES.get('B3'); b = BUDGETS.get('B3')
assert w is not None and b is not None
assert w.required_mode.value == 'real_docker'
assert b.max_trials == 936
assert b.max_total_runtime_s == 43200
print(f'B3: scale={w.scale_factor}, mode={w.required_mode.value}, max_trials={b.max_trials}, max_runtime={b.max_total_runtime_s}s')
"
if ($LASTEXITCODE -ne 0) {
    Write-Error "FATAL: B3 wave config sanity failed."
    exit 2
}
Write-Host ""

# 5. Launch marker.
if (Test-Path $LaunchMarker) {
    Write-Warning "Launch marker exists at $LaunchMarker. A prior B3-v2 launch may be in flight."
    Write-Warning "  To override, delete the marker manually."
    exit 3
}
Set-Content -Path $LaunchMarker -Value @"
launched_at=$Timestamp
log_file=$LogFile
pid=$PID
"@
Write-Host "Launch marker: $LaunchMarker"

# 6. Launch.
Write-Host ""
Write-Host "=== Launching B3-v2 (foreground, log: $LogFile) ==="
Write-Host "  This will run for up to 12 hours. Press Ctrl-C to interrupt."
Write-Host "  To resume later: CBC1_RESUME=1 $LogFile"
Write-Host ""

try {
    $env:CBC1_WAVE = "B3"
    $env:CBC1_INFRA_STORM = "1"
    $env:CBC1_EVOLVE = "1"
    python -u release/run_wave.py 2>&1 | Tee-Object -FilePath $LogFile
    $exitCode = $LASTEXITCODE
}
finally {
    Remove-Item -Force $LaunchMarker -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "=== B3-v2 finished (exit=$exitCode) ==="
Write-Host "Aggregate:           $EvidenceDir/cbc1-b-B3-aggregate.json"
Write-Host "Verdict ledger:      $EvidenceDir/cbc1-b-B3-ledger.jsonl"
Write-Host "Infra-storm ledger:  $EvidenceDir/cbc1-b-B3-infra-storm.jsonl"
Write-Host "B3-v1 ledger (preserved): $B3V1Ledger"

exit $exitCode
