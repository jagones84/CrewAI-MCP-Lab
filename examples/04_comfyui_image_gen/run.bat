@echo off
REM Convenience launcher for example 04.
setlocal
set "PYTHONPATH=%~dp0src;%~dp0..\..\src;%PYTHONPATH%"
"%~dp0..\..\..\venv\Scripts\python.exe" "%~dp0src\main.py"
endlocal
