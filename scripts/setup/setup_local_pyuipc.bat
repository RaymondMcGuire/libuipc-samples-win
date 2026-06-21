@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SAMPLE_ROOT=%~dp0..\.."
for %%I in ("%SAMPLE_ROOT%") do set "SAMPLE_ROOT=%%~fI"

if not "%~1"=="" set "LIBUIPC_ROOT=%~1"
if not defined LIBUIPC_ROOT set "LIBUIPC_ROOT=%SAMPLE_ROOT%\..\libuipc-win"
for %%I in ("%LIBUIPC_ROOT%") do set "LIBUIPC_ROOT=%%~fI"

if not defined SAMPLES_PYTHON set "SAMPLES_PYTHON=3.13"
if not defined BUILD_CONFIG set "BUILD_CONFIG=Release"
if not defined BUILD_PARALLEL set "BUILD_PARALLEL=8"
if not defined BUILD_TARGET set "BUILD_TARGET=pyuipc"
if not defined LIBUIPC_BUILD_DIR set "LIBUIPC_BUILD_DIR=%LIBUIPC_ROOT%\build\pyuipc_samples"

set "VENV_PY=%SAMPLE_ROOT%\.venv\Scripts\python.exe"
set "PYUIPC_SRC=%LIBUIPC_BUILD_DIR%\python"
set "WHEELHOUSE=%LIBUIPC_BUILD_DIR%\wheelhouse"
set "BUILD_WHEEL_PY=%LIBUIPC_ROOT%\scripts\build_pyuipc_wheel.py"

cd /d "%SAMPLE_ROOT%" || exit /b 1

echo [libuipc-samples] Project: %SAMPLE_ROOT%
echo [libuipc-samples] Libuipc: %LIBUIPC_ROOT%
echo [libuipc-samples] Python request: %SAMPLES_PYTHON%
echo [libuipc-samples] Build dir: %LIBUIPC_BUILD_DIR%
echo.

where uv >nul 2>nul
if errorlevel 1 (
    echo ERROR: uv was not found in PATH.
    echo Install uv first, then rerun this file.
    pause
    exit /b 1
)

where cmake >nul 2>nul
if errorlevel 1 (
    echo ERROR: cmake was not found in PATH.
    echo Install CMake or open a shell where CMake is available.
    pause
    exit /b 1
)

if not exist "%LIBUIPC_ROOT%\CMakeLists.txt" (
    echo ERROR: Could not find libuipc project root:
    echo   %LIBUIPC_ROOT%
    echo.
    echo Usage:
    echo   scripts\setup\setup_local_pyuipc.bat D:\path\to\libuipc-win
    echo.
    echo Or set LIBUIPC_ROOT before running this file.
    pause
    exit /b 1
)

if not exist "%BUILD_WHEEL_PY%" (
    echo ERROR: Could not find wheel builder:
    echo   %BUILD_WHEEL_PY%
    echo Make sure LIBUIPC_ROOT points to the libuipc-win project.
    pause
    exit /b 1
)

if not defined CMAKE_TOOLCHAIN_FILE if exist "%VCPKG_ROOT%\scripts\buildsystems\vcpkg.cmake" (
    set "CMAKE_TOOLCHAIN_FILE=%VCPKG_ROOT%\scripts\buildsystems\vcpkg.cmake"
)

if not defined CMAKE_TOOLCHAIN_FILE if exist "%LIBUIPC_ROOT%\build\CMakeCache.txt" (
    for /f "tokens=1,* delims==" %%A in ('findstr /b /c:"CMAKE_TOOLCHAIN_FILE:FILEPATH=" "%LIBUIPC_ROOT%\build\CMakeCache.txt" 2^>nul') do (
        set "CMAKE_TOOLCHAIN_FILE=%%B"
    )
)

if not defined CMAKE_TOOLCHAIN_FILE (
    echo ERROR: CMAKE_TOOLCHAIN_FILE is not set.
    echo.
    echo Set it to vcpkg.cmake, for example:
    echo   set CMAKE_TOOLCHAIN_FILE=D:\soft\vcpkg\scripts\buildsystems\vcpkg.cmake
    echo.
    echo Or set VCPKG_ROOT to your vcpkg directory.
    pause
    exit /b 1
)

if not exist "%CMAKE_TOOLCHAIN_FILE%" (
    echo ERROR: CMAKE_TOOLCHAIN_FILE does not exist:
    echo   %CMAKE_TOOLCHAIN_FILE%
    pause
    exit /b 1
)

echo [1/6] Syncing sample environment and pyuipc build tools...
uv sync --python "%SAMPLES_PYTHON%" --group build-pyuipc
if errorlevel 1 goto :fail

if not exist "%VENV_PY%" (
    echo ERROR: sample virtual environment Python was not created:
    echo   %VENV_PY%
    pause
    exit /b 1
)

echo.
echo [libuipc-samples] Python selected by uv:
"%VENV_PY%" -c "import sys; print('  ' + sys.executable); print('  ' + sys.version)"
if errorlevel 1 goto :fail

echo.
echo [2/6] Configuring libuipc with the sample Python...
cmake -S "%LIBUIPC_ROOT%" -B "%LIBUIPC_BUILD_DIR%" ^
    -DCMAKE_TOOLCHAIN_FILE="%CMAKE_TOOLCHAIN_FILE%" ^
    -DUIPC_BUILD_PYBIND=ON ^
    -DUIPC_BUILD_PYTHON_WHEEL=ON ^
    -DUIPC_BUILD_EXAMPLES=OFF ^
    -DUIPC_BUILD_TESTS=OFF ^
    -DUIPC_BUILD_BENCHMARKS=OFF ^
    -DUIPC_BUILD_GUI=OFF ^
    -DUIPC_PYTHON_EXECUTABLE_PATH="%VENV_PY%" ^
    %UIPC_EXTRA_CMAKE_ARGS%
if errorlevel 1 goto :fail

echo.
echo [3/6] Building libuipc and pyuipc...
cmake --build "%LIBUIPC_BUILD_DIR%" --config "%BUILD_CONFIG%" --target "%BUILD_TARGET%" --parallel %BUILD_PARALLEL%
if errorlevel 1 goto :fail

if not exist "%PYUIPC_SRC%\pyproject.toml" (
    echo ERROR: Could not find generated pyuipc package:
    echo   %PYUIPC_SRC%
    echo Check the libuipc build output above.
    pause
    exit /b 1
)

if not exist "%WHEELHOUSE%" mkdir "%WHEELHOUSE%"

echo.
echo [4/6] Building local pyuipc wheel...
"%VENV_PY%" "%BUILD_WHEEL_PY%" "%PYUIPC_SRC%" "%WHEELHOUSE%"
if errorlevel 1 goto :fail

set "WHEEL="
for /f "delims=" %%F in ('dir /b /a:-d /o:-d "%WHEELHOUSE%\pyuipc-*.whl" 2^>nul') do (
    set "WHEEL=%WHEELHOUSE%\%%F"
    goto :have_wheel
)

:have_wheel
if not defined WHEEL (
    echo ERROR: No pyuipc wheel was produced in:
    echo   %WHEELHOUSE%
    pause
    exit /b 1
)

echo.
echo [5/6] Installing local wheel into samples .venv...
echo   !WHEEL!
uv pip install --python "%VENV_PY%" "!WHEEL!" --force-reinstall
if errorlevel 1 goto :fail

echo.
echo [6/6] Running smoke tests...
"%VENV_PY%" -c "import uipc; print('uipc', uipc.__version__, uipc.__file__)"
if errorlevel 1 goto :fail
"%VENV_PY%" -c "from uipc import Engine; Engine('cuda', 'output/smoke'); print('cuda ok')"
if errorlevel 1 goto :fail

echo.
echo Setup complete. You can now run BAT files in scripts\run\run_samples.
pause
exit /b 0

:fail
echo.
echo ERROR: setup failed. Check the message above.
pause
exit /b 1
