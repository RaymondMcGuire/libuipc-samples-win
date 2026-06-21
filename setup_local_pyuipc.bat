@echo off
call "%~dp0scripts\setup\setup_local_pyuipc.bat" %*
exit /b %ERRORLEVEL%
