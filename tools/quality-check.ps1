param(
    [ValidateSet("quick", "full", "release", "smoke")]
    [string]$Mode = "full",
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
        if (Test-Path "tests") {
            Invoke-QualityStep "$AppDir unit tests" { npm run test:unit }
        }
        Invoke-QualityStep "$AppDir typecheck" { npm run typecheck }
        if (-not $EffectiveSkipBuild) {
            Invoke-QualityStep "$AppDir build" { npm run build }
        }
    }
    finally {
        Pop-Location
    }
}

if ($Mode -eq "smoke") {
    $EffectiveSkipBuild = $true
}
else {
    $EffectiveSkipBuild = [bool]$SkipBuild -or $Mode -eq "quick"
}

Write-Host "[quality] Repo: $RepoRoot"
Write-Host "[quality] Mode: $Mode"

if (-not $SkipBackend) {
    $TimeoutArgs = @(Get-PytestTimeoutArgs)
    $BackendTarget = if ($Mode -eq "smoke") { "unit/test_schemas_unit.py" } else { "unit" }
    Push-Location (Join-Path $RepoRoot "tests")
    try {
        Invoke-QualityStep "backend tests ($BackendTarget)" { python -m pytest $BackendTarget -q $TimeoutArgs }
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
