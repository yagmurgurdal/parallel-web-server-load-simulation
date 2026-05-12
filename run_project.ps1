param(
    [switch]$UseDocker,
    [switch]$SkipInstall,
    [int]$DelayMs = 100
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$serverDir = Join-Path $projectRoot "server"
$loadTesterRequirements = Join-Path $projectRoot "load_tester\requirements.txt"
$loadTesterScript = Join-Path $projectRoot "load_tester\load_test.py"
$resultsFile = Join-Path $projectRoot "results\test_results.csv"
$serverUrl = "http://localhost:3000/health"

function Test-CommandExists {
    param([string]$CommandName)

    return $null -ne (Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Wait-ForServer {
    param(
        [string]$Url,
        [int]$Retries = 30,
        [int]$DelayMilliseconds = 1000
    )

    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Host "Server is ready: $Url"
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds $DelayMilliseconds
        }
    }

    throw "Server did not become ready at $Url"
}

if ($UseDocker) {
    Write-Host "Starting project with Docker Compose..."
    Push-Location $projectRoot
    try {
        docker compose up --build -d server
        docker compose run --rm load_tester
        Write-Host "Results saved to $resultsFile"
    }
    finally {
        docker compose down
        Pop-Location
    }

    exit 0
}

if (-not (Test-CommandExists "python")) {
    throw "Python is not installed or not available in PATH."
}

if (-not (Test-CommandExists "npm.cmd")) {
    throw "npm.cmd is not installed or not available in PATH."
}

if (-not (Test-Path $resultsFile)) {
    New-Item -ItemType File -Force -Path $resultsFile | Out-Null
}

if (-not $SkipInstall) {
    Write-Host "Installing Node.js dependencies..."
    Push-Location $serverDir
    try {
        & npm.cmd install
    }
    finally {
        Pop-Location
    }

    Write-Host "Installing Python dependencies..."
    Push-Location $projectRoot
    try {
        & python -m pip install -r $loadTesterRequirements
    }
    finally {
        Pop-Location
    }
}

$serverJob = $null

Push-Location $projectRoot
try {
    Write-Host "Starting Node.js server..."
    $serverJob = Start-Job -ScriptBlock {
        param($WorkingDirectory)
        Set-Location $WorkingDirectory
        & node server.js
    } -ArgumentList $serverDir

    Wait-ForServer -Url $serverUrl

    $env:SIMULATION_DELAY_MS = "$DelayMs"

    Write-Host "Running load test..."
    & python $loadTesterScript

    Write-Host "Results saved to $resultsFile"
}
finally {
    if ($serverJob) {
        Stop-Job $serverJob -ErrorAction SilentlyContinue | Out-Null
        Remove-Job $serverJob -Force -ErrorAction SilentlyContinue | Out-Null
    }

    Pop-Location
}
