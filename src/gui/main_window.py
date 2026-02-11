"""
TopBackup - Janela Principal
Interface CustomTkinter do aplicativo
"""

import customtkinter as ctk
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path
import threading
import sys

from ..config.settings import Settings
from ..core.app_controller import AppController, AppState
from ..core.backup_engine import BackupResult
from ..version import VERSION, APP_NAME
from ..utils.logger import get_logger
from .tray_icon import TrayIcon
from .dialogs import show_info, show_error, show_warning, LogViewerDialog, SettingsDialog, AgendaListDialog


class MainWindow(ctk.CTk):
    """Janela principal do TopBackup"""

    def __init__(self, controller: AppController, settings: Settings):
        super().__init__()

        self.controller = controller
        self.settings = settings
        self.logger = get_logger()

        # Configuração da janela
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("780x550")
        self.minsize(750, 500)

        # Ícone da janela (barra de tarefas)
        self._set_window_icon()

        # Tema
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # System Tray
        self.tray_icon: Optional[TrayIcon] = None

        # Configura callbacks do controller
        self.controller.set_state_callback(self._on_state_change)
        self.controller.set_backup_progress_callback(self._on_backup_progress)
        self.controller.set_notification_callback(self._on_notification)

        # Cria interface
        self._create_widgets()

        # Atualiza interface
        self._update_status()

        # Configura eventos de janela
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Timer para atualização automática
        self._start_update_timer()

    def _set_window_icon(self):
        """Define o ícone da janela (barra de tarefas)"""
        try:
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).parent.parent.parent

            icon_path = base_dir / "assets" / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception as e:
            self.logger.warning(f"Erro ao definir ícone: {e}")

    def _create_widgets(self):
        """Cria todos os widgets da interface"""
        # Frame principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Header
        self._create_header()

        # Área de status
        self._create_status_area()

        # Área de ações
        self._create_actions_area()

        # Área de logs resumidos
        self._create_logs_area()

        # Footer com informações
        self._create_footer()

    def _create_header(self):
        """Cria o cabeçalho"""
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        # Logo/Título
        title_label = ctk.CTkLabel(
            header_frame,
            text=APP_NAME,
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left")

        # Versão
        version_label = ctk.CTkLabel(
            header_frame,
            text=f"v{VERSION}",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        version_label.pack(side="left", padx=10)

        # Indicador de status
        self.status_indicator = ctk.CTkLabel(
            header_frame,
            text="●",
            font=ctk.CTkFont(size=20),
            text_color="green"
        )
        self.status_indicator.pack(side="right")

        self.status_text = ctk.CTkLabel(
            header_frame,
            text="Rodando",
            font=ctk.CTkFont(size=12)
        )
        self.status_text.pack(side="right", padx=5)

    def _create_status_area(self):
        """Cria área de status com 2 blocos lado a lado"""
        # Container principal para os 2 blocos
        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(fill="x", pady=10)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        # ========== BLOCO ESQUERDO: Dados da Empresa ==========
        left_frame = ctk.CTkFrame(container)
        left_frame.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        left_frame.columnconfigure(1, weight=1)

        # Empresa
        ctk.CTkLabel(left_frame, text="Empresa:", anchor="w").grid(
            row=0, column=0, padx=10, pady=5, sticky="w"
        )
        self.empresa_label = ctk.CTkLabel(left_frame, text="-", anchor="w")
        self.empresa_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # CNPJ
        ctk.CTkLabel(left_frame, text="CNPJ:", anchor="w").grid(
            row=1, column=0, padx=10, pady=5, sticky="w"
        )
        self.cnpj_label = ctk.CTkLabel(left_frame, text="-", anchor="w")
        self.cnpj_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Local do Banco
        ctk.CTkLabel(left_frame, text="Banco:", anchor="w").grid(
            row=2, column=0, padx=10, pady=5, sticky="w"
        )
        self.banco_label = ctk.CTkLabel(left_frame, text="-", anchor="w")
        self.banco_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # Próximo backup
        ctk.CTkLabel(left_frame, text="Próximo Backup:", anchor="w").grid(
            row=3, column=0, padx=10, pady=5, sticky="w"
        )
        self.next_backup_label = ctk.CTkLabel(left_frame, text="-", anchor="w")
        self.next_backup_label.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        # ========== BLOCO DIREITO: Status e Destinos ==========
        right_frame = ctk.CTkFrame(container)
        right_frame.grid(row=0, column=1, padx=(5, 0), sticky="nsew")
        right_frame.columnconfigure(1, weight=1)

        # Último backup
        ctk.CTkLabel(right_frame, text="Último Backup:", anchor="w").grid(
            row=0, column=0, padx=10, pady=5, sticky="w"
        )
        self.last_backup_label = ctk.CTkLabel(right_frame, text="-", anchor="w")
        self.last_backup_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Conexões
        ctk.CTkLabel(right_frame, text="Conexões:", anchor="w").grid(
            row=1, column=0, padx=10, pady=5, sticky="w"
        )
        self.connections_label = ctk.CTkLabel(right_frame, text="-", anchor="w")
        self.connections_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Destino 1
        ctk.CTkLabel(right_frame, text="Destino 1:", anchor="w").grid(
            row=2, column=0, padx=10, pady=5, sticky="w"
        )
        self.destino1_label = ctk.CTkLabel(right_frame, text="-", anchor="w")
        self.destino1_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # Destino 2
        ctk.CTkLabel(right_frame, text="Destino 2:", anchor="w").grid(
            row=3, column=0, padx=10, pady=5, sticky="w"
        )
        self.destino2_label = ctk.CTkLabel(right_frame, text="-", anchor="w")
        self.destino2_label.grid(row=3, column=1, padx=10, pady=5, sticky="w")

    def _create_actions_area(self):
        """Cria área de ações"""
        actions_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        actions_frame.pack(fill="x", pady=10)

        # Botão de backup manual
        self.backup_btn = ctk.CTkButton(
            actions_frame,
            text="Backup Agora",
            command=self._on_backup_click,
            width=150,
            height=40
        )
        self.backup_btn.pack(side="left", padx=5)

        # Botão de pausar/resumir
        self.pause_btn = ctk.CTkButton(
            actions_frame,
            text="Pausar",
            command=self._on_pause_click,
            width=100,
            height=40,
            fg_color="orange",
            hover_color="darkorange"
        )
        self.pause_btn.pack(side="left", padx=5)

        # Botão de configurações
        settings_btn = ctk.CTkButton(
            actions_frame,
            text="Configurações",
            command=self._on_settings_click,
            width=120,
            height=40
        )
        settings_btn.pack(side="left", padx=5)

        # Botão de logs
        logs_btn = ctk.CTkButton(
            actions_frame,
            text="Ver Logs",
            command=self._on_logs_click,
            width=100,
            height=40
        )
        logs_btn.pack(side="left", padx=5)

        # Botão de agendas
        agendas_btn = ctk.CTkButton(
            actions_frame,
            text="Agendas",
            command=self._on_agendas_click,
            width=80,
            height=40,
            fg_color="purple",
            hover_color="darkviolet"
        )
        agendas_btn.pack(side="left", padx=3)

        # Botão de receber config do Firebird
        refresh_btn = ctk.CTkButton(
            actions_frame,
            text="Receber Config",
            command=self._on_refresh_click,
            width=110,
            height=40,
            fg_color="teal",
            hover_color="darkcyan"
        )
        refresh_btn.pack(side="left", padx=3)

    def _create_logs_area(self):
        """Cria área de logs resumidos"""
        logs_frame = ctk.CTkFrame(self.main_frame)
        logs_frame.pack(fill="both", expand=True, pady=10)

        # Título
        ctk.CTkLabel(
            logs_frame,
            text="Últimos Backups",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        # Área de texto para logs
        self.logs_text = ctk.CTkTextbox(logs_frame, height=150)
        self.logs_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.logs_text.configure(state="disabled")

    def _create_footer(self):
        """Cria rodapé"""
        footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=30)
        footer_frame.pack(fill="x")

        # Barra de progresso (oculta inicialmente)
        self.progress_bar = ctk.CTkProgressBar(footer_frame)
        self.progress_bar.set(0)

        # Label de progresso
        self.progress_label = ctk.CTkLabel(
            footer_frame,
            text="",
            font=ctk.CTkFont(size=11)
        )

    def _update_status(self):
        """Atualiza informações de status"""
        status = self.controller.get_status()

        # Empresa e CNPJ
        self.empresa_label.configure(text=status.get('empresa', '-') or '-')
        self.cnpj_label.configure(text=status.get('cnpj', '-') or '-')

        # Local do banco
        banco_path = status.get('database_path', '-') or '-'
        # Trunca se muito longo
        if len(banco_path) > 50:
            banco_path = "..." + banco_path[-47:]
        self.banco_label.configure(text=banco_path)

        # Próximo backup
        next_backup = status.get('next_backup')
        if next_backup:
            self.next_backup_label.configure(
                text=next_backup.strftime("%d/%m/%Y %H:%M")
            )
        else:
            self.next_backup_label.configure(text="Não agendado")

        # Último backup
        last_backup = status.get('last_backup')
        last_success = status.get('last_backup_success')
        if last_backup:
            color = "green" if last_success else "red"
            self.last_backup_label.configure(text=last_backup, text_color=color)
        else:
            self.last_backup_label.configure(text="Nenhum", text_color="gray")

        # Conexões
        fb_ok = status.get('firebird_connected', False)
        mysql_ok = status.get('mysql_connected', False)
        conn_text = f"Firebird: {'OK' if fb_ok else 'Erro'} | MySQL: {'OK' if mysql_ok else 'Erro'}"
        conn_color = "green" if (fb_ok and mysql_ok) else "orange"
        self.connections_label.configure(text=conn_text, text_color=conn_color)

        # Destinos
        dest1 = status.get('destino1', '-') or '-'
        dest2 = status.get('destino2', '-') or '-'
        if len(dest1) > 50:
            dest1 = "..." + dest1[-47:]
        if len(dest2) > 50:
            dest2 = "..." + dest2[-47:]
        self.destino1_label.configure(text=dest1)
        self.destino2_label.configure(text=dest2 if dest2 != '-' else "(não configurado)")

        # Status geral
        state = status.get('state', 'unknown')
        self._update_status_indicator(state)

        # Atualiza logs
        self._update_logs_display()

    def _update_status_indicator(self, state: str):
        """Atualiza indicador de status"""
        colors = {
            'running': ('green', 'Rodando'),
            'backup_running': ('blue', 'Backup em andamento'),
            'paused': ('orange', 'Pausado'),
            'error': ('red', 'Erro'),
            'stopped': ('gray', 'Parado'),
            'initializing': ('yellow', 'Inicializando'),
        }

        color, text = colors.get(state, ('gray', state))
        self.status_indicator.configure(text_color=color)
        self.status_text.configure(text=text)

    def _update_logs_display(self):
        """Atualiza exibição de logs"""
        logs = self.controller.get_backup_logs(limit=10)

        self.logs_text.configure(state="normal")
        self.logs_text.delete("1.0", "end")

        for log in logs:
            status_icon = "✓" if log.status == 'S' else "✗" if log.status == 'F' else "…"
            data = log.data_inicio.strftime("%d/%m %H:%M") if log.data_inicio else "-"
            arquivo = log.nome_arquivo or "-"
            tamanho = log.tamanho_formatado or ""
            tipo = "[Manual]" if getattr(log, 'manual', False) else "[Auto]"

            line = f"{status_icon} {data} | {arquivo} {tamanho} {tipo}\n"
            self.logs_text.insert("end", line)

        self.logs_text.configure(state="disabled")

    def _start_update_timer(self):
        """Inicia timer de atualização automática"""
        self._update_status()
        self.after(30000, self._start_update_timer)  # 30 segundos

    # ============ CALLBACKS ============

    def _on_state_change(self, state: AppState):
        """Callback de mudança de estado"""
        self.after(0, lambda: self._update_status_indicator(state.value))

        # Atualiza botões
        if state == AppState.BACKUP_RUNNING:
            self.after(0, lambda: self.backup_btn.configure(state="disabled"))
        else:
            self.after(0, lambda: self.backup_btn.configure(state="normal"))

    def _on_backup_progress(self, message: str):
        """Callback de progresso do backup"""
        if message:
            self.after(0, lambda: self._show_progress(message))
        else:
            # Mensagem vazia indica fim do backup - esconde a barra
            self.after(0, self._hide_progress)

    def _on_notification(self, title: str, message: str):
        """Callback de notificação"""
        # Notifica via tray se minimizado
        if self.tray_icon and self.state() == 'iconic':
            self.tray_icon.notify(title, message)
        else:
            self.after(0, lambda: show_info(self, title, message))

    def _show_progress(self, message: str):
        """Mostra progresso na interface"""
        self.progress_label.configure(text=message)
        self.progress_label.pack(side="left", padx=10)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=10)
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

    def _hide_progress(self):
        """Esconde barra de progresso"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()

    # ============ AÇÕES ============

    def _on_backup_click(self):
        """Inicia backup manual"""
        self.backup_btn.configure(state="disabled")

        def run_backup():
            result = self.controller.execute_backup_manual()
            self.after(0, lambda: self._on_backup_complete(result))

        thread = threading.Thread(target=run_backup, daemon=True)
        thread.start()

    def _on_backup_complete(self, result: BackupResult):
        """Callback de backup completo"""
        self._hide_progress()
        self.backup_btn.configure(state="normal")
        self._update_status()
        # Notificação já é enviada pelo controller via _on_notification callback

    def _on_pause_click(self):
        """Pausa/resume agendamento"""
        if self.controller.state == AppState.PAUSED:
            self.controller.resume()
            self.pause_btn.configure(text="Pausar", fg_color="orange")
        else:
            self.controller.pause()
            self.pause_btn.configure(text="Resumir", fg_color="green")

        self._update_status()

    def _on_settings_click(self):
        """Abre configurações"""
        # Recarrega settings para garantir valores atualizados
        self.settings = Settings.load()
        dialog = SettingsDialog(self, self.settings, on_save_callback=self._on_settings_saved)
        dialog.grab_set()

    def _on_settings_saved(self):
        """Callback após salvar configurações"""
        # Recarrega settings em todos os componentes do controller
        self.controller.refresh_settings()
        # Atualiza referência local
        self.settings = self.controller.settings
        # Atualiza interface
        self._update_status()

    def _on_logs_click(self):
        """Abre visualizador de logs"""
        dialog = LogViewerDialog(self)
        dialog.grab_set()

    def _on_agendas_click(self):
        """Abre visualizador de agendas"""
        agendas = self.controller.get_all_agendas()
        if agendas:
            dialog = AgendaListDialog(self, agendas)
            dialog.grab_set()
        else:
            show_warning(self, "Agendas", "Nenhuma agenda de backup encontrada")

    def _on_refresh_click(self):
        """Atualiza configurações"""
        self.controller.reload_config()
        self._update_status()
        show_info(self, "Configurações", "Configurações atualizadas")

    def _on_close(self):
        """Callback de fechar janela"""
        if self.settings.app.start_minimized:
            self.withdraw()  # Minimiza para tray
            if self.tray_icon:
                self.tray_icon.notify("TopBackup", "Minimizado para a bandeja do sistema")
        else:
            self._quit_app()

    def _quit_app(self):
        """Encerra o aplicativo"""
        self.controller.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()

    # ============ TRAY ============

    def setup_tray(self, icon_path: str):
        """Configura System Tray"""
        self.tray_icon = TrayIcon(
            icon_path=icon_path,
            app_name=APP_NAME,
            on_show=self._show_window,
            on_backup=self._on_backup_click,
            on_quit=self._quit_app
        )
        self.tray_icon.start()

    def _show_window(self):
        """Mostra a janela"""
        self.deiconify()
        self.lift()
        self.focus_force()

    def run(self):
        """Inicia o loop principal"""
        self.mainloop()
