<#
.SYNOPSIS
    Runs repository analysis on your personal GitHub repositories using Docker Compose.

.DESCRIPTION
    This script:
    1. Validates prerequisites (Docker, GitHub token)
    2. Creates/updates the .env file with your configuration
    3. Starts the required Docker services (TimescaleDB, RabbitMQ)
    4. Initializes the database schema
    5. Runs the GitHub repository extractor against your personal repos

.PARAMETER GitHubToken
    Your GitHub Personal Access Token (classic) with 'repo' scope.
    Can also be set via GITHUB_TOKEN environment variable.

.PARAMETER GitHubUser
    Your GitHub username. If not provided, the script will attempt to detect it from the token.

.PARAMETER GitHubOrg
    Optional GitHub organization to analyze instead of personal repos.

.PARAMETER SkipInfrastructure
    Skip starting Docker containers (useful if they're already running).

.PARAMETER TearDown
    Stop and remove all containers and volumes after analysis.

.PARAMETER Verbose
    Enable verbose output for debugging.

.EXAMPLE
    .\Run-GitHubAnalysis.ps1 -GitHubToken "ghp_xxxx" -GitHubUser "myusername"

.EXAMPLE
    .\Run-GitHubAnalysis.ps1 -GitHubOrg "my-organization"

.EXAMPLE
    $env:GITHUB_TOKEN = "ghp_xxxx"; .\Run-GitHubAnalysis.ps1 -GitHubUser "myusername"
#>

[CmdletBinding()]
param(
    [Parameter()]
    [string]$GitHubToken = $env:GITHUB_TOKEN,

    [Parameter()]
    [string]$GitHubUser = $env:GITHUB_USER,

    [Parameter()]
    [string]$GitHubOrg = $env:GITHUB_ORG,

    [Parameter()]
    [switch]$SkipInfrastructure,

    [Parameter()]
    [switch]$TearDown
)

# Strict mode for better error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Script configuration
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
$EnvFile = Join-Path $ProjectRoot ".env"
$SchemaFile = Join-Path $ProjectRoot "database\schema.sql"
# Resolve any environment variable references in the token
if ($GitHubToken -and $GitHubToken.Contains('%')) {
    $githubtoken = [Environment]::ExpandEnvironmentVariables($GitHubToken)
}
else {
    $githubtoken = $GitHubToken
}

# Color output helpers
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
    exit 1
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] " -ForegroundColor Blue -NoNewline
    Write-Host $Message
}

# Banner
function Show-Banner {
    Write-Host @"

 ____                        _
|  _ \ ___ _ __   ___       / \   _ __   __ _ _ __ _   _
| |_) / _ \ '_ \ / _ \     / _ \ | '_ \ / _` | '__| | | |
|  _ <  __/ |_) | (_) |   / ___ \| | | | (_| | |  | |_| |
|_| \_\___| .__/ \___/   /_/   \_\_| |_|\__,_|_|   \__, |
          |_|            GitHub Repository Analyzer|___/

"@ -ForegroundColor Cyan
}

# Check prerequisites
function Test-Prerequisites {
    Write-Step "Checking prerequisites..."

    # Check Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is not installed or not in PATH. Please install Docker Desktop."
    }

    # Check if Docker daemon is running
    try {
        $null = docker info 2>&1
        Write-Success "Docker is running"
    }
    catch {
        Write-Error "Docker daemon is not running. Please start Docker Desktop."
    }

    # Check docker compose (v2)
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is not installed. Please install Docker."
        return
    }

    try {
        $null = docker compose version 2>&1
        Write-Success "Docker Compose v2 is available"
        $script:ComposeCommand = "docker compose"
    }
    catch {
        Write-Error "Docker Compose v2 is not available. Please ensure Docker Desktop or Docker Compose v2 is installed."
        return
    }

    # Check GitHub token
    if ([string]::IsNullOrEmpty($GitHubToken)) {
        Write-Error @"
GitHub token is required. Provide it via:
  - Parameter: -GitHubToken "ghp_xxxx"
  - Environment variable: `$env:GITHUB_TOKEN = "ghp_xxxx"

Create a token at: https://github.com/settings/tokens
Required scopes: repo (Full control of private repositories)
"@
    }
    Write-Success "GitHub token provided"

    # Validate token and get username if needed
    if ([string]::IsNullOrEmpty($GitHubUser) -and [string]::IsNullOrEmpty($GitHubOrg)) {
        Write-Info "Detecting GitHub username from token..."
        try {
            $headers = @{
                "Authorization" = "Bearer $GitHubToken"
                "Accept"        = "application/vnd.github.v3+json"
                "User-Agent"    = "RepoAnalyzer-PowerShell"
            }
            $response = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headers -Method Get
            $script:GitHubUser = $response.login
            Write-Success "Detected GitHub user: $($script:GitHubUser)"
        }
        catch {
            Write-Error "Failed to validate GitHub token. Please check your token and try again."
        }
    }
}

# Create or update .env file
function Initialize-Environment {
    Write-Step "Configuring environment..."

    # Generate secure passwords
    $postgresPassword = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
    $rabbitmqPassword = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 24 | ForEach-Object { [char]$_ })

    # Check if .env exists and has GitHub config
    $existingEnv = @{}
    if (Test-Path $EnvFile) {
        Get-Content $EnvFile | ForEach-Object {
            if ($_ -match '^([^#=]+)=(.*)$') {
                $existingEnv[$matches[1].Trim()] = $matches[2].Trim()
            }
        }
        Write-Info "Found existing .env file"

        # Preserve existing passwords if set
        if ($existingEnv.ContainsKey("POSTGRES_PASSWORD") -and $existingEnv["POSTGRES_PASSWORD"] -ne "changeme_secure_password") {
            $postgresPassword = $existingEnv["POSTGRES_PASSWORD"]
        }
        if ($existingEnv.ContainsKey("RABBITMQ_DEFAULT_PASS") -and $existingEnv["RABBITMQ_DEFAULT_PASS"] -ne "changeme_rabbitmq_password") {
            $rabbitmqPassword = $existingEnv["RABBITMQ_DEFAULT_PASS"]
        }
    }

    # Build environment content
    $envContent = @"
# ===========================================
# Repository Analyzer - Environment Variables
# ===========================================
# Auto-generated by Run-GitHubAnalysis.ps1 on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# -----------------
# PostgreSQL/TimescaleDB Configuration
# -----------------
POSTGRES_USER=analyzer
POSTGRES_PASSWORD=$postgresPassword
POSTGRES_DB=repo_analyzer
POSTGRES_HOST=timescaledb
POSTGRES_PORT=5432

# TimescaleDB specific
TIMESCALEDB_TELEMETRY=off

# -----------------
# RabbitMQ Configuration
# -----------------
RABBITMQ_DEFAULT_USER=analyzer
RABBITMQ_DEFAULT_PASS=$rabbitmqPassword
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_MANAGEMENT_PORT=15672

# Celery broker URL
CELERY_BROKER_URL=amqp://analyzer:$rabbitmqPassword@rabbitmq:5672//

# -----------------
# GitHub Configuration
# -----------------
GITHUB_TOKEN=$GitHubToken
GITHUB_ORG=$GitHubOrg
GITHUB_USER=$GitHubUser

# -----------------
# Application Configuration
# -----------------
LOG_LEVEL=INFO
CELERY_WORKER_CONCURRENCY=4

# -----------------
# Azure DevOps Configuration (not used for GitHub-only analysis)
# -----------------
AZURE_DEVOPS_ORG_URL=
AZURE_DEVOPS_PAT=

# -----------------
# Backup Configuration (optional)
# -----------------
AZURE_STORAGE_CONNECTION_STRING=
AZURE_BACKUP_CONTAINER=database-backups
"@

    # Write .env file
    $envContent | Out-File -FilePath $EnvFile -Encoding utf8 -Force
    Write-Success "Environment file created/updated: $EnvFile"
}

# Helper to run docker compose commands
function Run-DockerCompose {
    param([string[]]$Arguments)
    & docker compose @Arguments
}

# Start Docker infrastructure
function Start-Infrastructure {
    Write-Step "Starting Docker infrastructure..."

    Push-Location $ProjectRoot
    try {
        # Pull latest images
        Write-Info "Pulling Docker images..."
        Run-DockerCompose -Arguments @("pull", "timescaledb", "rabbitmq", "flower", "grafana") 2>&1 | Out-Null

        # Start infrastructure services only (not the app services yet)
        Write-Info "Starting TimescaleDB, RabbitMQ, Flower, and Grafana..."
        Run-DockerCompose -Arguments @("up", "-d", "timescaledb", "rabbitmq", "flower", "grafana") 2>&1 | Out-Null

        # Wait for services to be healthy
        Write-Info "Waiting for services to be healthy..."

        $maxRetries = 30
        $retryCount = 0

        # Wait for TimescaleDB
        while ($retryCount -lt $maxRetries) {
            $health = docker inspect --format='{{.State.Health.Status}}' analyzer-timescaledb 2>$null
            if ($health -eq "healthy") {
                Write-Success "TimescaleDB is healthy"
                break
            }
            $retryCount++
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 2
        }
        if ($retryCount -ge $maxRetries) {
            Write-Error "TimescaleDB failed to become healthy"
        }

        # Wait for RabbitMQ
        $retryCount = 0
        while ($retryCount -lt $maxRetries) {
            $health = docker inspect --format='{{.State.Health.Status}}' analyzer-rabbitmq 2>$null
            if ($health -eq "healthy") {
                Write-Success "RabbitMQ is healthy"
                break
            }
            $retryCount++
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 2
        }
        if ($retryCount -ge $maxRetries) {
            Write-Error "RabbitMQ failed to become healthy"
        }
    }
    finally {
        Pop-Location
    }
}

# Initialize database schema
function Initialize-Database {
    Write-Step "Initializing database schema..."

    # Load environment variables
    $envVars = @{}
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $envVars[$matches[1].Trim()] = $matches[2].Trim()
        }
    }

    $pgUser = $envVars["POSTGRES_USER"]
    $pgDb = $envVars["POSTGRES_DB"]

    # Check if schema already exists
    $checkQuery = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'organizations';"
    $result = docker exec analyzer-timescaledb psql -U $pgUser -d $pgDb -t -c $checkQuery 2>$null

    if ($result -and $result.Trim() -gt 0) {
        Write-Info "Database schema already exists"
        return
    }

    # Copy schema file to container and execute
    Write-Info "Creating database schema..."

    if (-not (Test-Path $SchemaFile)) {
        Write-Error "Schema file not found: $SchemaFile"
    }

    # Copy schema to container
    docker cp $SchemaFile analyzer-timescaledb:/tmp/schema.sql

    # Execute schema
    docker exec analyzer-timescaledb psql -U $pgUser -d $pgDb -f /tmp/schema.sql 2>&1 | Out-Null

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Some schema statements may have warnings (this is often OK for IF NOT EXISTS clauses)"
    }

    Write-Success "Database schema initialized"
}

# Run the GitHub analysis
function Start-Analysis {
    Write-Step "Running GitHub repository analysis..."

    Push-Location $ProjectRoot
    try {
        # Build the application image
        Write-Info "Building application image..."
        Run-DockerCompose -Arguments @("build", "scheduler") 2>&1 | Out-Null

        # Run the extraction using the external Python script
        Write-Info "Starting repository extraction (this may take a while for large accounts)..."

        Run-DockerCompose -Arguments @("run", "--rm", "scheduler", "python", "/app/scripts/run_extraction.py")

        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Extraction completed with some warnings"
        }
        else {
            Write-Success "Extraction completed successfully"
        }
    }
    finally {
        Pop-Location
    }
}

# Show access information
function Show-AccessInfo {
    Write-Step "Analysis complete! Access your data:"

    Write-Host @"

 SERVICES AVAILABLE:
 -------------------
 TimescaleDB:     localhost:5432
 RabbitMQ:        localhost:5672
 RabbitMQ UI:     http://localhost:15672
 Flower UI:       http://localhost:5555  (task monitoring)
 Grafana UI:      http://localhost:3000  (admin/admin)

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
 1. Open Grafana at http://localhost:3000 (admin/admin) to view dashboards
 2. Connect a SQL client to explore raw data if needed
 3. Run scheduled analysis with: docker compose up -d
 4. Check Flower at http://localhost:5555 to monitor background tasks

"@ -ForegroundColor Gray
}

# Tear down infrastructure
function Stop-Infrastructure {
    Write-Step "Tearing down infrastructure..."

    Push-Location $ProjectRoot
    try {
        Run-DockerCompose -Arguments @("down", "-v") 2>&1 | Out-Null
        Write-Success "Infrastructure stopped and volumes removed"
    }
    finally {
        Pop-Location
    }
}

# Main execution
function Main {
    Show-Banner

    # Validate prerequisites
    Test-Prerequisites

    # Initialize environment
    Initialize-Environment

    if (-not $SkipInfrastructure) {
        # Start Docker services
        Start-Infrastructure

        # Initialize database
        Initialize-Database
    }

    # Run analysis
    Start-Analysis

    # Show access info
    Show-AccessInfo

    # Optionally tear down
    if ($TearDown) {
        Stop-Infrastructure
    }
}

# Run main
try {
    Main
}
catch {
    Write-Error "Script failed: $_"
}
