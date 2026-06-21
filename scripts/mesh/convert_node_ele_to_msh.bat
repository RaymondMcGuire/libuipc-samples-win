@echo off
setlocal EnableExtensions

set "SAMPLE_ROOT=%~dp0..\.."
for %%I in ("%SAMPLE_ROOT%") do set "SAMPLE_ROOT=%%~fI"

set "VENV_PY=%SAMPLE_ROOT%\.venv\Scripts\python.exe"
set "CONVERTER=%SAMPLE_ROOT%\tools\mesh\node_ele_to_msh.py"

if "%~1"=="" (
    echo Usage: scripts\mesh\convert_node_ele_to_msh.bat ^<mesh_base_or_node_file^> [converter args]
    echo Example:
    echo   scripts\mesh\convert_node_ele_to_msh.bat assets\sim_data\tetmesh_src\body_sit_1.5_80\body_sit_1.5_80 --install
    pause
    exit /b 1
)

if not exist "%VENV_PY%" (
    echo ERROR: .venv Python was not found:
    echo   %VENV_PY%
    echo Run scripts\setup\setup_local_pyuipc.bat first.
    pause
    exit /b 1
)

if not exist "%CONVERTER%" (
    echo ERROR: converter script was not found:
    echo   %CONVERTER%
    pause
    exit /b 1
)

cd /d "%SAMPLE_ROOT%" || exit /b 1
"%VENV_PY%" "%CONVERTER%" %*
exit /b %ERRORLEVEL%
