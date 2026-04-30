"""
TopBackup - Servidor IPC (Named Pipes)
Comunicação entre serviço Windows e GUI
"""

import json
import threading
from typing import Optional, Callable, Dict, Any

# Windows Named Pipes
import win32pipe
import win32file
import pywintypes

from ..config.constants import IPC_PIPE_NAME, IPC_BUFFER_SIZE
from ..utils.logger import get_logger


class IPCServer:
    """Servidor IPC usando Named Pipes do Windows"""

    def __init__(self):
        self.logger = get_logger()
        self.pipe_name = IPC_PIPE_NAME

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._pipe: Optional[int] = None

        # Handlers de comandos
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, command: str, handler: Callable[[Dict], Dict]):
        """
        Registra handler para um comando

        Args:
            command: Nome do comando
            handler: Função que recebe dict e retorna dict
        """
        self._handlers[command] = handler

    def start(self):
        """Inicia o servidor IPC"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._server_loop, daemon=True)
        self._thread.start()

        self.logger.info(f"IPC Server iniciado: {self.pipe_name}")

    def stop(self):
        """Para o servidor IPC"""
        self._running = False

        # Fecha pipe se estiver aberto
        if self._pipe:
            try:
                win32file.CloseHandle(self._pipe)
            except Exception:
                pass
            self._pipe = None

        self.logger.info("IPC Server parado")

    def _server_loop(self):
        """Loop principal do servidor"""
        while self._running:
            try:
                # Cria Named Pipe
                self._pipe = win32pipe.CreateNamedPipe(
                    self.pipe_name,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    IPC_BUFFER_SIZE,
                    IPC_BUFFER_SIZE,
                    0,
                    None
                )

                # Aguarda conexão
                win32pipe.ConnectNamedPipe(self._pipe, None)

                # Processa requisição em thread separada
                threading.Thread(
                    target=self._handle_client,
                    args=(self._pipe,),
                    daemon=True
                ).start()

                # Reseta pipe para nova conexão
                self._pipe = None

            except pywintypes.error as e:
                if self._running:
                    self.logger.error(f"Erro no pipe: {e}")
            except Exception as e:
                if self._running:
                    self.logger.error(f"Erro no servidor IPC: {e}")

    def _handle_client(self, pipe):
        """Processa requisição de um cliente"""
        try:
            # Lê mensagem
            result, data = win32file.ReadFile(pipe, IPC_BUFFER_SIZE)

            if result == 0:
                request = json.loads(data.decode('utf-8'))

                # Processa comando
                response = self._process_command(request)

                # Envia resposta
                response_data = json.dumps(response).encode('utf-8')
                win32file.WriteFile(pipe, response_data)

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON inválido: {e}")
            self._send_error(pipe, "JSON inválido")

        except Exception as e:
            self.logger.error(f"Erro ao processar cliente: {e}")

        finally:
            try:
                win32pipe.DisconnectNamedPipe(pipe)
                win32file.CloseHandle(pipe)
            except Exception:
                pass

    def _process_command(self, request: Dict) -> Dict:
        """Processa comando recebido"""
        command = request.get('command', '')
        params = request.get('params', {})

        self.logger.debug(f"IPC comando recebido: {command}")

        if command in self._handlers:
            try:
                result = self._handlers[command](params)
                return {'success': True, 'data': result}
            except Exception as e:
                self.logger.error(f"Erro no handler {command}: {e}")
                return {'success': False, 'error': str(e)}
        else:
            return {'success': False, 'error': f'Comando desconhecido: {command}'}

    def _send_error(self, pipe, message: str):
        """Envia mensagem de erro"""
        try:
            response = json.dumps({'success': False, 'error': message}).encode('utf-8')
            win32file.WriteFile(pipe, response)
        except Exception:
            pass


class IPCCommands:
    """Comandos IPC disponíveis"""

    STATUS = "STATUS"
    BACKUP_MANUAL = "BACKUP_MANUAL"
    RELOAD_CONFIG = "RELOAD_CONFIG"
    GET_LOGS = "GET_LOGS"
    GET_NEXT_BACKUP = "GET_NEXT_BACKUP"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    SHUTDOWN = "SHUTDOWN"


def create_ipc_handlers(controller) -> Dict[str, Callable]:
    """
    Cria handlers IPC para o controller

    Args:
        controller: AppController

    Returns:
        Dict de handlers
    """
    def handle_status(params):
        return controller.get_status()

    def handle_backup_manual(params):
        result = controller.execute_backup_manual()
        return {
            'success': result.success,
            'message': result.message,
            'arquivo': result.arquivo
        }

    def handle_reload_config(params):
        controller.reload_config()
        return {'reloaded': True}

    def handle_get_logs(params):
        limit = params.get('limit', 50)
        logs = controller.get_backup_logs(limit)
        return {
            'logs': [
                {
                    'id': log.id,
                    'data_inicio': log.data_inicio.isoformat() if log.data_inicio else None,
                    'status': log.status,
                    'arquivo': log.nome_arquivo,
                    'tamanho': log.tamanho_formatado
                }
                for log in logs
            ]
        }

    def handle_get_next_backup(params):
        next_time = controller.get_next_backup_time()
        return {
            'next_backup': next_time.isoformat() if next_time else None
        }

    def handle_pause(params):
        controller.pause()
        return {'paused': True}

    def handle_resume(params):
        controller.resume()
        return {'resumed': True}

    def handle_shutdown(params):
        controller.stop()
        return {'shutdown': True}

    return {
        IPCCommands.STATUS: handle_status,
        IPCCommands.BACKUP_MANUAL: handle_backup_manual,
        IPCCommands.RELOAD_CONFIG: handle_reload_config,
        IPCCommands.GET_LOGS: handle_get_logs,
        IPCCommands.GET_NEXT_BACKUP: handle_get_next_backup,
        IPCCommands.PAUSE: handle_pause,
        IPCCommands.RESUME: handle_resume,
        IPCCommands.SHUTDOWN: handle_shutdown,
    }
