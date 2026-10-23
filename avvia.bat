@echo off
title Ricalco
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 server.py
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python server.py
    ) else (
        echo Python non trovato. Installalo da https://www.python.org/downloads/ e spunta "Add python.exe to PATH".
    )
)
pause
