"""
TopBackup - Sistema de Logging
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class Logger:
    """Gerenciador de logging do aplicativo"""

    _instance: Optional["Logger"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if Logger._initialized:
            return

        self.logger = logging.getLogger("TopBackup")
        self.logger.setLevel(logging.DEBUG)

        # Define o diretório de logs
        if getattr(os.sys, 'frozen', False):
            # Executável - sempre usa C:\TOPBACKUP
            base_path = Path(r"C:\TOPBACKUP")
        else:
            # Desenvolvimento
            base_path = Path(__file__).parent.parent.parent

        self.log_dir = base_path / "logs"
        self.log_dir.mkdir(exist_ok=True)

        # Configura o handler de arquivo com rotação
        log_file = self.log_dir / "topbackup.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)

        # Configura o handler de console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formato do log
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Adiciona os handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        Logger._initialized = True

    def debug(self, message: str):
        """Log de debug"""
        self.logger.debug(message)

    def info(self, message: str):
        """Log de informação"""
        self.logger.info(message)

    def warning(self, message: str):
        """Log de aviso"""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        """Log de erro"""
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False):
        """Log crítico"""
        self.logger.critical(message, exc_info=exc_info)

    def backup_start(self, empresa: str):
        """Log específico de início de backup"""
        self.info(f"[BACKUP] Iniciando backup: {empresa}")

    def backup_success(self, empresa: str, arquivo: str, tamanho: str):
        """Log específico de sucesso do backup"""
        self.info(f"[BACKUP] Sucesso: {empresa} | Arquivo: {arquivo} | Tamanho: {tamanho}")

    def backup_error(self, empresa: str, erro: str):
        """Log específico de erro do backup"""
        self.error(f"[BACKUP] Erro: {empresa} | {erro}")

    def ftp_start(self, arquivo: str):
        """Log de início de upload FTP"""
        self.info(f"[FTP] Iniciando upload: {arquivo}")

    def ftp_success(self, arquivo: str):
        """Log de sucesso do upload FTP"""
        self.info(f"[FTP] Upload concluído: {arquivo}")

    def ftp_error(self, arquivo: str, erro: str):
        """Log de erro no upload FTP"""
        self.error(f"[FTP] Erro no upload: {arquivo} | {erro}")

    def get_log_file_path(self) -> Path:
        """Retorna o caminho do arquivo de log atual"""
        return self.log_dir / "topbackup.log"

    def get_recent_logs(self, lines: int = 100) -> list:
        """Retorna as últimas linhas do log"""
        log_file = self.get_log_file_path()
        if not log_file.exists():
            return []

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
        except Exception:
            return []


def get_logger() -> Logger:
    """Retorna a instância singleton do logger"""
    return Logger()
