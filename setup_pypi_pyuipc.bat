@echo off
call "%~dp0scripts\setup\setup_pypi_pyuipc.bat" %*
exit /b %ERRORLEVEL%
