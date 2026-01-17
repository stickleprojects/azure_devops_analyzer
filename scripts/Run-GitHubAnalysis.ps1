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
$githubtoken = [System.Environment]::ExpandEnvironmentVariables($GitHubToken)

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

    # Check docker-compose
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        # Try docker compose (v2)
        try {
            $null = docker compose version 2>&1
            Write-Success "Docker Compose v2 is available"
            $script:ComposeCommand = "docker compose"
        }
        catch {
            Write-Error "Docker Compose is not installed. Please install Docker Compose."
        }
    }
    else {
        Write-Success "Docker Compose is available"
        $script:ComposeCommand = "docker-compose"
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

# Start Docker infrastructure
function Start-Infrastructure {
    Write-Step "Starting Docker infrastructure..."

    Push-Location $ProjectRoot
    try {
        # Pull latest images
        Write-Info "Pulling Docker images..."
        Invoke-Expression "$script:ComposeCommand pull timescaledb rabbitmq 2>&1" | Out-Null

        # Start infrastructure services only (not the app services yet)
        Write-Info "Starting TimescaleDB and RabbitMQ..."
        Invoke-Expression "$script:ComposeCommand up -d timescaledb rabbitmq 2>&1"

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
        Invoke-Expression "$script:ComposeCommand build scheduler 2>&1" | Out-Null

        # Create a one-off container to run the extraction
        Write-Info "Starting repository extraction..."

        # Create a Python script to run the extraction
        $extractorScript = @'
import sys
import os

# Add src to path
sys.path.insert(0, '/app')

from src.extractors.github.extractor import GitHubExtractor
from src.database.connection import session_scope, get_engine
from src.database.models import (
    Organization, Project, Repository, Branch,
    Contributor, Commit, PullRequest, PRReview, PRComment
)
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_extraction():
    """Run GitHub repository extraction."""
    logger.info("Initializing GitHub extractor...")
    extractor = GitHubExtractor()

    logger.info("Fetching organizations/users...")
    orgs = extractor.get_organizations()

    for org_data in orgs:
        logger.info(f"Processing: {org_data.name}")

        with session_scope() as session:
            # Create or update organization
            org = session.query(Organization).filter_by(
                platform=org_data.platform.value,
                name=org_data.name
            ).first()

            if not org:
                org = Organization(
                    name=org_data.name,
                    url=org_data.url,
                    platform=org_data.platform.value
                )
                session.add(org)
                session.flush()
                logger.info(f"  Created organization: {org_data.name}")
            else:
                logger.info(f"  Organization exists: {org_data.name}")

            # Create project (GitHub doesn't have projects, use org name)
            project = session.query(Project).filter_by(
                organization_id=org.organization_id,
                name=org_data.name
            ).first()

            if not project:
                project = Project(
                    organization_id=org.organization_id,
                    name=org_data.name,
                    description=f"GitHub repositories for {org_data.name}"
                )
                session.add(project)
                session.flush()

        # Fetch repositories
        logger.info(f"  Fetching repositories for {org_data.name}...")
        repos = extractor.get_repositories(org_data.name)
        logger.info(f"  Found {len(repos)} repositories")

        for repo_data in repos:
            logger.info(f"    Processing repo: {repo_data.name}")

            with session_scope() as session:
                # Get project
                project = session.query(Project).join(Organization).filter(
                    Organization.name == org_data.name,
                    Organization.platform == org_data.platform.value
                ).first()

                # Create or update repository
                repo = session.query(Repository).filter_by(repo_id=repo_data.repo_id).first()

                if not repo:
                    repo = Repository(
                        repo_id=repo_data.repo_id,
                        project_id=project.project_id,
                        name=repo_data.name,
                        url=repo_data.url,
                        default_branch=repo_data.default_branch,
                        platform_repo_id=repo_data.platform_repo_id,
                        created_at=repo_data.created_at,
                        is_active=True
                    )
                    session.add(repo)
                    session.flush()
                    logger.info(f"      Created repository: {repo_data.name}")
                else:
                    repo.url = repo_data.url
                    repo.default_branch = repo_data.default_branch
                    logger.info(f"      Updated repository: {repo_data.name}")

            # Fetch branches
            try:
                branches = extractor.get_branches(repo_data.repo_id)
                logger.info(f"      Found {len(branches)} branches")

                with session_scope() as session:
                    for branch_data in branches[:10]:  # Limit to first 10 branches
                        branch = session.query(Branch).filter_by(
                            repo_id=repo_data.repo_id,
                            branch_name=branch_data.name
                        ).first()

                        if not branch:
                            branch = Branch(
                                repo_id=repo_data.repo_id,
                                branch_name=branch_data.name,
                                latest_commit_sha=branch_data.latest_commit_sha,
                                is_active=True
                            )
                            session.add(branch)
            except Exception as e:
                logger.warning(f"      Failed to fetch branches: {e}")

            # Fetch recent commits (limit to 50)
            try:
                commits = extractor.get_commits(repo_data.repo_id, limit=50)
                logger.info(f"      Found {len(commits)} recent commits")

                with session_scope() as session:
                    for commit_data in commits:
                        # Check if commit exists
                        existing = session.query(Commit).filter_by(commit_sha=commit_data.sha).first()
                        if existing:
                            continue

                        # Get or create contributor
                        contributor = session.query(Contributor).filter_by(
                            email=commit_data.author_email
                        ).first()

                        if not contributor:
                            contributor = Contributor(
                                email=commit_data.author_email,
                                name=commit_data.author_name
                            )
                            session.add(contributor)
                            session.flush()

                        commit = Commit(
                            commit_sha=commit_data.sha,
                            repo_id=repo_data.repo_id,
                            branch_name=repo_data.default_branch,
                            author_id=contributor.id,
                            committer_id=contributor.id,
                            message=commit_data.message[:1000] if commit_data.message else "",
                            commit_date=commit_data.commit_date,
                            files_changed=commit_data.files_changed,
                            lines_added=commit_data.lines_added,
                            lines_removed=commit_data.lines_removed
                        )
                        session.add(commit)
            except Exception as e:
                logger.warning(f"      Failed to fetch commits: {e}")

            # Fetch pull requests (limit to 20 most recent)
            try:
                prs = extractor.get_pull_requests(repo_data.repo_id)[:20]
                logger.info(f"      Found {len(prs)} pull requests")

                with session_scope() as session:
                    for pr_data in prs:
                        # Check if PR exists
                        existing = session.query(PullRequest).filter_by(
                            repo_id=repo_data.repo_id,
                            pr_number=pr_data.pr_number
                        ).first()

                        if existing:
                            continue

                        # Get or create author contributor
                        author = session.query(Contributor).filter_by(
                            email=pr_data.author_email
                        ).first()

                        if not author:
                            author = Contributor(
                                email=pr_data.author_email,
                                name=pr_data.author_name
                            )
                            session.add(author)
                            session.flush()

                        # Determine size classification
                        total_changes = pr_data.lines_added + pr_data.lines_removed
                        if total_changes < 50:
                            size = "small"
                        elif total_changes < 200:
                            size = "medium"
                        elif total_changes < 500:
                            size = "large"
                        else:
                            size = "extra_large"

                        pr = PullRequest(
                            repo_id=repo_data.repo_id,
                            pr_number=pr_data.pr_number,
                            platform_pr_id=pr_data.platform_pr_id,
                            title=pr_data.title[:500] if pr_data.title else "",
                            description=pr_data.description[:2000] if pr_data.description else None,
                            source_branch=pr_data.source_branch,
                            target_branch=pr_data.target_branch,
                            author_id=author.id,
                            status=pr_data.status,
                            created_at=pr_data.created_at,
                            updated_at=pr_data.updated_at,
                            merged_at=pr_data.merged_at,
                            closed_at=pr_data.closed_at,
                            files_changed=pr_data.files_changed,
                            lines_added=pr_data.lines_added,
                            lines_removed=pr_data.lines_removed,
                            size_category=size
                        )
                        session.add(pr)
                        session.flush()

                        # Add reviews
                        for review_data in pr_data.reviews:
                            reviewer = session.query(Contributor).filter_by(
                                email=review_data.reviewer_email
                            ).first()

                            if not reviewer:
                                reviewer = Contributor(
                                    email=review_data.reviewer_email,
                                    name=review_data.reviewer_name
                                )
                                session.add(reviewer)
                                session.flush()

                            # Map state to vote
                            vote_map = {
                                "approved": 10,
                                "changes_requested": -10,
                                "commented": 0,
                                "dismissed": 0
                            }

                            review = PRReview(
                                pr_id=pr.id,
                                reviewer_id=reviewer.id,
                                review_date=review_data.review_date,
                                vote=vote_map.get(review_data.state, 0),
                                is_required=review_data.is_required
                            )
                            session.add(review)

                        # Add comments
                        for comment_data in pr_data.comments[:50]:  # Limit comments
                            commenter = session.query(Contributor).filter_by(
                                email=comment_data.author_email
                            ).first()

                            if not commenter:
                                commenter = Contributor(
                                    email=comment_data.author_email,
                                    name=comment_data.author_name
                                )
                                session.add(commenter)
                                session.flush()

                            comment = PRComment(
                                pr_id=pr.id,
                                author_id=commenter.id,
                                content=comment_data.content[:2000] if comment_data.content else "",
                                published_date=comment_data.published_date,
                                thread_id=comment_data.thread_id,
                                file_path=comment_data.file_path,
                                line_number=comment_data.line_number,
                                comment_type=comment_data.comment_type
                            )
                            session.add(comment)

            except Exception as e:
                logger.warning(f"      Failed to fetch PRs: {e}")

    logger.info("Extraction complete!")

    # Print summary
    with session_scope() as session:
        org_count = session.query(Organization).count()
        repo_count = session.query(Repository).count()
        branch_count = session.query(Branch).count()
        commit_count = session.query(Commit).count()
        pr_count = session.query(PullRequest).count()
        contributor_count = session.query(Contributor).count()

        print("\n" + "=" * 50)
        print("EXTRACTION SUMMARY")
        print("=" * 50)
        print(f"Organizations:  {org_count}")
        print(f"Repositories:   {repo_count}")
        print(f"Branches:       {branch_count}")
        print(f"Commits:        {commit_count}")
        print(f"Pull Requests:  {pr_count}")
        print(f"Contributors:   {contributor_count}")
        print("=" * 50)

if __name__ == "__main__":
    run_extraction()
'@

        # Save script to temp location and copy to container
        $tempScript = Join-Path $env:TEMP "run_extraction.py"
        $extractorScript | Out-File -FilePath $tempScript -Encoding utf8 -Force

        # Run extraction using docker compose run
        Write-Info "Executing extraction (this may take a while for large accounts)..."

        # Copy script into container
        docker cp $tempScript "analyzer-timescaledb:/tmp/run_extraction.py"

        # Run a one-off container with the extraction script
        $runCmd = "$script:ComposeCommand run --rm -v `"$($tempScript):/app/run_extraction.py:ro`" scheduler python /app/run_extraction.py"
        Invoke-Expression $runCmd

        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Extraction completed with some warnings"
        }
        else {
            Write-Success "Extraction completed successfully"
        }

        # Cleanup temp file
        Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
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
 SELECT c.name, c.email, COUNT(cm.sha) as commit_count
 FROM contributors c
 JOIN commits cm ON c.contributor_id = cm.author_id
 GROUP BY c.contributor_id
 ORDER BY commit_count DESC;

 -- PR statistics
 SELECT status, COUNT(*) as count, AVG(lines_added + lines_removed) as avg_changes
 FROM pull_requests
 GROUP BY status;

 NEXT STEPS:
 -----------
 1. Connect a SQL client to explore the data
 2. Add Grafana for visualization (coming soon)
 3. Run scheduled analysis with: docker-compose up -d

"@ -ForegroundColor Gray
}

# Tear down infrastructure
function Stop-Infrastructure {
    Write-Step "Tearing down infrastructure..."

    Push-Location $ProjectRoot
    try {
        Invoke-Expression "$script:ComposeCommand down -v 2>&1"
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
