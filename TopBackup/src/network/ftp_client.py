"""
TopBackup - Cliente FTP
Upload de backups para servidor FTP
"""

import os
import ftplib
from pathlib import Path
from typing import Optional, Tuple, Callable
from datetime import datetime

from ..config.settings import FTPConfig
from ..config.constants import FTP_TIMEOUT, FTP_CHUNK_SIZE
from ..utils.logger import get_logger
from ..utils.resilience import retry


class FTPClient:
    """Cliente para upload FTP de backups"""

    def __init__(self, config: FTPConfig):
        self.config = config
        self.logger = get_logger()
        self._ftp: Optional[ftplib.FTP] = None
        self._progress_callback: Optional[Callable[[int, int], None]] = None

    def set_progress_callback(self, callback: Callable[[int, int], None]):
        """
        Define callback para progresso do upload

        Args:
            callback: Função (bytes_enviados, total_bytes)
        """
        self._progress_callback = callback

    def connect(self) -> Tuple[bool, str]:
        """
        Conecta ao servidor FTP

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            self._ftp = ftplib.FTP()
            self._ftp.connect(
                self.config.host,
                self.config.port,
                timeout=FTP_TIMEOUT
            )
            self._ftp.login(self.config.user, self.config.password)

            if self.config.passive_mode:
                self._ftp.set_pasv(True)

            # Navega para diretório remoto
            if self.config.remote_path:
                self._ensure_remote_directory(self.config.remote_path)
                self._ftp.cwd(self.config.remote_path)

            self.logger.debug(f"Conectado ao FTP: {self.config.host}")
            return True, "Conexão estabelecida"

        except ftplib.error_perm as e:
            self.logger.error(f"Erro de permissão FTP: {e}")
            return False, f"Erro de permissão: {e}"

        except Exception as e:
            self.logger.error(f"Erro de conexão FTP: {e}")
            return False, str(e)

    def disconnect(self):
        """Desconecta do servidor FTP"""
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                pass
            self._ftp = None

    def _ensure_remote_directory(self, path: str):
        """Garante que o diretório remoto existe"""
        if not self._ftp:
            return

        parts = path.strip('/').split('/')
        current = ""

        for part in parts:
            if not part:
                continue
            current = f"{current}/{part}"
            try:
                self._ftp.cwd(current)
            except ftplib.error_perm:
                try:
                    self._ftp.mkd(current)
                    self._ftp.cwd(current)
                except ftplib.error_perm:
                    pass

        # Volta para raiz
        self._ftp.cwd("/")

    @retry(max_attempts=3, delay=5.0, exceptions=(ftplib.error_temp, ConnectionError))
    def upload(self, local_path: str, remote_filename: Optional[str] = None) -> Tuple[bool, str]:
        """
        Faz upload de arquivo para FTP

        Args:
            local_path: Caminho do arquivo local
            remote_filename: Nome do arquivo remoto (opcional)

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        if not os.path.exists(local_path):
            return False, f"Arquivo não encontrado: {local_path}"

        # Conecta se necessário
        if not self._ftp:
            success, msg = self.connect()
            if not success:
                return False, msg

        try:
            filename = remote_filename or os.path.basename(local_path)
            file_size = os.path.getsize(local_path)
            bytes_sent = 0

            self.logger.ftp_start(filename)

            # Callback para progresso
            def progress_callback(data):
                nonlocal bytes_sent
                bytes_sent += len(data)
                if self._progress_callback:
                    self._progress_callback(bytes_sent, file_size)

            # Upload com progresso
            with open(local_path, 'rb') as f:
                self._ftp.storbinary(
                    f'STOR {filename}',
                    f,
                    blocksize=FTP_CHUNK_SIZE,
                    callback=progress_callback
                )

            self.logger.ftp_success(filename)
            return True, "Upload concluído"

        except ftplib.error_perm as e:
            self.logger.ftp_error(local_path, str(e))
            return False, f"Erro de permissão: {e}"

        except Exception as e:
            self.logger.ftp_error(local_path, str(e))
            return False, str(e)

        finally:
            self.disconnect()

    def list_files(self, path: Optional[str] = None) -> list:
        """Lista arquivos no diretório remoto"""
        if not self._ftp:
            success, _ = self.connect()
            if not success:
                return []

        try:
            if path:
                self._ftp.cwd(path)

            files = []
            self._ftp.retrlines('LIST', lambda x: files.append(x))
            return files

        except Exception as e:
            self.logger.error(f"Erro ao listar arquivos FTP: {e}")
            return []

        finally:
            self.disconnect()

    def delete_file(self, filename: str) -> Tuple[bool, str]:
        """Remove arquivo do servidor FTP"""
        if not self._ftp:
            success, msg = self.connect()
            if not success:
                return False, msg

        try:
            self._ftp.delete(filename)
            return True, "Arquivo removido"

        except ftplib.error_perm as e:
            return False, f"Erro de permissão: {e}"

        except Exception as e:
            return False, str(e)

        finally:
            self.disconnect()

    def test_connection(self) -> Tuple[bool, str]:
        """Testa conexão com servidor FTP"""
        try:
            success, msg = self.connect()
            if success:
                self.disconnect()
            return success, msg
        except Exception as e:
            return False, str(e)
