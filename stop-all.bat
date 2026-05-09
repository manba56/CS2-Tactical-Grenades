@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\stop-all.ps1"
endlocal
