param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Invoke-QualityStep {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "[quality] $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

function Get-PytestTimeoutArgs {
    & python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pytest_timeout') else 1)" *> $null
    if ($LASTEXITCODE -eq 0) {
        return @("--timeout=60")
    }
    Write-Host "[quality] pytest-timeout not installed; running without --timeout"
    return @()
}

function Invoke-NodeAppChecks {
    param([string]$AppDir)

    Push-Location (Join-Path $RepoRoot $AppDir)
    try {
        Invoke-QualityStep "$AppDir typecheck" { npm run typecheck }
        if (-not $SkipBuild) {
            Invoke-QualityStep "$AppDir build" { npm run build }
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "[quality] Repo: $RepoRoot"

if (-not $SkipBackend) {
    $TimeoutArgs = @(Get-PytestTimeoutArgs)
    Push-Location (Join-Path $RepoRoot "tests")
    try {
        Invoke-QualityStep "backend unit tests" { python -m pytest unit -q $TimeoutArgs }
    }
    finally {
        Pop-Location
    }
}

if (-not $SkipFrontend) {
    Invoke-NodeAppChecks "cs2-web"
    Invoke-NodeAppChecks "cs2-admin"
}

Invoke-QualityStep "git whitespace check" { git diff --check }

Write-Host ""
Write-Host "[quality] All checks passed"
