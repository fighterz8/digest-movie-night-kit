@echo off
cd /d "%~dp0"
echo.
echo   Stopping the Digest Movie Night Kit...
docker compose stop
echo.
echo   Stopped. Your movies and settings are kept. Double-click start to bring it back.
echo.
pause
