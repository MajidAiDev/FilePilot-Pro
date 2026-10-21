@echo off
setlocal
cd /d "%~dp0"
echo Installing FilePilot language rendering dependencies...
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m pip install -r requirements.txt
  if errorlevel 1 goto install_failed
  py -3 main.py
) else (
  python -m pip install -r requirements.txt
  if errorlevel 1 goto install_failed
  python main.py
)
if errorlevel 1 goto launch_failed
goto end

:install_failed
echo.
echo Dependency installation failed. Check your internet connection and Python/pip setup.
echo FilePilot can run in English without these optional Persian/Arabic shaping packages.
pause
goto end

:launch_failed
echo.
echo FilePilot could not start. Confirm Python 3 and Tkinter are installed.
pause

:end
endlocal
