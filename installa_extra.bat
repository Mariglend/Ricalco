@echo off
title Ricalco - pacchetti extra
cd /d "%~dp0"
echo Installo FastAPI, httpx, SQLAlchemy (unita 21-24 di Python) e pygame (progetto Invasione aliena)...
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m pip install --upgrade fastapi httpx sqlalchemy pygame
) else (
    python -m pip install --upgrade fastapi httpx sqlalchemy pygame
)
echo.
echo Fatto. Riavvia Ricalco (avvia.bat) per usarli.
pause
