@echo off
setlocal EnableExtensions

if "%~1"=="" (
    echo Usage: run_sample.bat ^<sample_folder_name^>
    echo Example: run_sample.bat 1_hello_libuipc
    pause
    exit /b 1
)

set "SAMPLE_NAME=%~1"
set "SAMPLE_ROOT=%~dp0..\.."
for %%I in ("%SAMPLE_ROOT%") do set "SAMPLE_ROOT=%%~fI"
set "VENV_PY=%SAMPLE_ROOT%\.venv\Scripts\python.exe"
set "SAMPLE_DIR=%SAMPLE_ROOT%\examples\%SAMPLE_NAME%"
set "SAMPLE_MAIN=%SAMPLE_DIR%\main.py"

cd /d "%SAMPLE_ROOT%" || exit /b 1

if not exist "%VENV_PY%" (
    echo ERROR: .venv Python was not found:
    echo   %VENV_PY%
    echo Run scripts\setup\setup_local_pyuipc.bat first.
    pause
    exit /b 1
)

if not exist "%SAMPLE_MAIN%" (
    echo ERROR: sample main.py was not found:
    echo   %SAMPLE_MAIN%
    pause
    exit /b 1
)

set "PYTHONPATH=%SAMPLE_ROOT%;%SAMPLE_ROOT%\examples;%SAMPLE_DIR%;%PYTHONPATH%"

echo Running sample: %SAMPLE_NAME%
echo   %SAMPLE_MAIN%
echo.
"%VENV_PY%" "%SAMPLE_MAIN%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo Sample failed with exit code %EXIT_CODE%.
) else (
    echo Sample finished successfully.
)
pause
exit /b %EXIT_CODE%
