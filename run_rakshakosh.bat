@echo off
setlocal

REM ======================================================
REM RakshaKosh - Air-Gapped Local Boot (Windows)
REM ======================================================

set BASE_DIR=%~dp0

echo [RakshaKosh] Starting in Air-Gapped Mode
echo [RakshaKosh] Checking model availability...
ollama list | find "phi3" >nul
if "%ERRORLEVEL%"=="0" (
    echo [RakshaKosh] Model 'phi3' found.
) else (
    echo [RakshaKosh] Model 'phi3' NOT found. Pulling...
    ollama pull phi3
)
REM Bundled Python paths (Windows venv layout)
set PYTHON_HOME=%BASE_DIR%env\python
set PYTHON_BIN=%PYTHON_HOME%\Scripts\python.exe
set PYTHONPATH=%PYTHON_HOME%\Lib\site-packages

if not exist "%PYTHON_BIN%" (
    echo [ERROR] Bundled Python not found.
    echo Expected at: %PYTHON_BIN%
    pause
    exit /b 1
)

echo [RakshaKosh] Using bundled Python: %PYTHON_BIN%

REM Start backend (blocking, foreground)
"%PYTHON_BIN%" "%BASE_DIR%backend\api\main.py"

echo [RakshaKosh] Backend stopped
pause
