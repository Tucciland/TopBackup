"""
TopBackup - Diálogos Auxiliares
Diálogos de mensagem, progresso e configurações
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
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


class AgendaListDialog(ctk.CTkToplevel):
    """Diálogo para visualização das agendas de backup"""

    def __init__(self, parent, agendas: list):
        super().__init__(parent)

        self.agendas = agendas

        self.title("Agendamentos de Backup")
        self.geometry("750x450")

        # Centraliza
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 750) // 2
        y = (self.winfo_screenheight() - 450) // 2
        self.geometry(f"+{x}+{y}")

        self._create_widgets()

    def _create_widgets(self):
        """Cria widgets"""
        # Frame principal
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # Título
        ctk.CTkLabel(
            main,
            text=f"Total de agendamentos: {len(self.agendas)}",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        # Frame scrollável para a lista
        scroll_frame = ctk.CTkScrollableFrame(main, height=350)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Cabeçalho
        header = ctk.CTkFrame(scroll_frame, fg_color="gray25")
        header.pack(fill="x", pady=(0, 5))

        headers = ["Horário", "Dias", "Destino 1", "Tipo"]
        widths = [80, 180, 350, 60]
        for i, (text, width) in enumerate(zip(headers, widths)):
            ctk.CTkLabel(
                header,
                text=text,
                width=width,
                font=ctk.CTkFont(weight="bold")
            ).pack(side="left", padx=2)

        # Linhas de dados
        for agenda in self.agendas:
            self._create_agenda_row(scroll_frame, agenda)

        # Botão fechar
        ctk.CTkButton(
            main,
            text="Fechar",
            command=self.destroy,
            width=100
        ).pack(pady=10)

    def _create_agenda_row(self, parent, agenda):
        """Cria uma linha para cada agenda"""
        row = ctk.CTkFrame(parent, fg_color="gray20", corner_radius=5)
        row.pack(fill="x", pady=2)

        # Horário
        hora, minuto = agenda.get_hora_minuto()
        horario_str = f"{hora:02d}:{minuto:02d}"
        ctk.CTkLabel(row, text=horario_str, width=80).pack(side="left", padx=2)

        # Dias da semana
        dias = []
        if agenda.dom == 'S': dias.append("Dom")
        if agenda.seg == 'S': dias.append("Seg")
        if agenda.ter == 'S': dias.append("Ter")
        if agenda.qua == 'S': dias.append("Qua")
        if agenda.qui == 'S': dias.append("Qui")
        if agenda.sex == 'S': dias.append("Sex")
        if agenda.sab == 'S': dias.append("Sab")
        dias_str = ", ".join(dias) if dias else "Nenhum"
        ctk.CTkLabel(row, text=dias_str, width=180).pack(side="left", padx=2)

        # Destino 1
        destino = agenda.local_destino1 or "-"
        if len(destino) > 45:
            destino = "..." + destino[-42:]
        ctk.CTkLabel(row, text=destino, width=350, anchor="w").pack(side="left", padx=2)

        # Tipo de backup
        tipos = {'V': 'Data/Hora', 'S': 'Semanal', 'U': 'Único'}
        tipo_str = tipos.get(agenda.prefixo_backup, agenda.prefixo_backup)
        ctk.CTkLabel(row, text=tipo_str, width=60).pack(side="left", padx=2)


class SettingsDialog(ctk.CTkToplevel):
    """Diálogo de configurações"""

    def __init__(self, parent, settings: Settings, on_save_callback: Callable = None):
        super().__init__(parent)

        self.settings = settings
        self.logger = get_logger()
        self.on_save_callback = on_save_callback

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
        dest1_frame = ctk.CTkFrame(tab, fg_color="transparent")
        dest1_frame.pack(anchor="w", fill="x")
        self.dest1_entry = ctk.CTkEntry(dest1_frame, width=350)
        self.dest1_entry.pack(side="left")
        ctk.CTkButton(
            dest1_frame,
            text="...",
            width=40,
            command=lambda: self._browse_folder(self.dest1_entry)
        ).pack(side="left", padx=5)

        # Destino 2
        ctk.CTkLabel(tab, text="Destino Secundário:").pack(anchor="w", pady=(10, 2))
        dest2_frame = ctk.CTkFrame(tab, fg_color="transparent")
        dest2_frame.pack(anchor="w", fill="x")
        self.dest2_entry = ctk.CTkEntry(dest2_frame, width=350)
        self.dest2_entry.pack(side="left")
        ctk.CTkButton(
            dest2_frame,
            text="...",
            width=40,
            command=lambda: self._browse_folder(self.dest2_entry)
        ).pack(side="left", padx=5)

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

        # Pasta do Firebird
        ctk.CTkLabel(fb_inner, text="Pasta do Firebird:").pack(anchor="w")
        fb_folder_frame = ctk.CTkFrame(fb_inner, fg_color="transparent")
        fb_folder_frame.pack(anchor="w", fill="x")
        self.fb_folder_entry = ctk.CTkEntry(fb_folder_frame, width=300)
        self.fb_folder_entry.pack(side="left")
        ctk.CTkButton(
            fb_folder_frame,
            text="...",
            width=40,
            command=self._browse_firebird_folder
        ).pack(side="left", padx=5)

        # Label mostrando onde fica o gbak
        self.gbak_status_label = ctk.CTkLabel(fb_inner, text="", text_color="gray")
        self.gbak_status_label.pack(anchor="w")

        # Banco de dados
        ctk.CTkLabel(fb_inner, text="Banco de Dados:").pack(anchor="w", pady=(5, 0))
        fb_db_frame = ctk.CTkFrame(fb_inner, fg_color="transparent")
        fb_db_frame.pack(anchor="w", fill="x")
        self.fb_db_entry = ctk.CTkEntry(fb_db_frame, width=300)
        self.fb_db_entry.pack(side="left")
        ctk.CTkButton(
            fb_db_frame,
            text="...",
            width=40,
            command=self._browse_database
        ).pack(side="left", padx=5)

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

    def _browse_firebird_folder(self):
        """Abre diálogo para selecionar pasta do Firebird"""
        import os
        folder = filedialog.askdirectory(
            title="Selecione a pasta do Firebird"
        )
        if folder:
            self.fb_folder_entry.delete(0, "end")
            self.fb_folder_entry.insert(0, folder)
            self._update_gbak_status()

    def _browse_database(self):
        """Abre diálogo para selecionar banco de dados"""
        path = filedialog.askopenfilename(
            title="Selecione o banco de dados",
            filetypes=[("Firebird Database", "*.fdb *.gdb"), ("Todos", "*.*")]
        )
        if path:
            self.fb_db_entry.delete(0, "end")
            self.fb_db_entry.insert(0, path)

    def _update_gbak_status(self):
        """Atualiza status do gbak baseado na pasta do Firebird"""
        import os
        fb_folder = self.fb_folder_entry.get()
        if fb_folder:
            gbak_path = os.path.join(fb_folder, "bin", "gbak.exe")
            if os.path.exists(gbak_path):
                self.gbak_status_label.configure(
                    text=f"gbak.exe encontrado",
                    text_color="green"
                )
            else:
                self.gbak_status_label.configure(
                    text=f"gbak.exe não encontrado em bin/",
                    text_color="orange"
                )
        else:
            self.gbak_status_label.configure(text="", text_color="gray")

    def _get_gbak_path(self) -> str:
        """Retorna caminho do gbak.exe baseado na pasta do Firebird"""
        import os
        fb_folder = self.fb_folder_entry.get()
        return os.path.join(fb_folder, "bin", "gbak.exe")

    def _browse_folder(self, entry_widget):
        """Abre diálogo para selecionar pasta"""
        folder = filedialog.askdirectory(
            title="Selecionar Pasta de Destino",
            initialdir=entry_widget.get() or "/"
        )
        if folder:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, folder)

    def _load_values(self):
        """Carrega valores atuais"""
        import os

        # Geral
        self.start_min_var.set(self.settings.app.start_minimized)
        self.auto_update_var.set(self.settings.app.auto_update)
        self.service_var.set(self.settings.app.run_as_service)

        # Backup
        self.dest1_entry.insert(0, self.settings.backup.local_destino1)
        self.dest2_entry.insert(0, self.settings.backup.local_destino2)
        self.zip_var.set(self.settings.backup.compactar_zip)
        self.verify_var.set(self.settings.backup.verificar_backup)
        self.prefix_var.set(self.settings.backup.prefixo_backup)

        # Conexões - Extrai pasta do Firebird do gbak_path (2 níveis acima)
        gbak_path = self.settings.firebird.gbak_path
        if gbak_path:
            fb_folder = os.path.dirname(os.path.dirname(gbak_path))
            self.fb_folder_entry.insert(0, fb_folder)
            self._update_gbak_status()

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
        self.settings.backup.prefixo_backup = self.prefix_var.get()

        # Conexões - Salva gbak_path baseado na pasta do Firebird
        self.settings.firebird.gbak_path = self._get_gbak_path()
        self.settings.firebird.database_path = self.fb_db_entry.get()
        self.settings.mysql.host = self.mysql_host_entry.get()

        # Salva
        if self.settings.save():
            show_info(self, "Sucesso", "Configurações salvas com sucesso!")
            # Notifica a janela principal para atualizar
            if self.on_save_callback:
                self.on_save_callback()
            self.destroy()
        else:
            show_error(self, "Erro", "Falha ao salvar configurações")
