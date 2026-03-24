# libuipc-samples

A sample library for Libuipc.

This library is a collection of sample programs that demonstrate how to use the Libuipc library.

## Install (uv recommended)

### From PyPI

Install all dependencies including `pyuipc` from PyPI:

```bash
uv sync
```

> **Note:** The PyPI version of `pyuipc` only supports CUDA 12.8. If you need a different CUDA version, use the "Build from source" method below.

### Build from source

If you want to use a `pyuipc` built from source, first install only the other dependencies (without `pyuipc`):

```bash
uv sync --only-group dev
```

Then install your locally built `pyuipc` wheel:

```bash
uv pip install pyuipc-<version>.whl
```

For build instructions, refer to the [Libuipc documentation](https://spirimirror.github.io/libuipc-doc/build_install/).
