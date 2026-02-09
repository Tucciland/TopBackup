"""
TopBackup - Cliente IPC (Named Pipes)
Cliente para comunicação com o serviço Windows
"""

import json
from typing import Optional, Dict, Any, Tuple

# Windows Named Pipes
import win32file
import win32pipe
import pywintypes

from ..config.constants import IPC_PIPE_NAME, IPC_BUFFER_SIZE
from ..utils.logger import get_logger
from .ipc_server import IPCCommands


class IPCClient:
    """Cliente IPC para comunicação com o serviço"""

    def __init__(self):
        self.logger = get_logger()
        self.pipe_name = IPC_PIPE_NAME
        self.timeout = 5000  # 5 segundos

    def _send_command(self, command: str, params: Optional[Dict] = None) -> Tuple[bool, Any]:
        """
        Envia comando para o serviço

        Args:
            command: Nome do comando
            params: Parâmetros opcionais

        Returns:
            Tuple[bool, Any]: (sucesso, dados ou erro)
        """
        try:
            # Conecta ao pipe
            pipe = win32file.CreateFile(
                self.pipe_name,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )

            try:
                # Prepara mensagem
                request = {
                    'command': command,
                    'params': params or {}
                }
                request_data = json.dumps(request).encode('utf-8')

                # Envia
                win32file.WriteFile(pipe, request_data)

                # Lê resposta
                result, response_data = win32file.ReadFile(pipe, IPC_BUFFER_SIZE)

                if result == 0:
                    response = json.loads(response_data.decode('utf-8'))

                    if response.get('success'):
                        return True, response.get('data')
                    else:
                        return False, response.get('error', 'Erro desconhecido')

                return False, "Falha ao ler resposta"

            finally:
                win32file.CloseHandle(pipe)

        except pywintypes.error as e:
            error_code = e.args[0]

            if error_code == 2:  # ERROR_FILE_NOT_FOUND
                return False, "Serviço não está em execução"
            elif error_code == 231:  # ERROR_PIPE_BUSY
                return False, "Serviço ocupado, tente novamente"
            else:
                return False, f"Erro de comunicação: {e}"

        except json.JSONDecodeError:
            return False, "Resposta inválida do serviço"

        except Exception as e:
            self.logger.error(f"Erro IPC: {e}")
            return False, str(e)

    def get_status(self) -> Tuple[bool, Dict]:
        """Obtém status do serviço"""
        return self._send_command(IPCCommands.STATUS)

    def execute_backup(self) -> Tuple[bool, Dict]:
        """Solicita execução de backup manual"""
        return self._send_command(IPCCommands.BACKUP_MANUAL)

    def reload_config(self) -> Tuple[bool, Dict]:
        """Solicita recarga de configurações"""
        return self._send_command(IPCCommands.RELOAD_CONFIG)

    def get_logs(self, limit: int = 50) -> Tuple[bool, Dict]:
        """Obtém logs de backup"""
        return self._send_command(IPCCommands.GET_LOGS, {'limit': limit})

    def get_next_backup(self) -> Tuple[bool, Dict]:
        """Obtém próximo horário de backup"""
        return self._send_command(IPCCommands.GET_NEXT_BACKUP)

    def pause(self) -> Tuple[bool, Dict]:
        """Pausa o agendamento"""
        return self._send_command(IPCCommands.PAUSE)

    def resume(self) -> Tuple[bool, Dict]:
        """Resume o agendamento"""
        return self._send_command(IPCCommands.RESUME)

    def shutdown(self) -> Tuple[bool, Dict]:
        """Solicita encerramento do serviço"""
        return self._send_command(IPCCommands.SHUTDOWN)

    def is_service_running(self) -> bool:
        """Verifica se o serviço está em execução"""
        success, _ = self.get_status()
        return success


def check_service_status() -> str:
    """
    Verifica status do serviço Windows

    Returns:
        Status: 'running', 'stopped', 'not_installed'
    """
    try:
        import win32serviceutil

        from ..config.constants import SERVICE_NAME

        status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
        state = status[1]

        if state == 4:  # SERVICE_RUNNING
            return 'running'
        elif state == 1:  # SERVICE_STOPPED
            return 'stopped'
        else:
            return 'transitioning'

    except Exception as e:
        if 'service does not exist' in str(e).lower():
            return 'not_installed'
        return 'unknown'
