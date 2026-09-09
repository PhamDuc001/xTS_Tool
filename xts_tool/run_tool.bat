@echo off
cd /d "%~dp0"
echo Starting xTS Pre-Setup Manager...
py -3 main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred while launching the tool.
    pause
)
