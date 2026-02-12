"""
TopBackup - Controlador Principal
Orquestra todos os componentes do aplicativo
"""

import threading
from datetime import datetime
from typing import Optional, Callable, List
from enum import Enum

from .backup_engine import BackupEngine, BackupResult
from .scheduler import BackupScheduler
from ..config.settings import Settings
from ..database.firebird_client import FirebirdClient
from ..database.mysql_client import MySQLClient
from ..database.sync_manager import SyncManager
from ..database.models import Empresa, AgendaBackup, LogBackup
from ..network.ftp_client import FTPClient
from ..network.update_checker import UpdateChecker
from ..utils.logger import get_logger


class AppState(Enum):
    """Estados do aplicativo"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    BACKUP_RUNNING = "backup_running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class AppController:
    """Controlador principal do aplicativo"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger()

        # Estado
        self._state = AppState.INITIALIZING
        self._lock = threading.Lock()
        self._last_backup_result: Optional[BackupResult] = None

        # Callbacks para UI
        self._state_callback: Optional[Callable[[AppState], None]] = None
        self._backup_progress_callback: Optional[Callable[[str], None]] = None
        self._notification_callback: Optional[Callable[[str, str], None]] = None

        # Componentes (inicializados posteriormente)
        self._firebird: Optional[FirebirdClient] = None
        self._mysql: Optional[MySQLClient] = None
        self._sync_manager: Optional[SyncManager] = None
        self._backup_engine: Optional[BackupEngine] = None
        self._scheduler: Optional[BackupScheduler] = None
        self._ftp_client: Optional[FTPClient] = None
        self._update_checker: Optional[UpdateChecker] = None

        # Dados em cache
        self._empresa: Optional[Empresa] = None
        self._agenda: Optional[AgendaBackup] = None

    # ============ CALLBACKS ============

    def set_state_callback(self, callback: Callable[[AppState], None]):
        """Define callback para mudança de estado"""
        self._state_callback = callback

    def set_backup_progress_callback(self, callback: Callable[[str], None]):
        """Define callback para progresso do backup"""
        self._backup_progress_callback = callback

    def set_notification_callback(self, callback: Callable[[str, str], None]):
        """Define callback para notificações (titulo, mensagem)"""
        self._notification_callback = callback

    # ============ ESTADO ============

    def _set_state(self, state: AppState):
        """Atualiza estado do aplicativo"""
        with self._lock:
            self._state = state
            if self._state_callback:
                self._state_callback(state)

    @property
    def state(self) -> AppState:
        """Retorna estado atual"""
        return self._state

    # ============ INICIALIZAÇÃO ============

    def initialize(self) -> tuple:
        """
        Inicializa todos os componentes

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            self._set_state(AppState.INITIALIZING)
            self.logger.info("Inicializando AppController...")

            # Inicializa Firebird
            self._firebird = FirebirdClient(self.settings.firebird)
            success, msg = self._firebird.test_connection()
            if not success:
                return False, f"Erro de conexão Firebird: {msg}"

            # Inicializa MySQL
            self._mysql = MySQLClient(self.settings.mysql)
            success, msg = self._mysql.test_connection()
            if not success:
                return False, f"Erro de conexão MySQL: {msg}"

            # Garante schema atualizado
            self._mysql.ensure_schema()

            # Inicializa SyncManager
            self._sync_manager = SyncManager(
                self._firebird,
                self._mysql,
                self.settings
            )

            # Sincroniza empresa
            success, msg, empresa_id = self._sync_manager.sync_empresa()
            if not success:
                return False, f"Erro ao sincronizar empresa: {msg}"

            # Sincroniza agenda
            success, msg = self._sync_manager.sync_agenda()
            if not success:
                self.logger.warning(f"Agenda não sincronizada: {msg}")

            # Carrega dados em cache
            self._empresa = self._sync_manager.get_empresa_local()
            self._agenda = self._sync_manager.get_agenda()

            # Inicializa BackupEngine
            self._backup_engine = BackupEngine(self.settings, self._mysql)
            self._backup_engine.set_progress_callback(self._on_backup_progress)

            # Inicializa Scheduler
            self._scheduler = BackupScheduler(self.settings)
            self._scheduler.set_backup_callback(self._on_scheduled_backup)
            self._scheduler.set_sync_callback(self._on_sync_schedule)
            self._scheduler.set_update_callback(self._on_update_schedule)

            # Configura TODAS as agendas de backup
            all_agendas = self._firebird.get_all_agendas()
            if all_agendas:
                self._scheduler.configure_from_agendas(all_agendas)
            elif self._agenda:
                self._scheduler.configure_from_agenda(self._agenda)

            # Configura jobs do sistema
            self._scheduler.configure_system_jobs()

            # Inicializa FTP (se configurado)
            if self.settings.backup.backup_remoto and self.settings.ftp.host:
                self._ftp_client = FTPClient(self.settings.ftp)

            # Inicializa Update Checker
            self._update_checker = UpdateChecker(self._mysql, self.settings)
            self._update_checker.set_update_callback(self._on_update_available)

            self.logger.info("AppController inicializado com sucesso")
            return True, "Inicialização concluída"

        except Exception as e:
            self.logger.error(f"Erro na inicialização: {e}", exc_info=True)
            self._set_state(AppState.ERROR)
            return False, str(e)

    def start(self):
        """Inicia o aplicativo"""
        if self._scheduler:
            self._scheduler.start()

        # Atualiza interação no início (substitui heartbeat)
        if self._mysql and self.settings.app.empresa_id:
            self._mysql.update_empresa_interacao(self.settings.app.empresa_id)

        self._set_state(AppState.RUNNING)
        self.logger.info("Aplicativo iniciado")

        # Verifica atualizações na inicialização
        if self._update_checker and self.settings.app.auto_update:
            self.logger.info("Verificando atualizações na inicialização...")
            self._check_and_apply_update()

    def stop(self):
        """Para o aplicativo"""
        if self._scheduler:
            self._scheduler.stop()

        self._set_state(AppState.STOPPED)
        self.logger.info("Aplicativo parado")

    def pause(self):
        """Pausa o agendamento"""
        if self._scheduler:
            self._scheduler.pause()
        self._set_state(AppState.PAUSED)

    def resume(self):
        """Resume o agendamento"""
        if self._scheduler:
            self._scheduler.resume()
        self._set_state(AppState.RUNNING)

    # ============ BACKUP ============

    def execute_backup_manual(self) -> BackupResult:
        """Executa backup manual"""
        if self._state == AppState.BACKUP_RUNNING:
            return BackupResult(
                success=False,
                message="Backup já em execução"
            )

        return self._execute_backup(manual=True)

    def _execute_backup(self, manual: bool = False) -> BackupResult:
        """Executa backup"""
        if not self._backup_engine or not self._empresa or not self._agenda:
            return BackupResult(
                success=False,
                message="Componentes não inicializados"
            )

        self._set_state(AppState.BACKUP_RUNNING)

        try:
            result = self._backup_engine.execute_backup(
                self._empresa,
                self._agenda,
                manual=manual
            )

            self._last_backup_result = result

            # Atualiza interação após backup
            if result.success and self._mysql and self.settings.app.empresa_id:
                self._mysql.update_empresa_interacao(self.settings.app.empresa_id)

            # Upload FTP se configurado
            if result.success and self.settings.backup.backup_remoto:
                self._upload_ftp(result)

            # Notificação de backup removida - app silencioso (v1.0.6)
            # O log já registra automaticamente via BackupEngine

            return result

        finally:
            self._set_state(AppState.RUNNING)
            # Sinaliza fim do progresso para esconder a barra na UI
            if self._backup_progress_callback:
                self._backup_progress_callback("")

    def cancel_backup(self):
        """Cancela backup em execução"""
        if self._backup_engine:
            self._backup_engine.cancel()

    def _upload_ftp(self, result: BackupResult):
        """Upload para FTP"""
        if not self._ftp_client or not result.caminho:
            return

        success, msg = self._ftp_client.upload(result.caminho)

        if success:
            self.logger.ftp_success(result.arquivo or "")
        else:
            self.logger.ftp_error(result.arquivo or "", msg)

    # ============ CALLBACKS DO SCHEDULER ============

    def _on_scheduled_backup(self):
        """Callback para backup agendado"""
        self._execute_backup(manual=False)

    def _on_sync_schedule(self):
        """Callback para sincronização"""
        if self._sync_manager:
            self._sync_manager.sync_agenda()
            self._agenda = self._sync_manager.get_agenda()

            if self._scheduler and self._firebird:
                all_agendas = self._firebird.get_all_agendas()
                if all_agendas:
                    self._scheduler.configure_from_agendas(all_agendas)
                elif self._agenda:
                    self._scheduler.configure_from_agenda(self._agenda)

    def _on_update_schedule(self):
        """Callback para verificação de updates"""
        # Atualiza DATA_ULTIMA_INTERACAO a cada verificação (independente de haver update)
        if self._mysql and self.settings.app.empresa_id:
            self._mysql.update_empresa_interacao(self.settings.app.empresa_id)
            self.logger.debug("DATA_ULTIMA_INTERACAO atualizada na verificação de updates")

        # Verifica e aplica atualização automaticamente
        if self._update_checker and self.settings.app.auto_update:
            self._check_and_apply_update()

    def _on_backup_progress(self, message: str):
        """Callback para progresso do backup"""
        if self._backup_progress_callback:
            self._backup_progress_callback(message)

    def _on_update_available(self, versao: str, changelog: str):
        """Callback para update disponível - apenas log, sem pop-up"""
        self.logger.info(f"Atualização disponível: versão {versao}")

    def _check_and_apply_update(self):
        """Verifica, baixa e aplica atualização automaticamente"""
        import threading

        def do_update():
            try:
                # Verifica se há atualização
                has_update, version_info = self._update_checker.check_for_updates()

                if not has_update:
                    self.logger.info("Nenhuma atualização disponível")
                    return

                self.logger.info(f"Atualização encontrada: {version_info.versao}")
                self.logger.info(f"Iniciando download da versão {version_info.versao}...")

                # Baixa a atualização
                success, result = self._update_checker.download_update()

                if not success:
                    self.logger.error(f"Falha no download da atualização: {result}")
                    return

                self.logger.info(f"Download concluído: {result}")

                # Aplica a atualização
                success, msg = self._update_checker.apply_update(result)

                if success:
                    self.logger.info("Atualização aplicada com sucesso - reiniciando aplicativo...")
                    # O apply_update já inicia o script de atualização que reinicia o app
                else:
                    self.logger.error(f"Falha ao aplicar atualização: {msg}")

            except Exception as e:
                self.logger.error(f"Erro na atualização automática: {e}")

        # Executa em thread separada para não bloquear a UI
        thread = threading.Thread(target=do_update, daemon=True)
        thread.start()

    # ============ INFORMAÇÕES ============

    def get_empresa(self) -> Optional[Empresa]:
        """Retorna dados da empresa"""
        return self._empresa

    def get_agenda(self) -> Optional[AgendaBackup]:
        """Retorna agenda de backup"""
        return self._agenda

    def get_all_agendas(self) -> List[AgendaBackup]:
        """Retorna todas as agendas de backup do Firebird"""
        if self._firebird:
            return self._firebird.get_all_agendas()
        return []

    def get_last_backup_result(self) -> Optional[BackupResult]:
        """Retorna resultado do último backup"""
        return self._last_backup_result

    def get_next_backup_time(self) -> Optional[datetime]:
        """Retorna próximo horário de backup"""
        if self._scheduler:
            return self._scheduler.get_next_backup_time()
        return None

    def get_backup_logs(self, limit: int = 50) -> List[LogBackup]:
        """Retorna logs de backup"""
        if self._mysql and self.settings.app.empresa_id:
            return self._mysql.get_logs_by_empresa(
                self.settings.app.empresa_id,
                limit
            )
        return []

    def get_status(self) -> dict:
        """Retorna status completo do aplicativo"""
        return {
            'state': self._state.value,
            'empresa': self._empresa.fantasia if self._empresa else None,
            'cnpj': self._empresa.cnpj if self._empresa else None,
            'database_path': self.settings.firebird.database_path,
            'destino1': self.settings.backup.local_destino1,
            'destino2': self.settings.backup.local_destino2,
            'next_backup': self.get_next_backup_time(),
            'last_backup': self._last_backup_result.arquivo if self._last_backup_result else None,
            'last_backup_success': self._last_backup_result.success if self._last_backup_result else None,
            'firebird_connected': self._sync_manager.is_connected_firebird() if self._sync_manager else False,
            'mysql_connected': self._sync_manager.is_connected_mysql() if self._sync_manager else False,
        }

    def refresh_settings(self):
        """
        Recarrega configurações do arquivo config.json
        Atualiza todas as referências nos componentes
        """
        self.settings = Settings.load()

        # Atualiza referências em todos os componentes
        if self._sync_manager:
            self._sync_manager.settings = self.settings

        if self._backup_engine:
            self._backup_engine.settings = self.settings

        # Atualiza agenda com os novos destinos
        if self._agenda:
            self._agenda.local_destino1 = self.settings.backup.local_destino1
            self._agenda.local_destino2 = self.settings.backup.local_destino2

        self.logger.info("Configurações recarregadas do arquivo")

    def reload_config(self, force_from_firebird: bool = True):
        """
        Recarrega configurações do Firebird

        Args:
            force_from_firebird: Se True, sobrescreve destinos locais com os do Firebird
        """
        self.settings = Settings.load()

        if self._sync_manager:
            # Atualiza referência de settings no sync_manager
            self._sync_manager.settings = self.settings
            self._sync_manager.refresh()

        if self._backup_engine:
            self._backup_engine.settings = self.settings

            # Força atualização dos destinos do Firebird
            if force_from_firebird and self._firebird:
                agenda_fb = self._firebird.get_agenda_backup()
                if agenda_fb:
                    self.settings.backup.local_destino1 = agenda_fb.local_destino1 or ""
                    self.settings.backup.local_destino2 = agenda_fb.local_destino2 or ""
                    self.settings.backup.prefixo_backup = agenda_fb.prefixo_backup
                    self.settings.save()
                    self.logger.info(f"Destinos atualizados do Firebird:")
                    self.logger.info(f"  Destino 1: {agenda_fb.local_destino1}")
                    self.logger.info(f"  Destino 2: {agenda_fb.local_destino2}")

                    # Atualiza agenda local sem chamar sync_agenda (que sobrescreveria)
                    self._agenda = agenda_fb
            else:
                # Só faz full_sync se não forçou do Firebird
                self._sync_manager.full_sync()
                self._agenda = self._sync_manager.get_agenda()

            if self._scheduler and self._firebird:
                all_agendas = self._firebird.get_all_agendas()
                if all_agendas:
                    self._scheduler.configure_from_agendas(all_agendas)
                elif self._agenda:
                    self._scheduler.configure_from_agenda(self._agenda)
