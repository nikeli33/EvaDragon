@echo off

setlocal

echo Starting GUI build with PyInstaller...

:: Changing to project directory
cd /d %~dp0

:: Checking for virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Running setup_venv.cmd...
    if exist setup_venv.cmd (
        call setup_venv.cmd
    ) else (
        echo setup_venv.cmd file not found. Cannot proceed.
        pause
        exit /b 1
    )
)

:: Re-check after running setup_venv.cmd
if not exist "venv\Scripts\activate.bat" (
    echo Failed to create virtual environment. Build interrupted.
    pause
    exit /b 1
)

:: Activating the environment
call venv\Scripts\activate.bat

:: Checking and installing PyInstaller
echo Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: Cleaning up previous builds
echo Cleaning up previous builds...
rmdir /s /q build dist main.spec 2>nul

:: Building the .exe file
echo Building .exe file...
pyinstaller --noconfirm --onefile --windowed --icon=assets/icon.ico ^
    --add-data "assets;assets" --name=Eva main.py

echo.
echo Build completed!
echo ▶ Output file: dist\Eva.exe
pause
endlocal
