$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = Join-Path $root ".runtime"

function Write-Step($message) {
  Write-Host "[CS2 Suite] $message" -ForegroundColor Cyan
}

function Stop-ServiceByPidFile {
  param(
    [string]$Name
  )

  $pidFile = Join-Path $runtimeDir "$Name.pid"
  if (-not (Test-Path $pidFile)) {
    Write-Host "$Name is not tracked by PID file, skipping." -ForegroundColor Yellow
    return
  }

  $rawPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $rawPid) {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host "$Name PID file was empty and has been removed." -ForegroundColor Yellow
    return
  }

  $processId = 0
  if (-not [int]::TryParse($rawPid, [ref]$processId)) {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host "$Name PID file was invalid and has been removed." -ForegroundColor Yellow
    return
  }

  $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
  if ($null -eq $process) {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host "$Name process was already stopped." -ForegroundColor Yellow
    return
  }

  Write-Step "Stopping $Name (PID $processId)"
  Stop-Process -Id $processId -Force
  Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path $runtimeDir)) {
  Write-Host "No .runtime directory found. Nothing to stop." -ForegroundColor Yellow
  exit 0
}

Stop-ServiceByPidFile -Name "cs2-api"
Stop-ServiceByPidFile -Name "cs2-web"
Stop-ServiceByPidFile -Name "cs2-admin"

$remaining = Get-ChildItem -LiteralPath $runtimeDir -Force -ErrorAction SilentlyContinue
if ($null -eq $remaining -or $remaining.Count -eq 0) {
  Remove-Item -LiteralPath $runtimeDir -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Requested shutdown for tracked CS2 services." -ForegroundColor Green
