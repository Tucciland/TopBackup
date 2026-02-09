@echo off
REM TopBackup - Script de Build com PyInstaller
REM Gera o executável do aplicativo

setlocal

echo ==========================================
echo    TopBackup - Build Script
echo ==========================================
echo.

REM Diretório do projeto
set PROJECT_DIR=%~dp0..
cd /d "%PROJECT_DIR%"

echo Diretorio do projeto: %PROJECT_DIR%
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Python nao encontrado no PATH
    echo Instale Python 3.8+ e adicione ao PATH
    pause
    exit /b 1
)

echo [1/4] Verificando dependencias...
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

echo.
echo [2/4] Instalando dependencias do projeto...
pip install -r requirements.txt

echo.
echo [3/4] Limpando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo [4/4] Gerando executavel...
pyinstaller topbackup.spec --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERRO: Falha no build
    pause
    exit /b 1
)

echo.
echo ==========================================
echo    Build concluido com sucesso!
echo ==========================================
echo.
echo Executavel gerado em: dist\TopBackup.exe
echo.

REM Copia arquivos adicionais para dist
echo Copiando arquivos adicionais...
if not exist "dist\config" mkdir "dist\config"
if not exist "dist\scripts" mkdir "dist\scripts"
if not exist "dist\logs" mkdir "dist\logs"

copy "config\config.json.example" "dist\config\" >nul 2>&1
copy "scripts\update.bat" "dist\scripts\" >nul 2>&1

echo.
echo Pronto! O aplicativo esta em: dist\
echo.
pause
