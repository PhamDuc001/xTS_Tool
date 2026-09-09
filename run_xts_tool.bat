@echo off
cd /d "%~dp0xts_tool"
echo Launching xTS Pre-Setup Tool...
py -3 main.py
if %ERRORLEVEL% NEQ 0 (
    pause
)
