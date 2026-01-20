<#
.SYNOPSIS
    Global constants and configuration for the startup scripts.
#>

# Project structure
$script:ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$script:EnvFile = Join-Path $ProjectRoot ".env"
$script:EnvExampleFile = Join-Path $ProjectRoot ".env.example"
$script:SchemaFile = Join-Path $ProjectRoot "database\schema.sql"
$script:DockerComposePath = $ProjectRoot

# Docker services
$script:DockerServices = @{
    Core      = @("timescaledb", "rabbitmq", "flower", "grafana")
    Worker    = "celery-worker"
    Migration = "db-migrations"
    Scheduler = "scheduler"
}

# Default values
$script:DefaultPostgresUser = "analyzer"
$script:DefaultPostgresDb = "repo_analyzer"
$script:DefaultPostgresHost = "timescaledb"
$script:DefaultPostgresPort = 5432

$script:DefaultRabbitmqUser = "analyzer"
$script:DefaultRabbitmqHost = "rabbitmq"
$script:DefaultRabbitmqPort = 5672
$script:DefaultRabbitmqManagementPort = 15672

$script:DefaultLogLevel = "INFO"
$script:DefaultCeleryWorkerConcurrency = 4

# Health check configuration
$script:MaxHealthCheckRetries = 30
$script:HealthCheckInterval = 2

# Password generation
$script:PasswordLength = 24

# Service URLs (read from .env or use defaults)
# These should match port mappings in docker-compose.yml
$script:GrafanaPort = [int]($env:GRAFANA_PORT ?? 3000)
$script:FlowerPort = [int]($env:FLOWER_PORT ?? 5555)
$script:RabbitmqManagementPort = [int]($env:RABBITMQ_MANAGEMENT_PORT ?? 15672)

$script:GrafanaUrl = "http://localhost:$($script:GrafanaPort)"
$script:FlowerUrl = "http://localhost:$($script:FlowerPort)"
$script:RabbitmqManagementUrl = "http://localhost:$($script:RabbitmqManagementPort)"

# Grafana defaults
$script:GrafanaUser = "admin"
$script:GrafanaPassword = "admin"

