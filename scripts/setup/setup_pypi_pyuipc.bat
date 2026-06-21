@echo off
setlocal EnableExtensions

set "SAMPLE_ROOT=%~dp0..\.."
for %%I in ("%SAMPLE_ROOT%") do set "SAMPLE_ROOT=%%~fI"

if not defined SAMPLES_PYTHON set "SAMPLES_PYTHON=3.13"
set "VENV_PY=%SAMPLE_ROOT%\.venv\Scripts\python.exe"

cd /d "%SAMPLE_ROOT%" || exit /b 1

echo [libuipc-samples] Project: %SAMPLE_ROOT%
echo [libuipc-samples] Python request: %SAMPLES_PYTHON%
echo.

where uv >nul 2>nul
if errorlevel 1 (
    echo ERROR: uv was not found in PATH.
    echo Install uv first, then rerun this file.
    pause
    exit /b 1
)

echo [1/2] Syncing sample environment with pyuipc from PyPI...
uv sync --python "%SAMPLES_PYTHON%" --group pypi
if errorlevel 1 goto :fail

echo.
echo [2/2] Running import smoke test...
"%VENV_PY%" -c "import uipc; print('uipc', uipc.__version__, uipc.__file__)"
if errorlevel 1 goto :fail

echo.
echo Setup complete with pyuipc from PyPI.
echo Note: the PyPI wheel may require a specific CUDA version.
pause
exit /b 0

:fail
echo.
echo ERROR: setup failed. Check the message above.
pause
exit /b 1
