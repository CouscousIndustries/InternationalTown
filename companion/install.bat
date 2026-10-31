@echo off
chcp 65001 >nul
rem InternationalTown - translator installer
cd /d "%~dp0"
title InternationalTown - translator installation

rem "python" may be a fake Microsoft Store shortcut: check that it really runs
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 (
    echo.
    echo   Python 3.10 or newer is required.
    echo   Install it from https://www.python.org/downloads/
    echo   and tick "Add python.exe to PATH" during the installation.
    echo.
    if /i not "%~1"=="nopause" pause
    exit /b 1
)

if not exist .venv\Scripts\python.exe (
    echo Creating the Python environment...
    python -m venv .venv || (echo Could not create the Python environment. & if /i not "%~1"=="nopause" pause & exit /b 1)
    .venv\Scripts\python -m pip install --upgrade pip --disable-pip-version-check -q
)

.venv\Scripts\python install.py
echo.
if /i not "%~1"=="nopause" pause
