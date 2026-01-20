<#
.SYNOPSIS
    .env file generation and loading.
#>

[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseDeclaredVarsMoreThanAssignments', 'userResolved,passResolved,hostResolved,portResolved', Justification = 'Variables used in string interpolation')]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingConvertToSecureStringWithPlainText', '', Justification = 'Not creating credentials, just building connection strings')]
param()

function New-EnvFile {
    param(
        [switch]$Force,
        [string]$EnvFile,
        [string]$EnvExampleFile
    )

    if (-not (Test-Path $EnvExampleFile)) {
        Write-Error ".env.example not found at $EnvExampleFile"
        return $false
    }

    if ((Test-Path $EnvFile) -and -not $Force) {
        Write-Info "Existing .env found. Skipping generation (use -RegenerateEnv to overwrite)."
        return $true
    }

    $exampleLines = Get-Content $EnvExampleFile
    $values = @{}

    foreach ($line in $exampleLines) {
        if ($line -match '^\s*([^#=\s]+)\s*=\s*(.*)$') {
            $key = $matches[1].Trim()
            $rawDefault = $matches[2]

            $default = switch ($key) {
                "POSTGRES_PASSWORD" { if ($rawDefault -like "changeme*") { New-RandomPassword } else { $rawDefault } }
                "RABBITMQ_DEFAULT_PASS" { if ($rawDefault -like "changeme*") { New-RandomPassword } else { $rawDefault } }
                default { $rawDefault }
            }

            if ($key -eq "CELERY_BROKER_URL") {
                $values[$key] = $rawDefault
                continue
            }

            $displayDefault = if ([string]::IsNullOrEmpty($default)) { "<empty>" } else { $default }
            $inputRaw = Read-Host "Enter $key [default: $displayDefault] (type 'env' to search existing environment variables)"

            $final = $null

            if ([string]::IsNullOrWhiteSpace($inputRaw)) {
                $final = $default
            }
            elseif ($inputRaw -ieq "env") {
                $searchTerm = Read-Host "Search term for environment variables [default: $key]"
                if ([string]::IsNullOrWhiteSpace($searchTerm)) {
                    $searchTerm = $key
                }
                $selected = Select-EnvVariable -SearchTerm $searchTerm
                if ($null -ne $selected) {
                    $final = "$" + $selected.Name
                    Write-Info "Using value from environment variable '$($selected.Name)'"
                }
                else {
                    $final = $default
                }
            }
            elseif ($inputRaw -match '^\$env:([\w\-]+)$') {
                $envName = $matches[1]
                $envVal = [Environment]::GetEnvironmentVariable($envName)
                if ($null -ne $envVal) {
                    $final = "$" + $envName
                    Write-Info "Using value from environment variable '$envName'"
                }
                else {
                    Write-Warning "Environment variable '$envName' not found. Using typed value."
                    $final = $inputRaw
                }
            }
            else {
                $envVal = [Environment]::GetEnvironmentVariable($inputRaw)
                if ($null -ne $envVal) {
                    $final = "$" + $inputRaw
                    Write-Info "Using value from environment variable '$inputRaw'"
                }
                else {
                    $final = $inputRaw
                }
            }

            $values[$key] = $final
        }
    }

    if ($values.ContainsKey("RABBITMQ_DEFAULT_USER") -and $values.ContainsKey("RABBITMQ_DEFAULT_PASS") -and $values.ContainsKey("RABBITMQ_HOST") -and $values.ContainsKey("RABBITMQ_PORT")) {
        $userResolved = Resolve-EnvValue($values['RABBITMQ_DEFAULT_USER'])
        $passResolved = Resolve-EnvValue($values['RABBITMQ_DEFAULT_PASS'])
        $hostResolved = Resolve-EnvValue($values['RABBITMQ_HOST'])
        $portResolved = Resolve-EnvValue($values['RABBITMQ_PORT'])
        $values["CELERY_BROKER_URL"] = "amqp://${userResolved}:${passResolved}@${hostResolved}:${portResolved}//"
    }

    $outputLines = New-Object System.Collections.Generic.List[string]
    foreach ($line in $exampleLines) {
        if ($line -match '^\s*([^#=\s]+)\s*=\s*(.*)$') {
            $key = $matches[1].Trim()
            $valueToWrite = if ($values.ContainsKey($key)) { $values[$key] } else { $matches[2] }
            $outputLines.Add("$key=$valueToWrite") | Out-Null
        }
        else {
            $outputLines.Add($line) | Out-Null
        }
    }

    $outputLines | Out-File -FilePath $EnvFile -Encoding utf8 -Force
    Write-Success "Environment file created: $EnvFile"
    return $true
}

function Read-EnvFile {
    param([string]$EnvFile)

    $envVars = @{}
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $envVars[$matches[1].Trim()] = Resolve-EnvValue($matches[2].Trim())
        }
    }
    return $envVars
}

function Export-ResolvedEnvVars {
    <#
    .SYNOPSIS
        Exports resolved environment variables to the current process environment.
    
    .DESCRIPTION
        Reads a .env file, resolves all $VARIABLE_NAME references to their actual values
        from the system environment, and exports them to the current process environment.
        Also exports any referenced variables so docker-compose can resolve them.
        This ensures docker-compose can read the resolved values without modifying the .env file.
    
    .PARAMETER EnvFile
        Path to the .env file to read and resolve.
    #>
    param([string]$EnvFile)

    if (-not (Test-Path $EnvFile)) {
        Write-Warning "Env file not found: $EnvFile"
        return $false
    }

    $lines = Get-Content $EnvFile
    $exportCount = 0
    $missingVars = @()

    foreach ($line in $lines) {
        if ($line -match '^([^#=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            # If value is a reference to another variable, export that variable too
            if ($value -match '^\$\{?([A-Za-z0-9_]+)\}?$') {
                $referencedVar = $matches[1]
                $referencedValue = [Environment]::GetEnvironmentVariable($referencedVar)
                if ($null -ne $referencedValue -and $referencedValue -ne '') {
                    [Environment]::SetEnvironmentVariable($referencedVar, $referencedValue, 'Process')
                    Write-Verbose "Exported referenced variable: $referencedVar"
                }
                else {
                    $missingVars += "$key references `$$referencedVar which is not set in the environment"
                }
            }
            elseif ($value -match '^\$env:([A-Za-z0-9_]+)$') {
                $referencedVar = $matches[1]
                $referencedValue = [Environment]::GetEnvironmentVariable($referencedVar)
                if ($null -ne $referencedValue -and $referencedValue -ne '') {
                    [Environment]::SetEnvironmentVariable($referencedVar, $referencedValue, 'Process')
                    Write-Verbose "Exported referenced variable: $referencedVar"
                }
                else {
                    $missingVars += "$key references `$$referencedVar which is not set in the environment"
                }
            }
            
            $resolvedValue = Resolve-EnvValue($value)
            
            # Export to current process environment
            [Environment]::SetEnvironmentVariable($key, $resolvedValue, 'Process')
            $exportCount++
        }
    }

    if ($missingVars.Count -gt 0) {
        Write-Warning "Some environment variable references could not be resolved:"
        foreach ($msg in $missingVars) {
            Write-Warning "  - $msg"
        }
        Write-Info "`nTo fix this, either:"
        Write-Info "  1. Set the environment variable in your system/shell (e.g., export GITHUB_ANALYZER_PAT=your_token)"
        Write-Info "  2. Or update .env to use the actual value instead of a variable reference"
        return $false
    }

    Write-Verbose "Exported $exportCount environment variables"
    return $true
}

function Test-RequiredEnvVars {
    <#
    .SYNOPSIS
        Validates that required environment variables are not blank after resolution.
    
    .DESCRIPTION
        Checks critical environment variables (tokens, passwords) to ensure they have
        non-empty values after resolution. This prevents running with invalid credentials.
    
    .PARAMETER EnvFile
        Path to the .env file to validate.
    
    .RETURNS
        $true if all required variables are set, $false otherwise.
    #>
    param([string]$EnvFile)

    if (-not (Test-Path $EnvFile)) {
        Write-Error "Env file not found: $EnvFile"
        return $false
    }

    # Define required variables that must not be blank
    $requiredVars = @{
        'POSTGRES_PASSWORD'     = 'Database password'
        'RABBITMQ_DEFAULT_PASS' = 'RabbitMQ password'
    }

    # Optional but if set should not be blank (at least one auth token should be configured)
    $optionalAuthVars = @{
        'GITHUB_TOKEN'     = 'GitHub Personal Access Token'
        'AZURE_DEVOPS_PAT' = 'Azure DevOps Personal Access Token'
    }

    $envVars = Read-EnvFile -EnvFile $EnvFile
    $hasErrors = $false
    $hasAtLeastOneAuth = $false

    # Check required variables
    foreach ($varName in $requiredVars.Keys) {
        if (-not $envVars.ContainsKey($varName) -or [string]::IsNullOrWhiteSpace($envVars[$varName])) {
            Write-Error "$($requiredVars[$varName]) ($varName) is blank or not set"
            $hasErrors = $true
        }
    }

    # Check if at least one auth token is configured
    foreach ($varName in $optionalAuthVars.Keys) {
        if ($envVars.ContainsKey($varName) -and -not [string]::IsNullOrWhiteSpace($envVars[$varName])) {
            # Check for placeholder values
            $value = $envVars[$varName]
            if ($value -notlike 'your_*' -and $value -notlike 'changeme*') {
                $hasAtLeastOneAuth = $true
                break
            }
        }
    }

    if (-not $hasAtLeastOneAuth) {
        Write-Error "No authentication token configured. At least one of GITHUB_TOKEN or AZURE_DEVOPS_PAT must be set."
        Write-Error "Current values:"
        foreach ($varName in $optionalAuthVars.Keys) {
            $value = if ($envVars.ContainsKey($varName)) { 
                $envVars[$varName] 
            }
            else { 
                '<not set>' 
            }
            Write-Error "  $varName = $value"
        }
        $hasErrors = $true
    }

    if ($hasErrors) {
        Write-Error "`nPlease update your .env file with valid credentials and try again."
        return $false
    }

    return $true
}

