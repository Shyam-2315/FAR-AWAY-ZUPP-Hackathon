param(
    [string]$BackendBaseUrl = "http://localhost:8000",
    [string]$FrontendDir = ".\frontend\athena-ai-dashboard-main"
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title =="
}

function Get-EnvValue {
    param(
        [string]$Path,
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    $line = Get-Content -LiteralPath $Path |
        Where-Object { $_ -match "^\s*$Name\s*=" } |
        Select-Object -First 1

    if (-not $line) {
        return $null
    }

    return ($line -replace "^\s*$Name\s*=\s*", "").Trim()
}

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$frontendPath = Resolve-Path -LiteralPath (Join-Path $repoRoot $FrontendDir)

Write-Section "Port 8000"
$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    foreach ($listener in $listeners) {
        $process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
        $name = if ($process) { $process.ProcessName } else { "unknown" }
        Write-Host "LISTENING pid=$($listener.OwningProcess) process=$name address=$($listener.LocalAddress):$($listener.LocalPort)"
    }
} else {
    Write-Host "NOT LISTENING on port 8000"
}

Write-Section "GET /healthz"
$healthUrl = "$BackendBaseUrl/healthz"
try {
    $health = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 10
    Write-Host "URL: $healthUrl"
    Write-Host "Status: $($health.StatusCode)"
    Write-Host "Body: $($health.Content)"
} catch {
    Write-Host "URL: $healthUrl"
    Write-Host "FAILED: $($_.Exception.Message)"
}

Write-Section "GET /openapi.json"
$openApiUrl = "$BackendBaseUrl/openapi.json"
try {
    $openApiResponse = Invoke-WebRequest -Uri $openApiUrl -UseBasicParsing -TimeoutSec 10
    Write-Host "URL: $openApiUrl"
    Write-Host "Status: $($openApiResponse.StatusCode)"
    $openApi = $openApiResponse.Content | ConvertFrom-Json
    $paths = @($openApi.paths.PSObject.Properties.Name)
    if ($paths -contains "/api/auth/register") {
        Write-Host "OpenAPI route present: /api/auth/register"
    } else {
        Write-Host "OpenAPI route missing: /api/auth/register"
    }
} catch {
    Write-Host "URL: $openApiUrl"
    Write-Host "FAILED: $($_.Exception.Message)"
}

Write-Section "Frontend API Base URL"
$envFiles = @(".env.local", ".env", ".env.example")
$found = $false
foreach ($envFile in $envFiles) {
    $envPath = Join-Path $frontendPath $envFile
    $value = Get-EnvValue -Path $envPath -Name "VITE_API_BASE_URL"
    if ($null -ne $value) {
        Write-Host "$envFile VITE_API_BASE_URL=$value"
        $found = $true
    }
}

if (-not $found) {
    Write-Host "VITE_API_BASE_URL not found in frontend .env.local, .env, or .env.example"
}
