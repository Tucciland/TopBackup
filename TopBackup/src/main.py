"""
TopBackup - Entry Point
Ponto de entrada principal do aplicativo
"""

import sys
import os
import argparse
import ctypes
from pathlib import Path

# Adiciona diretório src ao path ANTES de qualquer import do projeto
if getattr(sys, 'frozen', False):
    # Executando como executável - usa _MEIPASS para imports
    BASE_DIR = Path(sys._MEIPASS)
    # Diretório de instalação real
    INSTALL_DIR = Path(r"C:\TOPBACKUP")
else:
    # Executando como script Python
    BASE_DIR = Path(__file__).parent.parent
    INSTALL_DIR = BASE_DIR

sys.path.insert(0, str(BASE_DIR))


def initialize_firebird_library():
    """Inicializa a biblioteca Firebird antes de qualquer uso"""
    from src.utils.firebird_loader import initialize_firebird, get_python_architecture

    success, message = initialize_firebird()
    if not success:
        arch = get_python_architecture()
        print(f"AVISO: {message}")
        print(f"\nPara resolver, copie o fbclient.dll ({arch}-bit) para:")
        print(f"  {INSTALL_DIR / 'assets' / 'firebird' / ('x64' if arch == 64 else 'x86')}")
        print("\nO fbclient.dll pode ser encontrado na instalação do Firebird:")
        if arch == 64:
            print("  C:\\Program Files\\Firebird\\Firebird_2_5\\bin\\fbclient.dll (64-bit)")
        else:
            print("  C:\\Program Files (x86)\\Firebird\\Firebird_2_5\\bin\\fbclient.dll (32-bit)")
    return success


def is_admin() -> bool:
    """Verifica se está rodando como administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """Reinicia o aplicativo como administrador"""
    try:
        if getattr(sys, 'frozen', False):
            executable = sys.executable
        else:
            executable = sys.executable
            script = os.path.abspath(__file__)
            # Para scripts, precisamos passar o interpretador e o script
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", executable, f'"{script}"', None, 1
            )
            return

        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, "", None, 1
        )
    except Exception as e:
        print(f"Erro ao solicitar privilégios de administrador: {e}")


def run_gui():
    """Executa o aplicativo com interface gráfica"""
    from src.config.settings import Settings
    from src.core.app_controller import AppController
    from src.gui.main_window import MainWindow
    from src.gui.setup_wizard import SetupWizard
    from src.utils.logger import get_logger

    logger = get_logger()
    logger.info("Iniciando TopBackup em modo GUI")

    # Carrega configurações
    settings = Settings.load()

    # Verifica primeira execução
    if settings.app.first_run or not settings.is_configured():
        logger.info("Primeira execução - abrindo wizard de configuração")

        # Cria janela temporária para o wizard
        import customtkinter as ctk
        root = ctk.CTk()
        root.withdraw()

        wizard = SetupWizard(root)
        root.wait_window(wizard)

        if not wizard.completed:
            logger.info("Configuração cancelada pelo usuário")
            root.destroy()
            sys.exit(0)

        settings = wizard.settings
        root.destroy()

    # Inicializa controller
    controller = AppController(settings)

    success, msg = controller.initialize()
    if not success:
        logger.error(f"Falha na inicialização: {msg}")

        import customtkinter as ctk
        from tkinter import messagebox

        root = ctk.CTk()
        root.withdraw()
        messagebox.showerror("Erro de Inicialização", msg)
        root.destroy()
        sys.exit(1)

    # Cria janela principal
    window = MainWindow(controller, settings)

    # Configura System Tray
    # Tenta primeiro no diretório de instalação, depois nos embutidos
    icon_path = INSTALL_DIR / "assets" / "icon.ico"
    if not icon_path.exists():
        icon_path = BASE_DIR / "assets" / "icon.ico"
    if icon_path.exists():
        window.setup_tray(str(icon_path))

    # Inicia controller
    controller.start()

    # Atualiza status após scheduler iniciar (para mostrar próximo backup)
    window._update_status()

    # Minimiza se configurado
    if settings.app.start_minimized:
        window.withdraw()

    # Executa loop principal
    try:
        window.run()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()


def run_service():
    """Executa como serviço Windows"""
    from src.service.windows_service import TopBackupService
    import win32serviceutil
    import servicemanager

    if len(sys.argv) == 1:
        # Executado pelo SCM
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TopBackupService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Executado via linha de comando
        win32serviceutil.HandleCommandLine(TopBackupService)


def install_service():
    """Instala o serviço Windows"""
    if not is_admin():
        print("É necessário executar como administrador para instalar o serviço")
        run_as_admin()
        sys.exit(0)

    from src.service.windows_service import install_service as do_install
    do_install()


def uninstall_service():
    """Remove o serviço Windows"""
    if not is_admin():
        print("É necessário executar como administrador para remover o serviço")
        run_as_admin()
        sys.exit(0)

    from src.service.windows_service import uninstall_service as do_uninstall
    do_uninstall()


def start_service_cmd():
    """Inicia o serviço via linha de comando"""
    if not is_admin():
        print("É necessário executar como administrador")
        run_as_admin()
        sys.exit(0)

    from src.service.windows_service import start_service
    start_service()


def stop_service_cmd():
    """Para o serviço via linha de comando"""
    if not is_admin():
        print("É necessário executar como administrador")
        run_as_admin()
        sys.exit(0)

    from src.service.windows_service import stop_service
    stop_service()


def service_status():
    """Exibe status do serviço"""
    from src.service.windows_service import query_service_status
    status = query_service_status()
    print(f"Status do serviço: {status}")


def run_backup_now():
    """Executa backup imediatamente (sem GUI)"""
    from src.config.settings import Settings
    from src.core.app_controller import AppController
    from src.utils.logger import get_logger

    logger = get_logger()
    logger.info("Executando backup manual via CLI")

    settings = Settings.load()

    if not settings.is_configured():
        print("Erro: Aplicativo não configurado. Execute primeiro com a interface gráfica.")
        sys.exit(1)

    controller = AppController(settings)

    success, msg = controller.initialize()
    if not success:
        print(f"Erro de inicialização: {msg}")
        sys.exit(1)

    result = controller.execute_backup_manual()

    if result.success:
        print(f"Backup concluído: {result.arquivo}")
        print(f"Tamanho: {result.tamanho_formatado}")
    else:
        print(f"Falha no backup: {result.message}")
        sys.exit(1)

    controller.stop()


def ensure_installation():
    """
    Verifica se o app está instalado em C:\TOPBACKUP.
    Se não estiver, instala e reinicia.
    """
    if not getattr(sys, 'frozen', False):
        # Em desenvolvimento, não instala
        return False

    from src.core.installer import ensure_installed, show_permission_error

    needs_exit, message = ensure_installed()

    if needs_exit:
        if "permissão" in message.lower() or "permission" in message.lower():
            show_permission_error()
        # App foi instalado e nova instância foi iniciada
        sys.exit(0)

    return False


def main():
    """Função principal"""
    # 1. Garante instalação em C:\TOPBACKUP (se executável)
    ensure_installation()

    # 2. Inicializa Firebird ANTES de qualquer import que use fdb
    initialize_firebird_library()

    parser = argparse.ArgumentParser(
        description="TopBackup - Sistema de Backup Automático",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  topbackup                    Inicia a interface gráfica
  topbackup --service          Executa como serviço Windows
  topbackup --install          Instala o serviço Windows
  topbackup --uninstall        Remove o serviço Windows
  topbackup --start            Inicia o serviço Windows
  topbackup --stop             Para o serviço Windows
  topbackup --status           Exibe status do serviço
  topbackup --backup           Executa backup imediatamente
        """
    )

    parser.add_argument(
        '--service',
        action='store_true',
        help='Executa como serviço Windows'
    )
    parser.add_argument(
        '--install',
        action='store_true',
        help='Instala o serviço Windows'
    )
    parser.add_argument(
        '--uninstall',
        action='store_true',
        help='Remove o serviço Windows'
    )
    parser.add_argument(
        '--start',
        action='store_true',
        help='Inicia o serviço Windows'
    )
    parser.add_argument(
        '--stop',
        action='store_true',
        help='Para o serviço Windows'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Exibe status do serviço'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Executa backup imediatamente (sem GUI)'
    )
    parser.add_argument(
        '--version',
        action='store_true',
        help='Exibe versão do aplicativo'
    )

    args = parser.parse_args()

    if args.version:
        from src.version import VERSION, APP_NAME
        print(f"{APP_NAME} v{VERSION}")
        sys.exit(0)

    if args.service:
        run_service()
    elif args.install:
        install_service()
    elif args.uninstall:
        uninstall_service()
    elif args.start:
        start_service_cmd()
    elif args.stop:
        stop_service_cmd()
    elif args.status:
        service_status()
    elif args.backup:
        run_backup_now()
    else:
        run_gui()


if __name__ == '__main__':
    main()
