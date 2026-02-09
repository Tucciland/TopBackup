@echo off
REM TopBackup - Remover Serviço Windows
REM Execute como Administrador

setlocal

echo ==========================================
echo    TopBackup - Remocao do Servico
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
    pause
    exit /b 1
)

set /p CONFIRMA="Tem certeza que deseja remover o servico? (S/N): "
if /i not "%CONFIRMA%"=="S" (
    echo Operacao cancelada
    pause
    exit /b 0
)

echo.
echo Parando servico...
"%EXE_PATH%" --stop

echo.
echo Removendo servico...
"%EXE_PATH%" --uninstall

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Servico removido com sucesso!
) else (
    echo.
    echo Falha na remocao do servico
)

echo.
pause
