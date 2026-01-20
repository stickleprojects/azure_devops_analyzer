<#
.SYNOPSIS
    Docker Compose and infrastructure utilities.
#>

function Run-DockerCompose {
    param([string[]]$Arguments)
    & docker compose @Arguments
}

function Test-DockerPrerequisites {
    Write-Step "Checking Docker prerequisites..."

    # Check Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is not installed or not in PATH. Please install Docker Desktop."
        return $false
    }

    # Check if Docker daemon is running
    try {
        $null = docker info 2>&1
        Write-Success "Docker is running"
    }
    catch {
        Write-Error "Docker daemon is not running. Please start Docker Desktop."
        return $false
    }

    # Check docker compose (v2)
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is not installed. Please install Docker."
        return $false
    }

    try {
        $null = docker compose version 2>&1
        Write-Success "Docker Compose v2 is available"
    }
    catch {
        Write-Error "Docker Compose v2 is not available. Please ensure Docker Desktop or Docker Compose v2 is installed."
        return $false
    }

    Write-Success "Docker prerequisites met"
    return $true
}

function Wait-ForHealthy {
    param(
        [string]$ContainerName,
        [int]$MaxRetries = 30,
        [int]$Interval = 2
    )

    $retryCount = 0
    while ($retryCount -lt $MaxRetries) {
        $health = docker inspect --format='{{.State.Health.Status}}' $ContainerName 2>$null
        if ($health -eq "healthy") {
            Write-Success "$ContainerName is healthy"
            return $true
        }
        $retryCount++
        Write-Host "." -NoNewline
        Start-Sleep -Seconds $Interval
    }

    Write-Error "$ContainerName failed to become healthy"
    return $false
}

