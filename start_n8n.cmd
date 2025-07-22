@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Проверка запущен ли Docker
echo Проверка состояния Docker...
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo Ошибка: Docker не запущен или не установлен
    echo Пожалуйста, запустите Docker Desktop и попробуйте снова
    pause
    exit /b 1
)

:: Запускаем Docker контейнеры
echo Запуск Docker контейнеров...
docker compose down
if %errorlevel% neq 0 (
    echo Ошибка при остановке контейнеров
    pause
    exit /b 1
)

docker compose up -d
if %errorlevel% neq 0 (
    echo Ошибка при запуске контейнеров
    pause
    exit /b 1
)

:: Увеличиваем время ожидания и добавляем проверку
echo Ожидание запуска n8n (может занять до 30 секунд)...
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
    echo ВНИМАНИЕ: n8n не запустился за 30 секунд
    echo Попробуйте проверить вручную через минуту:
    echo 1. Откройте http://localhost:5678
    echo 2. Проверьте логи: docker compose logs n8n
    echo ========================================
    echo.
)

:: Открываем n8n в браузере
echo Открытие n8n в браузере...
start http://localhost:5678

:: Проверяем статус контейнеров
echo.
echo Проверка состояния контейнеров...
docker compose ps
echo.
echo ========================================
echo Процесс завершен!
echo Если n8n не загрузился, подождите ещё немного
echo и обновите страницу в браузере
echo ========================================
echo.
pause
endlocal 