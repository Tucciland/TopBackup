"""
TopBackup - Gerenciador de Heartbeat
Envia sinais de vida periódicos para o servidor
"""

import socket
import platform
from datetime import datetime
from typing import Optional
import requests

from ..database.models import Heartbeat
from ..database.mysql_client import MySQLClient
from ..config.settings import Settings
from ..version import VERSION
from ..utils.logger import get_logger


class HeartbeatManager:
    """Gerenciador de heartbeat para monitoramento"""

    def __init__(self, settings: Settings, mysql_client: MySQLClient):
        self.settings = settings
        self.mysql = mysql_client
        self.logger = get_logger()

        self._last_heartbeat: Optional[datetime] = None
        self._ip_publico: Optional[str] = None

    def send_heartbeat(self, status_servico: str = "running") -> bool:
        """
        Envia heartbeat para o servidor

        Args:
            status_servico: Status do serviço (running, stopped, error)

        Returns:
            True se enviado com sucesso
        """
        try:
            empresa_id = self.settings.app.empresa_id

            if not empresa_id:
                self.logger.warning("ID da empresa não configurado")
                return False

            # Cria heartbeat
            heartbeat = Heartbeat(
                id_empresa=empresa_id,
                data_hora=datetime.now(),
                versao_app=VERSION,
                hostname=self._get_hostname(),
                ip_publico=self._get_public_ip(),
                status_servico=status_servico
            )

            # Insere no MySQL
            result = self.mysql.insert_heartbeat(heartbeat)

            if result:
                # Atualiza último contato da empresa
                self.mysql.update_empresa_contato(empresa_id)
                self._last_heartbeat = datetime.now()
                self.logger.debug(f"Heartbeat enviado: {status_servico}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Erro ao enviar heartbeat: {e}")
            return False

    def _get_hostname(self) -> str:
        """Obtém hostname da máquina"""
        try:
            return socket.gethostname()
        except Exception:
            return "unknown"

    def _get_public_ip(self) -> Optional[str]:
        """Obtém IP público da máquina"""
        # Usa cache para evitar múltiplas requisições
        if self._ip_publico:
            return self._ip_publico

        try:
            # Tenta múltiplos serviços
            services = [
                'https://api.ipify.org',
                'https://ifconfig.me/ip',
                'https://icanhazip.com',
            ]

            for service in services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        self._ip_publico = response.text.strip()
                        return self._ip_publico
                except requests.RequestException:
                    continue

            return None

        except Exception:
            return None

    def get_system_info(self) -> dict:
        """Retorna informações do sistema"""
        return {
            'hostname': self._get_hostname(),
            'ip_publico': self._get_public_ip(),
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': platform.python_version(),
            'app_version': VERSION,
            'last_heartbeat': self._last_heartbeat
        }

    @property
    def last_heartbeat(self) -> Optional[datetime]:
        """Retorna último heartbeat enviado"""
        return self._last_heartbeat
