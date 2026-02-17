"""
TopBackup - Gerenciador de Sincronização
Sincroniza dados entre Firebird local e MySQL na nuvem
"""

from typing import Optional, Tuple
from datetime import datetime

from .models import Empresa, AgendaBackup
from .firebird_client import FirebirdClient
from .mysql_client import MySQLClient
from ..config.settings import Settings
from ..utils.logger import get_logger
from ..version import VERSION


class SyncManager:
    """Gerenciador de sincronização Firebird ↔ MySQL"""

    def __init__(self, firebird: FirebirdClient, mysql: MySQLClient, settings: Settings):
        self.firebird = firebird
        self.mysql = mysql
        self.settings = settings
        self.logger = get_logger()

        self._empresa_local: Optional[Empresa] = None
        self._empresa_cloud: Optional[Empresa] = None
        self._agenda: Optional[AgendaBackup] = None

    def sync_empresa(self) -> Tuple[bool, str, Optional[int]]:
        """
        Sincroniza dados da empresa do Firebird para MySQL

        Returns:
            Tuple[bool, str, Optional[int]]: (sucesso, mensagem, id_empresa)
        """
        try:
            # Busca empresa no Firebird
            self._empresa_local = self.firebird.get_empresa()

            if not self._empresa_local:
                return False, "Empresa não encontrada no Firebird", None

            if not self._empresa_local.cnpj:
                return False, "CNPJ não encontrado na empresa", None

            # Usa versão do TopBackup
            self._empresa_local.versao_local = VERSION

            # Atualiza data de interação
            self._empresa_local.data_ultima_interacao = datetime.now()

            # Sincroniza com MySQL (insert ou update)
            id_empresa = self.mysql.sync_empresa(self._empresa_local)

            if id_empresa:
                # Atualiza empresa cloud
                self._empresa_cloud = self.mysql.get_empresa_by_cnpj(self._empresa_local.cnpj)

                # Salva ID na configuração
                self.settings.app.empresa_id = id_empresa
                self.settings.app.empresa_cnpj = self._empresa_local.cnpj
                self.settings.save()

                self.logger.info(f"Empresa sincronizada: {self._empresa_local.fantasia} (ID: {id_empresa})")
                return True, "Empresa sincronizada com sucesso", id_empresa

            return False, "Falha ao sincronizar empresa", None

        except Exception as e:
            self.logger.error(f"Erro na sincronização: {e}", exc_info=True)
            return False, str(e), None

    def sync_agenda(self) -> Tuple[bool, str]:
        """
        Sincroniza agenda de backup do Firebird para configuração local

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Busca agenda no Firebird
            self._agenda = self.firebird.get_agenda_backup()

            if not self._agenda:
                return False, "Agenda de backup não encontrada no Firebird"

            # Sincroniza configurações - config local tem prioridade sobre Firebird
            self.logger.info(f"Valores do Firebird:")
            self.logger.info(f"  Destino 1 FB: {self._agenda.local_destino1}")
            self.logger.info(f"  Destino 2 FB: {self._agenda.local_destino2}")
            self.logger.info(f"Valores da Config Local:")
            self.logger.info(f"  Destino 1 Config: {self.settings.backup.local_destino1}")
            self.logger.info(f"  Destino 2 Config: {self.settings.backup.local_destino2}")

            # Só usa valor do Firebird se config local estiver vazia
            if not self.settings.backup.local_destino1:
                self.settings.backup.local_destino1 = self._agenda.local_destino1
                self.logger.info(f"Usando destino 1 do Firebird: {self._agenda.local_destino1}")
            else:
                # Atualiza a agenda com o valor da config local para usar no backup
                self._agenda.local_destino1 = self.settings.backup.local_destino1
                self.logger.info(f"Mantendo destino 1 da config: {self.settings.backup.local_destino1}")

            if not self.settings.backup.local_destino2:
                self.settings.backup.local_destino2 = self._agenda.local_destino2 or ""
                self.logger.info(f"Usando destino 2 do Firebird: {self._agenda.local_destino2}")
            else:
                # Atualiza a agenda com o valor da config local
                self._agenda.local_destino2 = self.settings.backup.local_destino2
                self.logger.info(f"Mantendo destino 2 da config: {self.settings.backup.local_destino2}")

            # Prefixo e backup_remoto sempre vêm do Firebird
            self.settings.backup.backup_remoto = self._agenda.backup_remoto == 'S'
            self.settings.backup.prefixo_backup = self._agenda.prefixo_backup

            self.settings.save()

            self.logger.info(f"Agenda sincronizada: {self._agenda.horario}")
            return True, "Agenda sincronizada com sucesso"

        except Exception as e:
            self.logger.error(f"Erro ao sincronizar agenda: {e}", exc_info=True)
            return False, str(e)

    def full_sync(self) -> Tuple[bool, str]:
        """
        Executa sincronização completa

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        # Sincroniza empresa
        sucesso_emp, msg_emp, id_emp = self.sync_empresa()
        if not sucesso_emp:
            return False, f"Erro ao sincronizar empresa: {msg_emp}"

        # Sincroniza agenda
        sucesso_agenda, msg_agenda = self.sync_agenda()
        if not sucesso_agenda:
            return False, f"Erro ao sincronizar agenda: {msg_agenda}"

        return True, "Sincronização completa realizada"

    def get_empresa_local(self) -> Optional[Empresa]:
        """Retorna empresa local em cache"""
        if not self._empresa_local:
            self._empresa_local = self.firebird.get_empresa()
        return self._empresa_local

    def get_empresa_cloud(self) -> Optional[Empresa]:
        """Retorna empresa cloud em cache"""
        if not self._empresa_cloud and self.settings.app.empresa_cnpj:
            self._empresa_cloud = self.mysql.get_empresa_by_cnpj(
                self.settings.app.empresa_cnpj
            )
        return self._empresa_cloud

    def get_agenda(self) -> Optional[AgendaBackup]:
        """Retorna agenda em cache"""
        if not self._agenda:
            self._agenda = self.firebird.get_agenda_backup()
        return self._agenda

    def refresh(self):
        """Limpa cache e força recarregamento"""
        self._empresa_local = None
        self._empresa_cloud = None
        self._agenda = None

    def is_connected_firebird(self) -> bool:
        """Verifica conexão com Firebird"""
        success, _ = self.firebird.test_connection()
        return success

    def is_connected_mysql(self) -> bool:
        """Verifica conexão com MySQL"""
        success, _ = self.mysql.test_connection()
        return success
