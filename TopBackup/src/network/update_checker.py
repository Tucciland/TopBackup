"""
TopBackup - Verificador de Atualizações
Verifica e gerencia atualizações do aplicativo
"""

from typing import Optional, Callable, Tuple
from packaging import version as pkg_version

from ..database.mysql_client import MySQLClient
from ..database.models import VersaoApp
from ..config.settings import Settings
from ..version import VERSION
from ..utils.logger import get_logger
from .downloader import Downloader


class UpdateChecker:
    """Verificador de atualizações do aplicativo"""

    def __init__(self, mysql_client: MySQLClient, settings: Settings):
        self.mysql = mysql_client
        self.settings = settings
        self.logger = get_logger()

        self._update_available: Optional[VersaoApp] = None
        self._update_callback: Optional[Callable[[str, str], None]] = None

    def set_update_callback(self, callback: Callable[[str, str], None]):
        """
        Define callback para notificação de update

        Args:
            callback: Função (versao, changelog)
        """
        self._update_callback = callback

    def check_for_updates(self) -> Tuple[bool, Optional[VersaoApp]]:
        """
        Verifica se há atualizações disponíveis

        Returns:
            Tuple[bool, Optional[VersaoApp]]: (há_update, dados_versao)
        """
        try:
            # Busca versão mais recente no servidor
            latest = self.mysql.get_latest_version()

            if not latest:
                self.logger.debug("Nenhuma versão encontrada no servidor")
                return False, None

            # Compara versões
            current = pkg_version.parse(VERSION)
            remote = pkg_version.parse(latest.versao)

            if remote > current:
                self._update_available = latest
                self.logger.info(f"Atualização disponível: {latest.versao}")

                # Notifica via callback
                if self._update_callback:
                    self._update_callback(
                        latest.versao,
                        latest.changelog or ""
                    )

                return True, latest

            self.logger.debug(f"Versão atual ({VERSION}) está atualizada")
            return False, None

        except Exception as e:
            self.logger.error(f"Erro ao verificar atualizações: {e}")
            return False, None

    def get_available_update(self) -> Optional[VersaoApp]:
        """Retorna informações da atualização disponível"""
        return self._update_available

    def download_update(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> Tuple[bool, str]:
        """
        Baixa a atualização disponível

        Args:
            progress_callback: Callback de progresso (bytes_baixados, total)

        Returns:
            Tuple[bool, str]: (sucesso, caminho_arquivo ou mensagem_erro)
        """
        if not self._update_available:
            return False, "Nenhuma atualização disponível"

        try:
            downloader = Downloader()

            if progress_callback:
                downloader.set_progress_callback(progress_callback)

            success, result = downloader.download(
                self._update_available.url_download,
                expected_hash=self._update_available.hash_sha256
            )

            if success:
                self.logger.info(f"Atualização baixada: {result}")
                return True, result
            else:
                self.logger.error(f"Falha no download: {result}")
                return False, result

        except Exception as e:
            self.logger.error(f"Erro ao baixar atualização: {e}")
            return False, str(e)

    def apply_update(self, update_path: str) -> Tuple[bool, str]:
        """
        Aplica a atualização baixada

        Este método prepara os arquivos e cria/executa o script de atualização.
        O script é gerado dinamicamente para não depender de arquivos externos.

        Args:
            update_path: Caminho do arquivo de atualização

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        import os
        import shutil
        import sys

        try:
            # Verifica se o arquivo existe
            if not os.path.exists(update_path):
                return False, "Arquivo de atualização não encontrado"

            # Diretório do executável atual
            if getattr(sys, 'frozen', False):
                app_dir = os.path.dirname(sys.executable)
                current_exe = sys.executable
            else:
                return False, "Atualização automática só funciona no executável"

            # Copia para diretório de update
            update_dir = os.path.join(app_dir, "update")
            os.makedirs(update_dir, exist_ok=True)

            new_exe = os.path.join(update_dir, "TopBackup_new.exe")
            shutil.copy2(update_path, new_exe)

            # Cria script de atualização dinamicamente
            backup_exe = os.path.join(update_dir, "TopBackup_backup.exe")

            script_content = f'''@echo off
chcp 65001 >nul
echo ==========================================
echo    TopBackup - Atualizacao Automatica
echo ==========================================
echo.

set "NEW_EXE={new_exe}"
set "CURRENT_EXE={current_exe}"
set "BACKUP_EXE={backup_exe}"

echo Aguardando aplicativo fechar...
timeout /t 3 /nobreak >nul

echo Parando servico (se existir)...
net stop TopBackupService 2>nul

echo Encerrando processo...
taskkill /f /im TopBackup.exe 2>nul
timeout /t 2 /nobreak >nul

echo Criando backup...
if exist "%CURRENT_EXE%" copy /y "%CURRENT_EXE%" "%BACKUP_EXE%" >nul

echo Instalando nova versao...
copy /y "%NEW_EXE%" "%CURRENT_EXE%"
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao copiar. Restaurando backup...
    copy /y "%BACKUP_EXE%" "%CURRENT_EXE%"
    pause
    exit /b 1
)

echo Iniciando nova versao...
start "" "%CURRENT_EXE%"

echo Limpando arquivos temporarios...
del /q "%NEW_EXE%" 2>nul

echo.
echo Atualizacao concluida!
timeout /t 3 >nul
exit /b 0
'''

            script_path = os.path.join(update_dir, "update.bat")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            # Inicia script de atualização usando cmd.exe
            import subprocess
            subprocess.Popen(
                f'cmd.exe /c "{script_path}"',
                cwd=app_dir,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            return True, "Atualização iniciada. O aplicativo será reiniciado."

        except Exception as e:
            self.logger.error(f"Erro ao aplicar atualização: {e}")
            return False, str(e)

    def is_update_available(self) -> bool:
        """Verifica se há atualização disponível em cache"""
        return self._update_available is not None

    def is_update_mandatory(self) -> bool:
        """Verifica se a atualização é obrigatória"""
        if self._update_available:
            return self._update_available.is_obrigatoria()
        return False

    @property
    def current_version(self) -> str:
        """Retorna versão atual do aplicativo"""
        return VERSION

    @property
    def latest_version(self) -> Optional[str]:
        """Retorna versão mais recente disponível"""
        if self._update_available:
            return self._update_available.versao
        return None
