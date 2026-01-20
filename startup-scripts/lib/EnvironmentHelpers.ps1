<#
.SYNOPSIS
    Environment variable utilities for handling .env files and references.
#>

function New-RandomPassword {
    param([int]$Length = 24)
    $chars = (65..90) + (97..122) + (48..57)
    -join ($chars | Get-Random -Count $Length | ForEach-Object { [char]$_ })
}

function Select-EnvVariable {
    param([string]$SearchTerm)

    $envVars = [Environment]::GetEnvironmentVariables()
    $matches = @()

    foreach ($name in $envVars.Keys) {
        if ($name -like "*${SearchTerm}*") {
            $matches += $name
        }
    }

    if ($matches.Count -eq 0) {
        Write-Warning "No environment variables matched '$SearchTerm'"
        return $null
    }

    Write-Info "Select an environment variable value:"
    for ($i = 0; $i -lt $matches.Count; $i++) {
        $idx = $i + 1
        Write-Host "  [$idx] $($matches[$i])" -ForegroundColor Gray
    }

    $choice = Read-Host "Enter number (or press Enter to cancel)"
    if ([string]::IsNullOrWhiteSpace($choice)) {
        return $null
    }

    if (-not [int]::TryParse($choice, [ref]$null)) {
        Write-Warning "Invalid selection. Skipping env selection."
        return $null
    }

    $index = [int]$choice - 1
    if ($index -lt 0 -or $index -ge $matches.Count) {
        Write-Warning "Selection out of range. Skipping env selection."
        return $null
    }

    $selectedName = $matches[$index]
    return @{ Name = $selectedName; Value = $envVars[$selectedName] }
}

function Resolve-EnvValue {
    param([string]$Value)

    if ($Value -match '^\$\{?([A-Za-z0-9_]+)\}?$') {
        $name = $matches[1]
        $resolved = [Environment]::GetEnvironmentVariable($name)
        if ($null -ne $resolved) {
            return $resolved
        }
    }

    if ($Value -match '^\$env:([A-Za-z0-9_]+)$') {
        $name = $matches[1]
        $resolved = [Environment]::GetEnvironmentVariable($name)
        if ($null -ne $resolved) {
            return $resolved
        }
    }

    return $Value
}

