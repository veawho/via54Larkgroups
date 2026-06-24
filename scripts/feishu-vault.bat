@echo off
REM via54Larkgroups Windows wrapper
REM Usage: feishu-vault <command> [args...]
setlocal
set HERE=%~dp0
set PROJECT_ROOT=%HERE%..
set PYEXE=C:\Users\via54\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe
"%PYEXE%" -m via54_larkgroups %*
endlocal