<#
.SYNOPSIS
    Bootstraps and runs repository analysis via Docker Compose (env setup, infra, migrations, extraction).

.DESCRIPTION
    This script:
    1. Validates prerequisites (Docker)
    2. Creates/updates the .env file with your configuration (prompts for credentials)
    3. Starts the required Docker services (TimescaleDB, RabbitMQ)
    4. Initializes the database schema
    5. Runs the repository extractor for GitHub/Azure DevOps

.PARAMETER SkipInfrastructure
    Skip starting Docker containers (useful if they're already running).

.PARAMETER RunDirect
    Run extraction directly without using Celery workers. By default, extraction
    is submitted to Celery for distributed processing and can be monitored in Flower.

.PARAMETER TearDown
    Stop and remove all containers and volumes after analysis.

.PARAMETER RegenerateEnv
    Force regeneration of .env file, prompting for all values.

.EXAMPLE
    .\Start-RepoAnalysis.ps1 -RegenerateEnv

.EXAMPLE
    .\Start-RepoAnalysis.ps1 -RunDirect

.EXAMPLE
    .\Start-RepoAnalysis.ps1 -SkipInfrastructure -RunDirect
#>

param(
    [Parameter()]
    [switch]$SkipInfrastructure,

    [Parameter()]
    [switch]$RunDirect,

    [Parameter()]
    [switch]$TearDown,

    [Parameter()]
    [switch]$RegenerateEnv
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Import modules
$libPath = Join-Path $PSScriptRoot "startup-scripts" "lib"
. (Join-Path $libPath "Constants.ps1")
. (Join-Path $libPath "OutputHelpers.ps1")
. (Join-Path $libPath "EnvironmentHelpers.ps1")
. (Join-Path $libPath "DockerHelpers.ps1")
. (Join-Path $libPath "EnvFileHelpers.ps1")

# Orchestration functions

function Initialize-Environment {
    Write-Step "Configuring environment..."
    $success = New-EnvFile `
        -Force:$RegenerateEnv `
        -EnvFile $script:EnvFile `
        -EnvExampleFile $script:EnvExampleFile
    
    if (-not $success) {
        return $false
    }

    Write-Info "Validating required credentials..."
    if (-not (Test-RequiredEnvVars -EnvFile $script:EnvFile)) {
        Write-Error "Environment validation failed. Please configure valid credentials."
        return $false
    }

    Write-Info "Resolving and exporting environment variables..."
    if (-not (Export-ResolvedEnvVars -EnvFile $script:EnvFile)) {
        Write-Error "Failed to resolve environment variable references. See warnings above."
        return $false
    }
    
    return $true
}

function Start-Infrastructure {
    Write-Step "Starting Docker infrastructure..."

    Push-Location $script:ProjectRoot
    try {
        Write-Info "Pulling Docker images..."
        $services = $script:DockerServices.Core
        if (-not $RunDirect) {
            $services += $script:DockerServices.Worker
        }
        Run-DockerCompose -Arguments (@("pull") + $services) 2>&1 | Out-Null

        Write-Info "Starting services..."
        if ($RunDirect) {
            Write-Info "  - Running in DIRECT mode (no Celery workers)"
            Run-DockerCompose -Arguments @("up", "-d") + $script:DockerServices.Core 2>&1 | Out-Null
        }
        else {
            Write-Info "  - Running in CELERY mode with worker monitoring"
            $allServices = $script:DockerServices.Core + $script:DockerServices.Worker
            Run-DockerCompose -Arguments (@("up", "-d") + $allServices) 2>&1 | Out-Null
        }

        Write-Info "Waiting for services to be healthy..."
        Wait-ForHealthy -ContainerName "analyzer-timescaledb" -MaxRetries $script:MaxHealthCheckRetries -Interval $script:HealthCheckInterval | Out-Null
        Wait-ForHealthy -ContainerName "analyzer-rabbitmq" -MaxRetries $script:MaxHealthCheckRetries -Interval $script:HealthCheckInterval | Out-Null
    }
    finally {
        Pop-Location
    }
}

function Initialize-Database {
    Write-Step "Initializing database schema and migrations..."

    Push-Location $script:ProjectRoot
    try {
        Write-Info "Starting database migration service..."
        
        try {
            Run-DockerCompose -Arguments @("run", "--rm", $script:DockerServices.Migration) 2>&1 | Out-Null

            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Migration service completed with warnings (this may be OK if migrations already applied)"
            }
            else {
                Write-Success "Database schema and migrations initialized successfully"
            }
        }
        catch {
            Write-Warning "Error running migrations: $_"
            Write-Info "This may be OK if migrations are already applied"
        }
    }
    finally {
        Pop-Location
    }
}

function Start-Analysis {
    Write-Step "Running repository analysis..."

    Push-Location $script:ProjectRoot
    try {
        Write-Info "Building application image..."
        Run-DockerCompose -Arguments @("build", $script:DockerServices.Scheduler) 2>&1 | Out-Null

        if ($RunDirect) {
            Write-Info "Starting repository extraction in DIRECT mode (synchronous)..."
            Run-DockerCompose -Arguments @("run", "--rm", $script:DockerServices.Scheduler, "python", "/app/scripts/run_extraction.py")

            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Extraction completed with some warnings"
            }
            else {
                Write-Success "Extraction completed successfully"
            }
        }
        else {
            Write-Info "Submitting extraction task to Celery workers..."
            Run-DockerCompose -Arguments @("run", "--rm", $script:DockerServices.Scheduler, "python", "/app/scripts/submit_extraction_task.py")

            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to submit extraction task"
            }
            else {
                Write-Success "Extraction task submitted successfully"
                Write-Info "Task is now being processed by Celery workers"
            }
        }
    }
    finally {
        Pop-Location
    }
}

function Show-AccessInfo {
    Write-Step "Analysis complete! Access your data:"

    $modeInfo = if ($RunDirect) {
        "DIRECT mode - extraction ran synchronously"
    }
    else {
        "CELERY mode - extraction submitted to background workers"
    }

    Write-Host @"

 EXECUTION MODE:
 ---------------
 $modeInfo

 SERVICES AVAILABLE:
 -------------------
 TimescaleDB:     localhost:5432
 RabbitMQ:        localhost:5672
 RabbitMQ UI:     $($script:RabbitmqManagementUrl)
 Flower UI:       $($script:FlowerUrl) (task monitoring)
 Grafana UI:      $($script:GrafanaUrl) (admin/admin)

 DATABASE CONNECTION:
 --------------------
 Host:     localhost
 Port:     5432
 Database: repo_analyzer
 User:     analyzer
 Password: (see .env file)

 USEFUL QUERIES:
 ---------------
 -- List all repositories
 SELECT r.name, r.url, r.default_branch, o.name as org
 FROM repositories r
 JOIN projects p ON r.project_id = p.project_id
 JOIN organizations o ON p.organization_id = o.organization_id;

 -- Count commits by contributor
 SELECT c.name, c.email, COUNT(cm.commit_sha) as commit_count
 FROM contributors c
 JOIN commits cm ON c.id = cm.author_id
 GROUP BY c.id, c.name, c.email
 ORDER BY commit_count DESC;

 -- PR statistics
 SELECT status, COUNT(*) as count, AVG(lines_added + lines_removed) as avg_changes
 FROM pull_requests
 GROUP BY status;

 NEXT STEPS:
 -----------
 1. Open Grafana at $($script:GrafanaUrl) to view dashboards
 2. Connect a SQL client to explore raw data if needed
 3. Run scheduled analysis with: docker compose up -d
"@ -ForegroundColor Gray

    if (-not $RunDirect) {
        Write-Host " 4. Monitor task progress in Flower at $($script:FlowerUrl)" -ForegroundColor Gray
    }

    Write-Host "" -ForegroundColor Gray
}

function Stop-Infrastructure {
    Write-Step "Tearing down infrastructure..."

    Push-Location $script:ProjectRoot
    try {
        Run-DockerCompose -Arguments @("down", "-v") 2>&1 | Out-Null
        Write-Success "Infrastructure stopped and volumes removed"
    }
    finally {
        Pop-Location
    }
}

function Main {
    try {
        Show-Banner

        if (-not (Test-DockerPrerequisites)) {
            Write-Error "Docker prerequisites not met"
            exit 1
        }

        if (-not (Initialize-Environment)) {
            Write-Error "Failed to initialize environment"
            exit 1
        }

        if (-not $SkipInfrastructure) {
            Start-Infrastructure
            Initialize-Database
        }

        Start-Analysis
        Show-AccessInfo

        if ($TearDown) {
            Stop-Infrastructure
        }
    }
    catch {
        Write-Error "Script failed: $_`n$($_.Exception.StackTrace)"
        exit 1
    }
}

# Execute
Main
