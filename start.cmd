@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing_environment
".venv\Scripts\python.exe" -I -m number_app gui --data-dir "%~dp0data"
set "numberExitCode=%errorlevel%"
if not "%numberExitCode%"=="0" (
    echo The application stopped with an error. Run setup.cmd and check the message above.
    pause
)
exit /b %numberExitCode%

:missing_environment
echo Run setup.cmd once before starting the application.
pause
exit /b 2
