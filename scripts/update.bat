@echo off
REM TopBackup - Script de Atualização Automática
REM Este script é executado para aplicar atualizações do aplicativo

setlocal enabledelayedexpansion

echo ==========================================
echo    TopBackup - Atualizacao Automatica
echo ==========================================
echo.

REM Diretório do script
set SCRIPT_DIR=%~dp0
set APP_DIR=%SCRIPT_DIR%..
set UPDATE_DIR=%APP_DIR%\update
set BACKUP_DIR=%APP_DIR%\backup_update

REM Arquivos
set NEW_EXE=%UPDATE_DIR%\TopBackup_new.exe
set CURRENT_EXE=%APP_DIR%\TopBackup.exe
set BACKUP_EXE=%BACKUP_DIR%\TopBackup_backup.exe

echo Diretorio do aplicativo: %APP_DIR%
echo.

REM Verifica se existe arquivo de atualização
if not exist "%NEW_EXE%" (
    echo ERRO: Arquivo de atualizacao nao encontrado
    echo Caminho esperado: %NEW_EXE%
    pause
    exit /b 1
)

echo [1/5] Parando servico TopBackup...
net stop TopBackupService 2>nul
if %ERRORLEVEL% EQU 0 (
    echo       Servico parado com sucesso
) else (
    echo       Servico nao estava em execucao
)

echo.
echo [2/5] Encerrando processo TopBackup.exe...
taskkill /f /im TopBackup.exe 2>nul
timeout /t 2 /nobreak >nul

echo.
echo [3/5] Criando backup da versao atual...
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if exist "%CURRENT_EXE%" (
    copy /y "%CURRENT_EXE%" "%BACKUP_EXE%"
    echo       Backup criado: %BACKUP_EXE%
)

echo.
echo [4/5] Instalando nova versao...
copy /y "%NEW_EXE%" "%CURRENT_EXE%"
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao copiar nova versao
    echo Restaurando versao anterior...
    copy /y "%BACKUP_EXE%" "%CURRENT_EXE%"
    pause
    exit /b 1
)
echo       Nova versao instalada com sucesso

echo.
echo [5/5] Iniciando servico TopBackup...
net start TopBackupService 2>nul
if %ERRORLEVEL% EQU 0 (
    echo       Servico iniciado com sucesso
) else (
    echo       Iniciando aplicativo em modo GUI...
    start "" "%CURRENT_EXE%"
)

echo.
echo ==========================================
echo    Atualizacao concluida com sucesso!
echo ==========================================
echo.

REM Limpa arquivos de atualização
echo Limpando arquivos temporarios...
del /q "%NEW_EXE%" 2>nul
rmdir /s /q "%UPDATE_DIR%" 2>nul

echo.
echo Pressione qualquer tecla para fechar...
timeout /t 5 >nul
exit /b 0
