# Run GitHub extractor tests with isolated venv
# Usage: .\tests\run_github_test.ps1

$ErrorActionPreference = "Stop"
$testDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $testDir
$venvPath = Join-Path $projectRoot ".venv-test"

Write-Host "=== GitHub Extractor Test Runner ===" -ForegroundColor Cyan
Write-Host ""

# Create venv if it doesn't exist
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at $venvPath..." -ForegroundColor Yellow
    python -m venv $venvPath
}

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
. $activateScript

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install --quiet PyGithub python-dotenv pytest

# Load .env file
$envFile = Join-Path $projectRoot ".env"
if (Test-Path $envFile) {
    Write-Host "Loading environment from .env..." -ForegroundColor Yellow
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# Run the tests
Write-Host ""
Write-Host "Running tests..." -ForegroundColor Green
Write-Host ""

Set-Location $projectRoot
pytest tests/test_github_extractor_standalone.py -v -s

Write-Host ""
Write-Host "=== Tests Complete ===" -ForegroundColor Cyan
