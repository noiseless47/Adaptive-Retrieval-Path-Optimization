param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$FrontendDir = Join-Path $Root "frontend"
$LogDir = Join-Path $Root ".dev"
$BackendOutLog = Join-Path $LogDir "backend.out.log"
$BackendErrLog = Join-Path $LogDir "backend.err.log"
$FrontendOutLog = Join-Path $LogDir "frontend.out.log"
$FrontendErrLog = Join-Path $LogDir "frontend.err.log"

function Write-Info($Message) {
    Write-Host "[ARPO] $Message" -ForegroundColor Cyan
}

function Write-Warn($Message) {
    Write-Host "[ARPO] $Message" -ForegroundColor Yellow
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [string]$Name,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                Write-Info "$Name ready at $Url"
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 750
        }
    }

    Write-Warn "$Name did not become ready within $TimeoutSeconds seconds. Check its log."
    return $false
}

if (-not (Test-Path -LiteralPath $FrontendDir)) {
    throw "Frontend directory not found: $FrontendDir"
}

if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "package.json"))) {
    throw "Frontend package.json not found: $FrontendDir"
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
Set-Content -LiteralPath $BackendOutLog -Value ""
Set-Content -LiteralPath $BackendErrLog -Value ""
Set-Content -LiteralPath $FrontendOutLog -Value ""
Set-Content -LiteralPath $FrontendErrLog -Value ""

if ($Install) {
    Write-Info "Installing backend API dependencies..."
    Push-Location $Root
    try {
        & python -m pip install -e ".[api]"
    } finally {
        Pop-Location
    }

    Write-Info "Installing frontend dependencies..."
    Push-Location $FrontendDir
    try {
        & npm install
    } finally {
        Pop-Location
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) {
    Write-Warn "frontend/node_modules is missing. Run scripts/start-dev.ps1 -Install or run npm install in frontend/."
}

$ViteScript = Join-Path $FrontendDir "node_modules\vite\bin\vite.js"
if (-not (Test-Path -LiteralPath $ViteScript)) {
    throw "Vite is not installed. Run scripts/start-dev.ps1 -Install or run npm install in frontend/."
}

Write-Info "Starting backend on http://127.0.0.1:$BackendPort"
$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $Root "src"
    $BackendProcess = Start-Process `
        -FilePath "python" `
        -ArgumentList @("-m", "uvicorn", "arpo.api.main:app", "--reload", "--host", "127.0.0.1", "--port", "$BackendPort") `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $BackendOutLog `
        -RedirectStandardError $BackendErrLog `
        -WindowStyle Hidden `
        -PassThru
} finally {
    $env:PYTHONPATH = $PreviousPythonPath
}

Write-Info "Starting frontend on http://127.0.0.1:$FrontendPort"
$FrontendProcess = Start-Process `
    -FilePath "node" `
    -ArgumentList @($ViteScript, "--host", "127.0.0.1", "--port", "$FrontendPort") `
    -WorkingDirectory $FrontendDir `
    -RedirectStandardOutput $FrontendOutLog `
    -RedirectStandardError $FrontendErrLog `
    -WindowStyle Hidden `
    -PassThru

try {
    Wait-ForUrl -Url "http://127.0.0.1:$BackendPort/health" -Name "Backend" | Out-Null
    Wait-ForUrl -Url "http://127.0.0.1:$FrontendPort/" -Name "Frontend" | Out-Null

    Write-Host ""
    Write-Host "ARPO dev stack is running" -ForegroundColor Green
    Write-Host "Backend:  http://127.0.0.1:$BackendPort"
    Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
    Write-Host "Logs:"
    Write-Host "  Backend stdout:  $BackendOutLog"
    Write-Host "  Backend stderr:  $BackendErrLog"
    Write-Host "  Frontend stdout: $FrontendOutLog"
    Write-Host "  Frontend stderr: $FrontendErrLog"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop both processes." -ForegroundColor Yellow

    while ($true) {
        Start-Sleep -Seconds 1
        if ($BackendProcess.HasExited) {
            Write-Warn "Backend process exited. Check $BackendOutLog and $BackendErrLog"
            break
        }
        if ($FrontendProcess.HasExited) {
            Write-Warn "Frontend process exited. Check $FrontendOutLog and $FrontendErrLog"
            break
        }
    }
} finally {
    Write-Info "Stopping ARPO dev stack..."
    foreach ($process in @($BackendProcess, $FrontendProcess)) {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
