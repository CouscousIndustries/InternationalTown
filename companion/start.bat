@echo off
chcp 65001 >nul
rem InternationalTown - starts the translation companion
cd /d "%~dp0"
title InternationalTown - translator

if not exist settings.json (
    echo First start: installing the translator...
    call install.bat
    if not exist settings.json exit /b 1
)

.venv\Scripts\python translator.py %*
pause
