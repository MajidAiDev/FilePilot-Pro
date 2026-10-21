@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 main.py
) else (
  python main.py
)
if errorlevel 1 (
  echo.
  echo FilePilot could not start. Confirm Python 3 and Tkinter are installed.
  pause
)
endlocal
