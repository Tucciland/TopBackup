"""
TopBackup - Diálogos Auxiliares
Diálogos de mensagem, progresso e configurações
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Callable
import threading

from ..config.settings import Settings
from ..utils.logger import get_logger


def show_info(parent, title: str, message: str):
    """Mostra diálogo de informação"""
    messagebox.showinfo(title, message, parent=parent)


def show_error(parent, title: str, message: str):
    """Mostra diálogo de erro"""
    messagebox.showerror(title, message, parent=parent)


def show_warning(parent, title: str, message: str):
    """Mostra diálogo de aviso"""
    messagebox.showwarning(title, message, parent=parent)


def show_confirm(parent, title: str, message: str) -> bool:
    """Mostra diálogo de confirmação"""
    return messagebox.askyesno(title, message, parent=parent)


class BackupProgressDialog(ctk.CTkToplevel):
    """Diálogo de progresso de backup"""

    def __init__(self, parent, title: str = "Backup em Andamento"):
        super().__init__(parent)

        self.title(title)
        self.geometry("400x200")
        self.resizable(False, False)

        # Centraliza
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 400) // 2
        y = (self.winfo_screenheight() - 200) // 2
        self.geometry(f"+{x}+{y}")

        # Widgets
        self._create_widgets()

        # Resultado
        self.cancelled = False

        # Modal
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _create_widgets(self):
        """Cria widgets"""
        # Frame principal
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)

        # Mensagem
        self.message_label = ctk.CTkLabel(
            main,
            text="Iniciando backup...",
            font=ctk.CTkFont(size=14)
        )
        self.message_label.pack(pady=10)

        # Barra de progresso
        self.progress = ctk.CTkProgressBar(main, width=300)
        self.progress.pack(pady=10)
        self.progress.configure(mode="indeterminate")
        self.progress.start()

        # Porcentagem
        self.percent_label = ctk.CTkLabel(main, text="")
        self.percent_label.pack(pady=5)

        # Botão cancelar
        self.cancel_btn = ctk.CTkButton(
            main,
            text="Cancelar",
            command=self._on_cancel,
            fg_color="red",
            hover_color="darkred"
        )
        self.cancel_btn.pack(pady=10)

    def update_progress(self, message: str, progress: Optional[float] = None):
        """Atualiza progresso"""
        self.message_label.configure(text=message)

        if progress is not None:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress.set(progress)
            self.percent_label.configure(text=f"{int(progress * 100)}%")

    def _on_cancel(self):
        """Callback de cancelar"""
        self.cancelled = True
        self.destroy()

    def close(self):
        """Fecha o diálogo"""
        self.progress.stop()
        self.destroy()


class LogViewerDialog(ctk.CTkToplevel):
    """Diálogo para visualização de logs"""

    def __init__(self, parent):
        super().__init__(parent)

        self.logger = get_logger()

        self.title("Visualizador de Logs")
        self.geometry("800x500")

        # Widgets
        self._create_widgets()

        # Carrega logs
        self._load_logs()

    def _create_widgets(self):
        """Cria widgets"""
        # Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            toolbar,
            text="Atualizar",
            command=self._load_logs,
            width=100
        ).pack(side="left")

        ctk.CTkButton(
            toolbar,
            text="Limpar",
            command=self._clear_display,
            width=100
        ).pack(side="left", padx=5)

        # Filtro
        ctk.CTkLabel(toolbar, text="Linhas:").pack(side="left", padx=(20, 5))

        self.lines_var = ctk.StringVar(value="100")
        lines_menu = ctk.CTkOptionMenu(
            toolbar,
            values=["50", "100", "200", "500"],
            variable=self.lines_var,
            command=lambda _: self._load_logs()
        )
        lines_menu.pack(side="left")

        # Área de texto
        self.log_text = ctk.CTkTextbox(self, font=("Consolas", 11))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

    def _load_logs(self):
        """Carrega logs do arquivo"""
        try:
            lines = int(self.lines_var.get())
        except ValueError:
            lines = 100

        logs = self.logger.get_recent_logs(lines)

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")

        for line in logs:
            self.log_text.insert("end", line)

        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def _clear_display(self):
        """Limpa a exibição"""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


class SettingsDialog(ctk.CTkToplevel):
    """Diálogo de configurações"""

    def __init__(self, parent, settings: Settings):
        super().__init__(parent)

        self.settings = settings
        self.logger = get_logger()

        self.title("Configurações")
        self.geometry("500x400")
        self.resizable(False, False)

        # Centraliza
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 400) // 2
        self.geometry(f"+{x}+{y}")

        # Widgets
        self._create_widgets()

        # Carrega valores
        self._load_values()

    def _create_widgets(self):
        """Cria widgets"""
        # Notebook para abas
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Aba Geral
        self._create_general_tab()

        # Aba Backup
        self._create_backup_tab()

        # Aba Conexões
        self._create_connections_tab()

        # Botões
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="Salvar",
            command=self._save,
            width=100
        ).pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=self.destroy,
            width=100,
            fg_color="gray"
        ).pack(side="right", padx=5)

    def _create_general_tab(self):
        """Cria aba geral"""
        tab = self.tabview.add("Geral")

        # Iniciar minimizado
        self.start_min_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            tab,
            text="Iniciar minimizado na bandeja",
            variable=self.start_min_var
        ).pack(anchor="w", pady=5)

        # Auto update
        self.auto_update_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            tab,
            text="Verificar atualizações automaticamente",
            variable=self.auto_update_var
        ).pack(anchor="w", pady=5)

        # Rodar como serviço
        self.service_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            tab,
            text="Executar como serviço Windows",
            variable=self.service_var
        ).pack(anchor="w", pady=5)

    def _create_backup_tab(self):
        """Cria aba de backup"""
        tab = self.tabview.add("Backup")

        # Destino 1
        ctk.CTkLabel(tab, text="Destino Primário:").pack(anchor="w", pady=(10, 2))
        self.dest1_entry = ctk.CTkEntry(tab, width=400)
        self.dest1_entry.pack(anchor="w")

        # Destino 2
        ctk.CTkLabel(tab, text="Destino Secundário:").pack(anchor="w", pady=(10, 2))
        self.dest2_entry = ctk.CTkEntry(tab, width=400)
        self.dest2_entry.pack(anchor="w")

        # Opções
        self.zip_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            tab,
            text="Compactar backup em ZIP",
            variable=self.zip_var
        ).pack(anchor="w", pady=10)

        self.verify_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            tab,
            text="Verificar integridade após backup",
            variable=self.verify_var
        ).pack(anchor="w", pady=5)

        # Prefixo
        ctk.CTkLabel(tab, text="Tipo de Nome:").pack(anchor="w", pady=(10, 2))
        self.prefix_var = ctk.StringVar()
        prefix_frame = ctk.CTkFrame(tab, fg_color="transparent")
        prefix_frame.pack(anchor="w")

        ctk.CTkRadioButton(
            prefix_frame,
            text="Versionado (data/hora)",
            variable=self.prefix_var,
            value="V"
        ).pack(side="left", padx=5)

        ctk.CTkRadioButton(
            prefix_frame,
            text="Dia da Semana",
            variable=self.prefix_var,
            value="S"
        ).pack(side="left", padx=5)

        ctk.CTkRadioButton(
            prefix_frame,
            text="Único",
            variable=self.prefix_var,
            value="U"
        ).pack(side="left", padx=5)

    def _create_connections_tab(self):
        """Cria aba de conexões"""
        tab = self.tabview.add("Conexões")

        # Firebird
        fb_frame = ctk.CTkFrame(tab)
        fb_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            fb_frame,
            text="Firebird",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        fb_inner = ctk.CTkFrame(fb_frame, fg_color="transparent")
        fb_inner.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(fb_inner, text="Banco:").pack(anchor="w")
        self.fb_db_entry = ctk.CTkEntry(fb_inner, width=350)
        self.fb_db_entry.pack(anchor="w")

        # MySQL
        mysql_frame = ctk.CTkFrame(tab)
        mysql_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            mysql_frame,
            text="MySQL",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        mysql_inner = ctk.CTkFrame(mysql_frame, fg_color="transparent")
        mysql_inner.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(mysql_inner, text="Host:").pack(anchor="w")
        self.mysql_host_entry = ctk.CTkEntry(mysql_inner, width=350)
        self.mysql_host_entry.pack(anchor="w")

    def _load_values(self):
        """Carrega valores atuais"""
        # Geral
        self.start_min_var.set(self.settings.app.start_minimized)
        self.auto_update_var.set(self.settings.app.auto_update)
        self.service_var.set(self.settings.app.run_as_service)

        # Backup
        self.dest1_entry.insert(0, self.settings.backup.local_destino1)
        self.dest2_entry.insert(0, self.settings.backup.local_destino2)
        self.zip_var.set(self.settings.backup.compactar_zip)
        self.verify_var.set(self.settings.backup.verificar_backup)
        self.prefix_var.set(self.settings.backup.prefixo_arquivo)

        # Conexões
        self.fb_db_entry.insert(0, self.settings.firebird.database_path)
        self.mysql_host_entry.insert(0, self.settings.mysql.host)

    def _save(self):
        """Salva configurações"""
        # Geral
        self.settings.app.start_minimized = self.start_min_var.get()
        self.settings.app.auto_update = self.auto_update_var.get()
        self.settings.app.run_as_service = self.service_var.get()

        # Backup
        self.settings.backup.local_destino1 = self.dest1_entry.get()
        self.settings.backup.local_destino2 = self.dest2_entry.get()
        self.settings.backup.compactar_zip = self.zip_var.get()
        self.settings.backup.verificar_backup = self.verify_var.get()
        self.settings.backup.prefixo_arquivo = self.prefix_var.get()

        # Conexões
        self.settings.firebird.database_path = self.fb_db_entry.get()
        self.settings.mysql.host = self.mysql_host_entry.get()

        # Salva
        if self.settings.save():
            show_info(self, "Sucesso", "Configurações salvas com sucesso!")
            self.destroy()
        else:
            show_error(self, "Erro", "Falha ao salvar configurações")
