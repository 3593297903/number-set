@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 goto missing_python
py -3.13 -c "import sys,struct; assert sys.version_info[:2] == (3,13) and struct.calcsize('P') == 8"
if errorlevel 1 goto missing_python

if exist ".venv\Scripts\python.exe" goto environment_ready
py -3.13 -m venv ".venv"
if errorlevel 1 goto failed

:environment_ready
".venv\Scripts\python.exe" -c "import sys,struct; assert sys.version_info[:2] == (3,13) and struct.calcsize('P') == 8"
if errorlevel 1 goto wrong_environment
".venv\Scripts\python.exe" -m pip --isolated install --disable-pip-version-check --index-url https://pypi.org/simple -r "requirements-dev.lock"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip --isolated install --disable-pip-version-check --no-build-isolation --no-deps -e .
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -I -c "import number_app; from PySide6.QtWidgets import QApplication; print('Application imports OK')"
if errorlevel 1 goto failed
echo.
echo Setup complete. Run start.cmd to open the application.
if /i not "%~1"=="--no-pause" pause
exit /b 0

:missing_python
echo Install Windows Python 3.13 x64 with the Python launcher, then run setup.cmd again.
if /i not "%~1"=="--no-pause" pause
exit /b 2

:wrong_environment
echo The existing .venv is not Python 3.13 x64. Keep your data and create a compatible environment.
if /i not "%~1"=="--no-pause" pause
exit /b 2

:failed
echo Setup failed. Check the error above and your network connection, then retry.
if /i not "%~1"=="--no-pause" pause
exit /b 1
