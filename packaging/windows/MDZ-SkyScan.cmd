@echo off
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
  py -3 desktop.py
) else (
  python desktop.py
)
if errorlevel 1 (
  echo Install Python 3.10 or newer from python.org and enable Add Python to PATH.
  pause
)
