@echo off
setlocal
cd /d "%~dp0"
title Digest Movie Night Kit
echo.
echo   Digest Movie Night Kit
echo   ======================
echo.

docker info >nul 2>&1
if errorlevel 1 (
  echo   Docker Desktop isn't running yet.
  echo   Open Docker Desktop, wait until it says it's running, then double-click start again.
  echo.
  pause
  exit /b 1
)

findstr /b /c:"PASSWORD=change-me" settings.txt >nul
if not errorlevel 1 (
  echo   First, pick a password. settings.txt is opening in Notepad:
  echo   change the PASSWORD line, save, close Notepad, then double-click start again.
  echo.
  start "" notepad settings.txt
  pause
  exit /b 1
)

echo "%CD%" | findstr /i "OneDrive" >nul
if not errorlevel 1 (
  echo   This folder is inside OneDrive, so your movies would upload to OneDrive.
  echo   Move the whole folder somewhere else, like C:\MovieNight, then double-click start again.
  echo.
  pause
  exit /b 1
)

if not exist "media\movies" mkdir "media\movies"
if not exist "media\downloads" mkdir "media\downloads"
rem Jellyfin skips an empty movies folder (so the first movie wouldn't show up); this note keeps it non-empty.
if not exist "media\movies\README.txt" (echo Your movies appear here, one folder per film. Radarr names them, so leave the names as they are.) > "media\movies\README.txt"

echo   Starting the apps. The first time takes a few minutes while they download...
docker compose up -d
if errorlevel 1 (
  echo.
  echo   Something went wrong starting the apps. The messages above say why.
  pause
  exit /b 1
)

echo.
echo   Connecting everything...
docker compose wait setup >nul
if errorlevel 1 (
  echo.
  echo   Setup hit a problem. Here's what it said:
  docker compose logs --no-log-prefix --tail 15 setup
  pause
  exit /b 1
)

set "LANIP="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1).IPv4Address.IPAddress"`) do set "LANIP=%%i"

echo.
echo   READY!
echo.
echo     Add movies, in Radarr:   http://localhost:7878
echo     Watch, in Jellyfin:      http://localhost:8096
if defined LANIP echo     On your TV or phone:     http://%LANIP%:8096
echo.
echo   Your movies are saved in %CD%\media\movies
echo.
start "" "http://localhost:7878"
start "" "http://localhost:8096"
pause
