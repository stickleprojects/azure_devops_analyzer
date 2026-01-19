# Pre-commit hook for Python code quality checks (Windows PowerShell)
# Automatically runs tests and analysis on Python files before commit
#
# Install: Run setup_git_hooks.ps1
# To bypass: git commit --no-verify

param(
    [switch]$SkipTests
)

# Colors
$ErrorColor = "Red"
$SuccessColor = "Green"
$WarningColor = "Yellow"
$InfoColor = "Cyan"

function Write-StepMessage {
    param([string]$Message)
    Write-Host $Message -ForegroundColor $InfoColor
}

function Write-SuccessMessage {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $SuccessColor
}

function Write-ErrorMessage {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $ErrorColor
}

function Write-WarningMessage {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $WarningColor
}

Write-StepMessage "`n=== Pre-commit Python Validation ==="

# Get list of Python files being committed
$pythonFiles = @(git diff --cached --name-only --diff-filter=ACM | Where-Object { $_ -like "*.py" })

if ($pythonFiles.Count -eq 0) {
    Write-SuccessMessage "No Python files to check"
    exit 0
}

Write-StepMessage "Checking Python files:"
$pythonFiles | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }

$errors = 0

# 1. Check syntax
Write-StepMessage "`n[1/3] Validating Python syntax..."
foreach ($file in $pythonFiles) {
    if (Test-Path $file) {
        try {
            $null = python -m py_compile $file 2>&1
            Write-SuccessMessage "$file"
        }
        catch {
            Write-ErrorMessage "Syntax error in $file"
            $errors++
        }
    }
}

# 2. Run tests if available
if ((Test-Path "tests/test_imports_and_structure.py") -and -not $SkipTests) {
    Write-StepMessage "`n[2/3] Running import structure tests..."
    
    # Check if pytest is available
    $pytestAvailable = $null -ne (Get-Command pytest -ErrorAction SilentlyContinue)
    
    if ($pytestAvailable) {
        $testOutput = pytest tests/test_imports_and_structure.py -v --tb=short 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-SuccessMessage "All import tests passed"
        }
        else {
            Write-ErrorMessage "Import tests failed"
            Write-Host $testOutput -ForegroundColor $WarningColor
            $errors++
        }
    }
    else {
        Write-WarningMessage "pytest not installed, skipping unit tests"
        Write-Host "  Install with: pip install pytest" -ForegroundColor Gray
    }
}

# 3. Check for common issues
Write-StepMessage "`n[3/3] Checking for common Python issues..."
$issueCount = 0

foreach ($file in $pythonFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        
        if ($content -match "from tasks\.") {
            Write-ErrorMessage "File $file uses non-existent 'tasks' module"
            $issueCount++
        }
        
        if ($content -match "from scheduler\.celery_app") {
            Write-ErrorMessage "File $file uses wrong import path (should be 'src.scheduler.celery_app')"
            $issueCount++
        }
    }
}

if ($issueCount -eq 0) {
    Write-SuccessMessage "No common issues detected"
}
else {
    $errors += $issueCount
}

# Summary
Write-StepMessage "`n=== Pre-commit Check Summary ==="
if ($errors -eq 0) {
    Write-SuccessMessage "All checks passed! Proceeding with commit."
    exit 0
}
else {
    Write-ErrorMessage "$errors error(s) found. Commit aborted."
    Write-WarningMessage "To bypass this check, use: git commit --no-verify"
    exit 1
}
