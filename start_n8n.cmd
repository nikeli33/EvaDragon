@echo off

setlocal enabledelayedexpansion

:: Checking if Docker is running
echo Checking Docker status...
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not running or not installed
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)

:: Starting Docker containers
echo Starting Docker containers...
docker compose down
if %errorlevel% neq 0 (
    echo Error stopping containers
    pause
    exit /b 1
)

docker compose up -d
if %errorlevel% neq 0 (
    echo Error starting containers
    pause
    exit /b 1
)

:: Increasing waiting time and adding check
echo Waiting for n8n to start (may take up to 30 seconds)...
set "n8n_ready=0"
set "max_n8n_attempts=30"
set "n8n_attempt=0"
:check_n8n
timeout /t 1 >nul
set /a n8n_attempt+=1
curl --head --silent --fail http://localhost:5678 >nul 2>&1
if %errorlevel% == 0 (
    set "n8n_ready=1"
) else (
    if !n8n_attempt! lss !max_n8n_attempts! (
        goto check_n8n
    )
)
if !n8n_ready! == 0 (
    echo.
    echo ========================================
    echo WARNING: n8n did not start within 30 seconds
    echo Please try checking manually in a minute:
    echo 1. Open http://localhost:5678
    echo 2. Check logs: docker compose logs n8n
    echo ========================================
    echo.
)

:: Opening n8n in the browser
echo Opening n8n in the browser...
start http://localhost:5678

:: Checking container status
echo.
echo Checking container status...
docker compose ps
echo.
echo ========================================
echo Process completed!
echo If n8n didn't load, please wait a bit longer
echo and refresh the page in the browser
echo ========================================
echo.
pause
endlocal
