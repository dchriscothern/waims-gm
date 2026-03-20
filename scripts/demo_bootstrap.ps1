param(
    [switch]$LocalDemo = $true,
    [switch]$FullStack,
    [switch]$SeedDemoData,
    [switch]$NoNewWindows
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$streamlitApp = Join-Path $repoRoot "streamlit_app.py"
$preflight = Join-Path $repoRoot "scripts\preflight.py"
$seedScript = Join-Path $repoRoot "scripts\seed_demo_data.py"

if (-not (Test-Path $python)) {
    throw "Project virtualenv not found at $python"
}

if ($FullStack) {
    $LocalDemo = $false
}

Write-Host "WAIMS-GM Demo Bootstrap" -ForegroundColor Cyan
Write-Host "Repo: $repoRoot"

if ($LocalDemo) {
    Write-Host "Mode: Local interview demo (no Supabase auth or backend required)" -ForegroundColor Green
} else {
    Write-Host "Mode: Full stack sandbox demo" -ForegroundColor Yellow
    & $python $preflight
}

if (-not $LocalDemo) {
    $backendCommand = "& '$python' -m uvicorn app.main:app --reload"
    if ($NoNewWindows) {
        Write-Host "Starting FastAPI in this terminal..." -ForegroundColor Yellow
        Start-Job -ScriptBlock {
            param($root, $command)
            Set-Location $root
            powershell -NoProfile -Command $command
        } -ArgumentList $repoRoot, $backendCommand | Out-Null
    } else {
        Start-Process powershell -WorkingDirectory $repoRoot -ArgumentList "-NoExit", "-Command", $backendCommand | Out-Null
    }
    Start-Sleep -Seconds 2
}

if ($SeedDemoData -and -not $LocalDemo) {
    Write-Host "Seeding sandbox demo data..." -ForegroundColor Yellow
    & $python $seedScript --replace
}

if ($LocalDemo) {
    $streamlitCommand = "`$env:WAIMS_DEMO_MODE='1'; & '$python' -m streamlit run '$streamlitApp'"
} else {
    $streamlitCommand = "& '$python' -m streamlit run '$streamlitApp'"
}

if ($NoNewWindows) {
    Write-Host "Starting Streamlit in this terminal..." -ForegroundColor Yellow
    powershell -NoProfile -Command $streamlitCommand
} else {
    Start-Process powershell -WorkingDirectory $repoRoot -ArgumentList "-NoExit", "-Command", $streamlitCommand | Out-Null
    Write-Host "Streamlit launched in a new PowerShell window." -ForegroundColor Green
}

if ($LocalDemo) {
    Write-Host ""
    Write-Host "Interview mode notes:" -ForegroundColor Cyan
    Write-Host "- No token is required."
    Write-Host "- Demo dossiers are loaded locally from shared canonical demo files."
    Write-Host "- Create, delete, compare, and export work in local session state."
} else {
    Write-Host ""
    Write-Host "Full stack notes:" -ForegroundColor Cyan
    Write-Host "- Generate a sandbox token with scripts\get_token.py"
    Write-Host "- Paste the token into the Streamlit sidebar and click Load briefing."
}
