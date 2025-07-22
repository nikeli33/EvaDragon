@echo off
chcp 65001 >nul
setlocal

echo Создание виртуального окружения...
python -m venv venv

if errorlevel 1 (
    echo Ошибка: Не удалось создать виртуальное окружение
    pause
    exit /b 1
)

echo Активация виртуального окружения...
call venv\Scripts\activate.bat

echo Обновление pip...
python -m pip install --upgrade pip

echo Установка зависимостей из requirements.txt...
pip install -r requirements.txt

echo.
echo ✅ Установка завершена. Для запуска GUI выполните:
echo venv\Scripts\activate
echo python main.py
echo.
pause
endlocal 