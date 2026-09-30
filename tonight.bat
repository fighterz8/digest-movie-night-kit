@echo off
setlocal
cd /d "%~dp0"
rem Digest Movie Night Kit: tonight's shopping trip (Windows). Checks the Movie Night list (if it's on) and searches
rem for every movie on your wishlist that isn't downloaded yet. Double-click it to run it now. To run it every
rem night, schedule it in Task Scheduler with the argument "scheduled" (see the README).
if /i "%~1"=="scheduled" (
  call :run log >> tonight-log.txt 2>&1
  exit /b
)
call :run
echo.
pause
exit /b

:run
if "%~1"=="log" echo === %date% %time%
docker info >nul 2>&1
if errorlevel 1 (
  echo   Docker Desktop isn't running, so tonight's movies were skipped.
  exit /b 1
)
docker compose run --rm --no-deps -T setup python3 /kit/setup.py tonight
exit /b
