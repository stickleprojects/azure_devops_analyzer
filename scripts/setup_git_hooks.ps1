<#
.SYNOPSIS
    Setup script to install git hooks for Python code validation (Windows)

.DESCRIPTION
    This script installs pre-commit and post-commit hooks that automatically
    validate Python code before commits.

.PARAMETER Uninstall
    Uninstall git hooks instead of installing them

.PARAMETER Verify
    Verify git hooks are installed and working

.EXAMPLE
    .\scripts\setup_git_hooks.ps1
    .\scripts\setup_git_hooks.ps1 -Uninstall
    .\scripts\setup_git_hooks.ps1 -Verify
#>

[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$Verify
)

$ErrorActionPreference = "Stop"

# Colors
$SuccessColor = "Green"
$ErrorColor = "Red"
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

function Get-GitHooksDir {
    $hooksDir = Join-Path (Get-Location) ".git" "hooks"
    return $hooksDir
}

function Install-Hooks {
    Write-StepMessage "`nInstalling git hooks..."
    
    $hooksDir = Get-GitHooksDir
    if (-not (Test-Path $hooksDir)) {
        Write-ErrorMessage "Git hooks directory not found: $hooksDir"
        Write-Host "Make sure you're in the root of a git repository." -ForegroundColor Gray
        return $false
    }
    
    $hookMappings = @(
        @{
            Source  = "scripts/hooks/pre-commit.ps1"
            Dest    = "pre-commit"
            Content = {
                # Create a wrapper that calls the PS1 script
                $psHookPath = Join-Path (Get-Location) "scripts/hooks/pre-commit.ps1"
                @"
#!/bin/sh
# Pre-commit hook wrapper - calls PowerShell script

powershell.exe -ExecutionPolicy Bypass -File "$psHookPath" `$args
exit `$?
"@
            }
        }
    )
    
    $success = $true
    
    foreach ($mapping in $hookMappings) {
        $destPath = Join-Path $hooksDir $mapping.Dest
        
        if (-not (Test-Path $mapping.Source)) {
            Write-Host "⚠ Source not found: $($mapping.Source)" -ForegroundColor $WarningColor
            continue
        }
        
        try {
            $content = & $mapping.Content
            $content | Out-File -FilePath $destPath -Encoding ASCII -NoNewline -Force
            Write-SuccessMessage "Installed $($mapping.Dest)"
        }
        catch {
            Write-ErrorMessage "Failed to install $($mapping.Dest): $_"
            $success = $false
        }
    }
    
    return $success
}

function Uninstall-Hooks {
    Write-StepMessage "`nUninstalling git hooks..."
    
    $hooksDir = Get-GitHooksDir
    if (-not (Test-Path $hooksDir)) {
        Write-ErrorMessage "Git hooks directory not found: $hooksDir"
        return $false
    }
    
    $hooksToRemove = @("pre-commit", "post-commit")
    $success = $true
    
    foreach ($hook in $hooksToRemove) {
        $hookPath = Join-Path $hooksDir $hook
        if (Test-Path $hookPath) {
            try {
                Remove-Item $hookPath -Force
                Write-SuccessMessage "Removed $hook"
            }
            catch {
                Write-ErrorMessage "Failed to remove ${hook}: $_"
                $success = $false
            }
        }
        else {
            Write-Host "- $hook not installed" -ForegroundColor Gray
        }
    }
    
    return $success
}

function Verify-Hooks {
    Write-StepMessage "`nVerifying git hooks..."
    
    $hooksDir = Get-GitHooksDir
    if (-not (Test-Path $hooksDir)) {
        Write-ErrorMessage "Git hooks directory not found: $hooksDir"
        return $false
    }
    
    $hooksToCheck = @("pre-commit", "post-commit")
    $allGood = $true
    
    foreach ($hook in $hooksToCheck) {
        $hookPath = Join-Path $hooksDir $hook
        if (Test-Path $hookPath) {
            Write-SuccessMessage "$hook installed"
        }
        else {
            Write-ErrorMessage "$hook not installed"
            $allGood = $false
        }
    }
    
    return $allGood
}

# Main execution
try {
    if ($Uninstall) {
        $success = Uninstall-Hooks
    }
    elseif ($Verify) {
        $success = Verify-Hooks
    }
    else {
        $success = Install-Hooks
        if ($success) {
            Write-SuccessMessage "`nGit hooks installed successfully!`n"
            Write-Host "Python code will be validated before each commit.`n" -ForegroundColor Gray
            Write-Host "To bypass: git commit --no-verify`n" -ForegroundColor Gray
            $null = Verify-Hooks
        }
    }
    
    exit $(if ($success) { 0 } else { 1 })
}
catch {
    Write-ErrorMessage "Error: $_"
    exit 1
}
