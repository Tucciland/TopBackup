"""
TopBackup - Motor de Backup
Executa gbak, valida, compacta e move backups
"""

import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Callable
from dataclasses import dataclass

from ..config.settings import Settings
from ..config.constants import (
    BACKUP_TIMEOUT, STATUS_EXECUTANDO, STATUS_SUCESSO, STATUS_FALHA,
    BACKUP_EXTENSION, ZIP_EXTENSION
)
from ..database.models import LogBackup, Empresa, AgendaBackup
from ..database.mysql_client import MySQLClient
from ..utils.logger import get_logger
from ..utils.file_utils import FileUtils


@dataclass
class BackupResult:
    """Resultado de um backup"""
    success: bool
    message: str
    arquivo: Optional[str] = None
    caminho: Optional[str] = None
    tamanho_bytes: int = 0
    tamanho_formatado: str = ""
    duracao_segundos: float = 0


class BackupEngine:
    """Motor de execução de backup Firebird"""

    def __init__(
        self,
        settings: Settings,
        mysql_client: Optional[MySQLClient] = None
    ):
        self.settings = settings
        self.mysql = mysql_client
        self.logger = get_logger()
        self._progress_callback: Optional[Callable[[str], None]] = None
        self._cancel_requested: bool = False

    def set_progress_callback(self, callback: Callable[[str], None]):
        """Define callback para progresso do backup"""
        self._progress_callback = callback

    def _report_progress(self, message: str):
        """Reporta progresso do backup"""
        self.logger.info(message)
        if self._progress_callback:
            self._progress_callback(message)

    def cancel(self):
        """Solicita cancelamento do backup"""
        self._cancel_requested = True

    def execute_backup(
        self,
        empresa: Empresa,
        agenda: AgendaBackup,
        manual: bool = False
    ) -> BackupResult:
        """
        Executa backup completo

        Args:
            empresa: Dados da empresa
            agenda: Configurações de agendamento
            manual: Se é backup manual (ignora dia da semana)

        Returns:
            BackupResult com o resultado do backup
        """
        self._cancel_requested = False
        inicio = datetime.now()

        # Verifica se deve executar hoje
        if not manual and not agenda.deve_executar_hoje():
            return BackupResult(
                success=False,
                message="Backup não agendado para hoje"
            )

        # Cria log de backup
        log = LogBackup(
            id_empresa=self.settings.app.empresa_id or 0,
            data_inicio=inicio,
            tipo_backup=agenda.prefixo_backup,
            status=STATUS_EXECUTANDO,
            manual=manual
        )

        # Insere log no MySQL
        if self.mysql:
            log.id = self.mysql.insert_log_backup(log)

        try:
            # Log do destino configurado
            self.logger.info(f"Destino 1: {agenda.local_destino1 or '(vazio)'}")
            self.logger.info(f"Destino 2: {agenda.local_destino2 or '(vazio)'}")
            self.logger.info(f"Tipo backup: {agenda.prefixo_backup}")

            # 1. Executa gbak
            self._report_progress("Iniciando backup com gbak...")
            fbk_path = self._execute_gbak()

            self.logger.info(f"Backup criado em: {fbk_path}")
            self.logger.info(f"Tamanho do .fbk: {os.path.getsize(fbk_path)} bytes")

            if self._cancel_requested:
                raise BackupCancelledError("Backup cancelado pelo usuário")

            # 2. Valida backup
            self._report_progress("Validando backup...")
            self._validate_backup(fbk_path)

            if self._cancel_requested:
                raise BackupCancelledError("Backup cancelado pelo usuário")

            # 3. Compacta se configurado
            if self.settings.backup.compactar_zip:
                self._report_progress("Compactando arquivo...")
                final_path = self._compress_backup(fbk_path, empresa, agenda)
                self.logger.info(f"ZIP criado: {final_path}")
                self.logger.info(f"Tamanho do ZIP: {os.path.getsize(final_path)} bytes")
            else:
                final_path = fbk_path

            if self._cancel_requested:
                raise BackupCancelledError("Backup cancelado pelo usuário")

            # 4. Move para destinos
            self.logger.info(f"=== INICIANDO MOVIMENTACAO ===")
            self.logger.info(f"Arquivo origem: {final_path}")
            self.logger.info(f"Arquivo existe? {os.path.exists(final_path)}")
            self.logger.info(f"Destino agenda: {agenda.local_destino1}")
            self.logger.info(f"Destino config: {self.settings.backup.local_destino1}")

            # Usa o destino da agenda, não da config
            destino_final = agenda.local_destino1
            if not destino_final:
                destino_final = self.settings.backup.local_destino1
                self.logger.warning(f"Agenda sem destino, usando config: {destino_final}")

            if not destino_final:
                raise BackupError("Nenhum diretório de destino configurado!")

            self._report_progress(f"Movendo para: {destino_final}")

            try:
                destino1 = self._move_to_destination(
                    final_path,
                    destino_final,
                    empresa,
                    agenda
                )
                self.logger.info(f"Arquivo movido para: {destino1}")
            except Exception as move_error:
                self.logger.error(f"ERRO ao mover arquivo: {move_error}")
                raise

            # 5. Copia para destino secundário
            destino2 = None
            if agenda.local_destino2:
                self._report_progress("Copiando para destino secundário...")
                destino2 = self._copy_to_destination(
                    destino1,
                    agenda.local_destino2
                )

            # Calcula resultado
            tamanho = FileUtils.get_file_size(destino1)
            tamanho_fmt = FileUtils.format_size(tamanho)
            duracao = (datetime.now() - inicio).total_seconds()

            # Atualiza log como sucesso
            log.set_sucesso(
                arquivo=os.path.basename(destino1),
                caminho=destino1,
                tamanho=tamanho,
                tamanho_fmt=tamanho_fmt,
                caminho2=destino2
            )

            if self.mysql and log.id:
                self.mysql.update_log_backup(log)

            self.logger.backup_success(
                empresa.fantasia,
                os.path.basename(destino1),
                tamanho_fmt
            )

            return BackupResult(
                success=True,
                message="Backup realizado com sucesso",
                arquivo=os.path.basename(destino1),
                caminho=destino1,
                tamanho_bytes=tamanho,
                tamanho_formatado=tamanho_fmt,
                duracao_segundos=duracao
            )

        except BackupCancelledError as e:
            log.set_falha(str(e))
            if self.mysql and log.id:
                self.mysql.update_log_backup(log)
            return BackupResult(success=False, message=str(e))

        except Exception as e:
            self.logger.backup_error(empresa.fantasia, str(e))
            log.set_falha(str(e))
            if self.mysql and log.id:
                self.mysql.update_log_backup(log)
            return BackupResult(success=False, message=str(e))

        finally:
            # Limpa arquivos temporários
            self._cleanup_temp()

    def _execute_gbak(self) -> str:
        """
        Executa gbak para criar backup

        Returns:
            Caminho do arquivo .fbk gerado
        """
        gbak_path = self.settings.firebird.gbak_path
        db_path = self.settings.firebird.database_path

        if not os.path.exists(gbak_path):
            raise BackupError(f"gbak não encontrado: {gbak_path}")

        if not os.path.exists(db_path):
            raise BackupError(f"Banco de dados não encontrado: {db_path}")

        # Cria diretório temporário
        temp_dir = FileUtils.get_temp_directory()
        temp_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        fbk_filename = f"backup_{timestamp}{BACKUP_EXTENSION}"
        fbk_path = temp_dir / fbk_filename

        # Comando gbak simples - igual ao batch que funciona
        # gbak -b -user sysdba -pass masterkey banco destino
        cmd = [
            gbak_path,
            "-b",
            "-user", self.settings.firebird.user,
            "-pass", self.settings.firebird.password,
            db_path,
            str(fbk_path)
        ]

        self.logger.debug(f"Executando: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=BACKUP_TIMEOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Erro desconhecido"
                raise BackupError(f"gbak falhou: {error_msg}")

            if not fbk_path.exists():
                raise BackupError("Arquivo de backup não foi criado")

            return str(fbk_path)

        except subprocess.TimeoutExpired:
            raise BackupError(f"Timeout após {BACKUP_TIMEOUT}s")

    def _validate_backup(self, fbk_path: str) -> bool:
        """
        Valida integridade do backup verificando apenas tamanho

        Args:
            fbk_path: Caminho do arquivo .fbk

        Returns:
            True se válido
        """
        # Validação simples: verifica se arquivo existe e tem tamanho razoável
        if not os.path.exists(fbk_path):
            raise BackupError("Arquivo de backup não encontrado")

        file_size = os.path.getsize(fbk_path)
        if file_size < 1024:  # Menos de 1KB é suspeito
            raise BackupError(f"Arquivo de backup muito pequeno: {file_size} bytes")

        self.logger.debug(f"Backup validado: {file_size} bytes")
        return True

    def _compress_backup(
        self,
        fbk_path: str,
        empresa: Empresa,
        agenda: AgendaBackup
    ) -> str:
        """
        Compacta backup em ZIP

        Returns:
            Caminho do arquivo ZIP
        """
        # Gera nome do arquivo
        zip_filename = FileUtils.generate_backup_filename(
            empresa.cnpj,
            agenda.prefixo_backup,
            ZIP_EXTENSION
        )

        temp_dir = FileUtils.get_temp_directory()
        zip_path = temp_dir / zip_filename

        success, message = FileUtils.compress_to_zip(fbk_path, str(zip_path))

        if not success:
            raise BackupError(f"Erro na compactação: {message}")

        # Remove arquivo .fbk original
        FileUtils.safe_delete(fbk_path)

        return str(zip_path)

    def _move_to_destination(
        self,
        source_path: str,
        dest_dir: str,
        empresa: Empresa,
        agenda: AgendaBackup
    ) -> str:
        """
        Move arquivo para diretório de destino

        Returns:
            Caminho final do arquivo
        """
        if not dest_dir:
            raise BackupError("Diretório de destino não configurado")

        # Garante que o diretório existe
        FileUtils.ensure_directory(dest_dir)

        # Gera nome do arquivo se não for ZIP
        if not source_path.endswith(ZIP_EXTENSION):
            filename = FileUtils.generate_backup_filename(
                empresa.cnpj,
                agenda.prefixo_backup,
                BACKUP_EXTENSION
            )
        else:
            filename = os.path.basename(source_path)

        dest_path = os.path.join(dest_dir, filename)

        success, message = FileUtils.safe_move(source_path, dest_path)

        if not success:
            raise BackupError(f"Erro ao mover arquivo: {message}")

        return dest_path

    def _copy_to_destination(self, source_path: str, dest_dir: str) -> str:
        """
        Copia arquivo para diretório secundário

        Returns:
            Caminho da cópia
        """
        if not dest_dir:
            return source_path

        FileUtils.ensure_directory(dest_dir)

        filename = os.path.basename(source_path)
        dest_path = os.path.join(dest_dir, filename)

        success, message = FileUtils.safe_copy(source_path, dest_path)

        if not success:
            self.logger.warning(f"Erro ao copiar para destino secundário: {message}")

        return dest_path

    def _cleanup_temp(self):
        """Limpa arquivos temporários"""
        try:
            FileUtils.cleanup_temp_files(max_age_hours=24)
        except Exception as e:
            self.logger.warning(f"Erro na limpeza de temporários: {e}")


class BackupError(Exception):
    """Exceção para erros de backup"""
    pass


class BackupCancelledError(Exception):
    """Exceção para backup cancelado"""
    pass
