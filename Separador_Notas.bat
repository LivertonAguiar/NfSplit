@echo off
chcp 65001 > nul
title Separador de Notas ^& Boletos
cd /d "C:\Users\Suporte\.gemini\antigravity\scratch\separador_notas"

rem Verifica se o usuario solicitou explicitamente a interface Tkinter
if "%~1"=="--classic" goto modo_tkinter
if "%~1"=="--tkinter" goto modo_tkinter

rem Verifica se o servidor local esta ativo na porta 5000
curl.exe -s --max-time 1 http://127.0.0.1:5000/api/config > nul 2>&1
if %errorlevel% neq 0 (
    where pythonw >nul 2>nul
    if %errorlevel% equ 0 (
        start "" pythonw app.py --porta 5000
    ) else (
        start "" python app.py --porta 5000
    )
    timeout /t 2 /nobreak > nul
)

rem Localiza Microsoft Edge ou Google Chrome para abrir em Modo Aplicativo Desktop Independente
set "APP_EXE="
if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" set "APP_EXE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if "%APP_EXE%"=="" if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" set "APP_EXE=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if "%APP_EXE%"=="" if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "APP_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
if "%APP_EXE%"=="" if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "APP_EXE=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if "%APP_EXE%"=="" if exist "%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe" set "APP_EXE=%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"

if not "%APP_EXE%"=="" (
    start "" "%APP_EXE%" --app="http://127.0.0.1:5000" --window-size=1180,840 --window-position=120,80
    exit /b 0
)

:modo_tkinter
rem Fallback para a interface Tkinter suavizada
where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw gui.py %*
) else (
    start "" python gui.py %*
)
