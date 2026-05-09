param(
  [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiDir = Join-Path $root "cs2-api"
$webDir = Join-Path $root "cs2-web"
$adminDir = Join-Path $root "cs2-admin"

function Write-Step($message) {
  Write-Host "[CS2 Suite] $message" -ForegroundColor Cyan
}

function Assert-Command($command, $hint) {
  if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
    throw "${command} is not available. $hint"
  }
}

function Ensure-PythonDeps {
  param(
    [string]$Workdir
  )

  if ($SkipInstall) {
    return
  }

  & python -c "import fastapi, uvicorn" 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Step "Installing Python dependencies for cs2-api"
    & python -m pip install -r (Join-Path $Workdir "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
      throw "Failed to install Python dependencies for cs2-api."
    }
  }
}

function Ensure-NodeDeps {
  param(
    [string]$Workdir
  )

  if ($SkipInstall) {
    return
  }

  $nodeModules = Join-Path $Workdir "node_modules"
  if (-not (Test-Path $nodeModules)) {
    $projectName = Split-Path $Workdir -Leaf
    Write-Step "Installing Node dependencies for $projectName"
    Push-Location $Workdir
    try {
      & npm install
      if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Node dependencies for $projectName."
      }
    }
    finally {
      Pop-Location
    }
  }
}

function Start-ServiceWindow {
  param(
    [string]$Title,
    [string]$Workdir,
    [string]$Command
  )

  $escapedWorkdir = $Workdir.Replace("'", "''")
  $script = "Set-Location '$escapedWorkdir'; `$Host.UI.RawUI.WindowTitle = '$Title'; $Command"
  Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $script -WorkingDirectory $Workdir -WindowStyle Normal
}

Assert-Command "python" "Install Python 3 first."
Assert-Command "npm" "Install Node.js and npm first."

Ensure-PythonDeps -Workdir $apiDir
Ensure-NodeDeps -Workdir $webDir
Ensure-NodeDeps -Workdir $adminDir

Write-Step "Starting cs2-api"
Start-ServiceWindow -Title "cs2-api" -Workdir $apiDir -Command "python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8008"

Write-Step "Starting cs2-web"
Start-ServiceWindow -Title "cs2-web" -Workdir $webDir -Command "npm run dev"

Write-Step "Starting cs2-admin"
Start-ServiceWindow -Title "cs2-admin" -Workdir $adminDir -Command "npm run dev"

Write-Host ""
Write-Host "Launched 3 service windows:" -ForegroundColor Green
Write-Host "  API:    http://127.0.0.1:8008"
Write-Host "  Web:    http://127.0.0.1:5174"
Write-Host "  Admin:  http://127.0.0.1:5175"
Write-Host ""
Write-Host "To skip dependency checks next time:" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File .\start-all.ps1 -SkipInstall"
