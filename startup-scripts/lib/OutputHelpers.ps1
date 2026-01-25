<#
.SYNOPSIS
    Output and formatting utilities.
#>

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> " -ForegroundColor Cyan -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] " -ForegroundColor Blue -NoNewline
    Write-Host $Message
}

function Show-Banner {
    Write-Host @"

 ____                        _
|  _ \ ___ _ __   ___       / \   _ __   __ _ _ __ _   _
| |_) / _ \ '_ \ / _ \     / _ \ | '_ \ / _' | '__| | | |
|  _ <  __/ |_) | (_) |   / ___ \| | | | (_| | |  | |_| |
|_| \_\___| .__/ \___/   /_/   \_\_| |_|\__,_|_|   \__, |
          |_|            GitHub Repository Analyzer|___/

"@ -ForegroundColor Cyan
}

