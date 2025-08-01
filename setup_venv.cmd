@echo off

setlocal

echo Creating virtual environment...
py -m venv venv

if errorlevel 1 (
    echo Error: Failed to create virtual environment
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo ✅ Installation complete. To run the GUI, use:
echo venv\Scripts\activate
echo python main.py
echo.
pause
endlocal
