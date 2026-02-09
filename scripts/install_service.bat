@echo off
REM TopBackup - Instalar Serviço Windows
REM Execute como Administrador

setlocal

echo ==========================================
echo    TopBackup - Instalacao do Servico
echo ==========================================
echo.

REM Verifica privilégios de administrador
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Este script precisa ser executado como Administrador
    echo.
    echo Clique com botao direito e selecione "Executar como administrador"
    pause
    exit /b 1
)

set SCRIPT_DIR=%~dp0
set APP_DIR=%SCRIPT_DIR%..
set EXE_PATH=%APP_DIR%\TopBackup.exe

REM Verifica se o executável existe
if not exist "%EXE_PATH%" (
    echo ERRO: Executavel nao encontrado: %EXE_PATH%
    echo.
    echo Execute primeiro o script build.bat para gerar o executavel
    pause
    exit /b 1
)

echo Instalando servico TopBackup...
echo.

"%EXE_PATH%" --install

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Servico instalado com sucesso!
    echo.

    set /p INICIAR="Deseja iniciar o servico agora? (S/N): "
    if /i "%INICIAR%"=="S" (
        echo.
        echo Iniciando servico...
        "%EXE_PATH%" --start
    )
) else (
    echo.
    echo Falha na instalacao do servico
)

echo.
pause
