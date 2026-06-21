# libuipc-samples

A sample library for Libuipc.

This library is a collection of sample programs that demonstrate how to use the Libuipc library.

## Install (uv recommended)

Install base dependencies (without `pyuipc`):

```bash
uv sync
```

### pyuipc from PyPI

```bat
scripts\setup\setup_pypi_pyuipc.bat
```

> **Note:** The PyPI version of `pyuipc` only supports CUDA 12.8. If you need a different CUDA version, use the "Build from source" method below.

### pyuipc from source

Place `libuipc-win` and `libuipc-samples-win` next to each other, then run:

```bat
scripts\setup\setup_local_pyuipc.bat
```

If `libuipc-win` is somewhere else, pass its path:

```bat
scripts\setup\setup_local_pyuipc.bat D:\path\to\libuipc-win
```

The script creates the sample `.venv`, configures and builds `libuipc` with that Python, builds a matching local `pyuipc` wheel, installs it, and runs smoke tests.

Useful overrides:

```bat
set SAMPLES_PYTHON=3.13
set CMAKE_TOOLCHAIN_FILE=D:\soft\vcpkg\scripts\buildsystems\vcpkg.cmake
set BUILD_PARALLEL=8
set BUILD_TARGET=pyuipc
scripts\setup\setup_local_pyuipc.bat
```

Run a sample after setup:

```bat
scripts\run\run_sample.bat 1_hello_libuipc
```
