@echo off
chcp 65001 >nul
setlocal

echo 🛠 Запуск сборки GUI с помощью PyInstaller...

:: Переход в директорию проекта
cd /d %~dp0

:: Проверка виртуального окружения
if not exist "venv\Scripts\activate.bat" (
    echo 🔍 Виртуальное окружение не найдено. Запускаем setup_venv.cmd...
    if exist setup_venv.cmd (
        call setup_venv.cmd
    ) else (
        echo ❌ Файл setup_venv.cmd не найден. Невозможно продолжить.
        pause
        exit /b 1
    )
)

:: Повторная проверка после setup_venv.cmd
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Не удалось создать виртуальное окружение. Сборка прервана.
    pause
    exit /b 1
)

:: Активация окружения
call venv\Scripts\activate.bat

:: Проверка и установка PyInstaller
echo Проверка PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 🔄 Установка PyInstaller...
    pip install pyinstaller
)

:: Очистка предыдущих сборок
echo 🧹 Очистка предыдущих сборок...
rmdir /s /q build dist main.spec 2>nul

:: Сборка .exe файла
echo ⚙ Сборка .exe файла...
pyinstaller --noconfirm --onefile --windowed --icon=assets/icon.ico ^
    --add-data "assets;assets" --name=Eva main.py

echo.
echo ✅ Сборка завершена!
echo ▶ Готовый файл: dist\Eva.exe
pause
endlocal 
