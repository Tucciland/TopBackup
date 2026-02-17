"""
TopBackup - Serviço Windows
Implementação do serviço Windows usando pywin32
"""

import sys
import os
import time
import threading

import win32serviceutil
import win32service
import win32event
import servicemanager

# Adiciona o diretório src ao path
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.insert(0, base_path)

from src.config.settings import Settings
from src.config.constants import SERVICE_NAME, SERVICE_DISPLAY_NAME, SERVICE_DESCRIPTION
from src.core.app_controller import AppController
from src.service.ipc_server import IPCServer, create_ipc_handlers
from src.utils.logger import get_logger


class TopBackupService(win32serviceutil.ServiceFramework):
    """Serviço Windows do TopBackup"""

    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)

        # Evento para sinalizar parada
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

        self.logger = get_logger()
        self.settings = None
        self.controller = None
        self.ipc_server = None

        self._is_running = False

    def SvcStop(self):
        """Chamado quando o serviço deve parar"""
        self.logger.info("Serviço recebeu sinal de parada")

        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        self._is_running = False
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        """Chamado quando o serviço inicia"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )

        self.logger.info("Serviço TopBackup iniciando...")

        try:
            self._main()
        except Exception as e:
            self.logger.critical(f"Erro fatal no serviço: {e}", exc_info=True)
            servicemanager.LogErrorMsg(f"TopBackup: Erro fatal - {e}")

    def _main(self):
        """Loop principal do serviço"""
        try:
            # Carrega configurações
            self.settings = Settings.load()

            if not self.settings.is_configured():
                self.logger.error("Serviço não configurado")
                return

            # Inicializa controller
            self.controller = AppController(self.settings)

            success, msg = self.controller.initialize()
            if not success:
                self.logger.error(f"Falha na inicialização: {msg}")
                return

            # Inicia servidor IPC
            self.ipc_server = IPCServer()

            # Registra handlers
            handlers = create_ipc_handlers(self.controller)
            for command, handler in handlers.items():
                self.ipc_server.register_handler(command, handler)

            self.ipc_server.start()

            # Inicia controller
            self.controller.start()

            self._is_running = True
            self.logger.info("Serviço TopBackup iniciado com sucesso")

            # Loop principal - aguarda sinal de parada
            while self._is_running:
                # Aguarda evento de parada por 1 segundo
                rc = win32event.WaitForSingleObject(self.stop_event, 1000)

                if rc == win32event.WAIT_OBJECT_0:
                    # Evento de parada sinalizado
                    break

            # Cleanup
            self._shutdown()

        except Exception as e:
            self.logger.critical(f"Erro no serviço: {e}", exc_info=True)
            raise

    def _shutdown(self):
        """Encerra o serviço gracefully"""
        self.logger.info("Encerrando serviço...")

        try:
            if self.ipc_server:
                self.ipc_server.stop()

            if self.controller:
                self.controller.stop()

            self.logger.info("Serviço encerrado com sucesso")

        except Exception as e:
            self.logger.error(f"Erro ao encerrar serviço: {e}")


def install_service():
    """Instala o serviço Windows"""
    try:
        # Caminho do executável
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = sys.executable
            script_path = os.path.abspath(__file__)

        win32serviceutil.InstallService(
            TopBackupService._svc_reg_class_,
            SERVICE_NAME,
            SERVICE_DISPLAY_NAME,
            startType=win32service.SERVICE_AUTO_START,
            description=SERVICE_DESCRIPTION
        )

        print(f"Serviço '{SERVICE_NAME}' instalado com sucesso")
        return True

    except Exception as e:
        print(f"Erro ao instalar serviço: {e}")
        return False


def uninstall_service():
    """Remove o serviço Windows"""
    try:
        win32serviceutil.RemoveService(SERVICE_NAME)
        print(f"Serviço '{SERVICE_NAME}' removido com sucesso")
        return True

    except Exception as e:
        print(f"Erro ao remover serviço: {e}")
        return False


def start_service():
    """Inicia o serviço Windows"""
    try:
        win32serviceutil.StartService(SERVICE_NAME)
        print(f"Serviço '{SERVICE_NAME}' iniciado")
        return True

    except Exception as e:
        print(f"Erro ao iniciar serviço: {e}")
        return False


def stop_service():
    """Para o serviço Windows"""
    try:
        win32serviceutil.StopService(SERVICE_NAME)
        print(f"Serviço '{SERVICE_NAME}' parado")
        return True

    except Exception as e:
        print(f"Erro ao parar serviço: {e}")
        return False


def query_service_status():
    """Consulta status do serviço"""
    try:
        status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
        state = status[1]

        states = {
            1: 'Parado',
            2: 'Iniciando',
            3: 'Parando',
            4: 'Executando',
            5: 'Continuando',
            6: 'Pausando',
            7: 'Pausado'
        }

        return states.get(state, 'Desconhecido')

    except Exception as e:
        return f'Não instalado ou erro: {e}'


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # Quando executado pelo SCM (Service Control Manager)
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TopBackupService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Quando executado via linha de comando
        win32serviceutil.HandleCommandLine(TopBackupService)
