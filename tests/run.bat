@echo off
REM ═══════════════════════════════════════════════════════════════
REM CS2 Tactics Suite — Test Runner (Windows)
REM ═══════════════════════════════════════════════════════════════

setlocal enabledelayedexpansion
cd /d "%~dp0"

set API_BASE=%TEST_API_BASE%
if "%API_BASE%"=="" set API_BASE=http://127.0.0.1:8008
set ALLURE_ARGS=
set PYTEST_EXTRA=

:parse_args
if "%~1"=="" goto after_parse
if "%~1"=="--allure" (
    set ALLURE_ARGS=--alluredir=allure-results --clean-alluredir
    shift
    goto parse_args
)
set PYTEST_EXTRA=!PYTEST_EXTRA! %1
shift
goto parse_args

:after_parse

echo [TEST] Checking API health at %API_BASE%...
curl -sf "%API_BASE%/api/health" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] API is not reachable at %API_BASE%
    echo        Start it first: cd cs2-api ^&^& uvicorn app.main:app --host 0.0.0.0 --port 8008
    exit /b 1
)
echo [TEST] API OK

REM Install deps if needed
python -c "import pytest" 2>nul
if errorlevel 1 (
    echo [TEST] Installing dependencies...
    pip install -r requirements-test.txt
)

REM Run API tests
echo [TEST] Running API tests...
python -m pytest api/ -v --tb=short --color=yes %ALLURE_ARGS% %PYTEST_EXTRA%

if errorlevel 1 (
    echo [FAIL] Some tests failed
) else (
    echo [PASS] All tests passed
)

if not "%ALLURE_ARGS%"=="" (
    echo.
    echo Allure results saved to allure-results\
    echo View: allure serve allure-results
)
pause
