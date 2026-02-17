"""
TopBackup - Setup Wizard
Assistente de configuração inicial
"""

import customtkinter as ctk
from tkinter import filedialog
from typing import Optional, Tuple
import os

from ..config.settings import Settings
from ..database.firebird_client import FirebirdClient
from ..database.mysql_client import MySQLClient
from ..utils.file_utils import FileUtils
from ..version import APP_NAME, VERSION


class SetupWizard(ctk.CTkToplevel):
    """Assistente de configuração inicial"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.title(f"{APP_NAME} - Configuração Inicial")
        self.geometry("650x620")
        self.resizable(False, False)

        # Centraliza na tela
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 650) // 2
        y = (self.winfo_screenheight() - 620) // 2
        self.geometry(f"+{x}+{y}")

        # Resultado
        self.settings: Optional[Settings] = None
        self.completed = False

        # Etapa atual
        self._step = 0

        # Cria frames de etapas
        self._create_widgets()

        # Mostra primeira etapa
        self._show_step(0)

        # Modal
        self.grab_set()

    def _create_widgets(self):
        """Cria widgets do wizard"""
        # Header
        header = ctk.CTkFrame(self, height=60, fg_color="#1f538d")
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text=f"{APP_NAME} - Configuração",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        ).pack(pady=15)

        # Container para etapas
        self.steps_container = ctk.CTkFrame(self)
        self.steps_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Cria frames de cada etapa
        self._create_step1()  # Firebird
        self._create_step2()  # MySQL
        self._create_step3()  # FTP (opcional)
        self._create_step4()  # Resumo

        # Botões de navegação
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=20, pady=10)

        self.back_btn = ctk.CTkButton(
            nav_frame,
            text="Voltar",
            command=self._prev_step,
            width=100
        )
        self.back_btn.pack(side="left")

        self.next_btn = ctk.CTkButton(
            nav_frame,
            text="Próximo",
            command=self._next_step,
            width=100
        )
        self.next_btn.pack(side="right")

    def _create_step1(self):
        """Etapa 1: Configuração Firebird"""
        self.step1_frame = ctk.CTkFrame(self.steps_container)

        ctk.CTkLabel(
            self.step1_frame,
            text="Configuração do Banco Firebird",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        ctk.CTkLabel(
            self.step1_frame,
            text="Informe o caminho do banco de dados e do gbak.exe"
        ).pack(pady=5)

        # Caminho do banco
        db_frame = ctk.CTkFrame(self.step1_frame, fg_color="transparent")
        db_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(db_frame, text="Banco de Dados (.fdb):").pack(anchor="w")

        db_input_frame = ctk.CTkFrame(db_frame, fg_color="transparent")
        db_input_frame.pack(fill="x")

        self.db_path_entry = ctk.CTkEntry(db_input_frame, width=400)
        self.db_path_entry.pack(side="left", padx=(0, 5))

        # Caminho padrão TopSoft
        default_db_path = r"C:\TOPSOFT\Dados\dados.fdb"
        if os.path.exists(default_db_path):
            self.db_path_entry.insert(0, default_db_path)

        ctk.CTkButton(
            db_input_frame,
            text="...",
            width=40,
            command=self._browse_database
        ).pack(side="left")

        # Pasta do Firebird
        fb_folder_frame = ctk.CTkFrame(self.step1_frame, fg_color="transparent")
        fb_folder_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(fb_folder_frame, text="Pasta do Firebird:").pack(anchor="w")

        fb_folder_input = ctk.CTkFrame(fb_folder_frame, fg_color="transparent")
        fb_folder_input.pack(fill="x")

        self.fb_folder_entry = ctk.CTkEntry(fb_folder_input, width=400)
        self.fb_folder_entry.pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            fb_folder_input,
            text="...",
            width=40,
            command=self._browse_firebird_folder
        ).pack(side="left")

        # Caminho padrão do Firebird
        default_fb_folder = r"C:\Program Files (x86)\Firebird\Firebird_2_5"
        if os.path.exists(default_fb_folder):
            self.fb_folder_entry.insert(0, default_fb_folder)
        else:
            # Tenta encontrar automaticamente
            auto_path = FileUtils.find_gbak_executable()
            if auto_path:
                # Extrai pasta do Firebird (2 níveis acima do gbak.exe)
                fb_folder = os.path.dirname(os.path.dirname(auto_path))
                self.fb_folder_entry.insert(0, fb_folder)

        # Label mostrando onde fica o gbak
        self.gbak_path_label = ctk.CTkLabel(
            fb_folder_frame,
            text="",
            text_color="gray"
        )
        self.gbak_path_label.pack(anchor="w", pady=(5, 0))
        self._update_gbak_path_label()

        # Credenciais
        cred_frame = ctk.CTkFrame(self.step1_frame, fg_color="transparent")
        cred_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(cred_frame, text="Usuário:").pack(anchor="w")
        self.fb_user_entry = ctk.CTkEntry(cred_frame, width=200)
        self.fb_user_entry.insert(0, "SYSDBA")
        self.fb_user_entry.pack(anchor="w", pady=2)

        ctk.CTkLabel(cred_frame, text="Senha:").pack(anchor="w")
        self.fb_pass_entry = ctk.CTkEntry(cred_frame, width=200, show="*")
        self.fb_pass_entry.insert(0, "masterkey")
        self.fb_pass_entry.pack(anchor="w", pady=2)

        # Botão de teste
        self.test_fb_btn = ctk.CTkButton(
            self.step1_frame,
            text="Testar Conexão",
            command=self._test_firebird
        )
        self.test_fb_btn.pack(pady=10)

        self.fb_status_label = ctk.CTkLabel(
            self.step1_frame,
            text="",
            text_color="gray"
        )
        self.fb_status_label.pack()

    def _create_step2(self):
        """Etapa 2: Configuração MySQL"""
        self.step2_frame = ctk.CTkFrame(self.steps_container)

        ctk.CTkLabel(
            self.step2_frame,
            text="Configuração do MySQL (Nuvem)",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        ctk.CTkLabel(
            self.step2_frame,
            text="Informe os dados de conexão com o banco MySQL"
        ).pack(pady=5)

        # Host e Porta
        host_frame = ctk.CTkFrame(self.step2_frame, fg_color="transparent")
        host_frame.pack(fill="x", pady=10)

        h1 = ctk.CTkFrame(host_frame, fg_color="transparent")
        h1.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(h1, text="Host:").pack(anchor="w")
        self.mysql_host_entry = ctk.CTkEntry(h1, width=250)
        self.mysql_host_entry.insert(0, "dashboard.topsoft.cloud")  # Padrão TopSoft
        self.mysql_host_entry.pack(anchor="w")

        h2 = ctk.CTkFrame(host_frame, fg_color="transparent")
        h2.pack(side="left", padx=10)
        ctk.CTkLabel(h2, text="Porta:").pack(anchor="w")
        self.mysql_port_entry = ctk.CTkEntry(h2, width=80)
        self.mysql_port_entry.insert(0, "3306")
        self.mysql_port_entry.pack(anchor="w")

        # Database
        db_frame = ctk.CTkFrame(self.step2_frame, fg_color="transparent")
        db_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(db_frame, text="Database:").pack(anchor="w")
        self.mysql_db_entry = ctk.CTkEntry(db_frame, width=300)
        self.mysql_db_entry.insert(0, "PROJETO_BACKUPS")
        self.mysql_db_entry.pack(anchor="w")

        # Credenciais
        cred_frame = ctk.CTkFrame(self.step2_frame, fg_color="transparent")
        cred_frame.pack(fill="x", pady=10)

        c1 = ctk.CTkFrame(cred_frame, fg_color="transparent")
        c1.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(c1, text="Usuário:").pack(anchor="w")
        self.mysql_user_entry = ctk.CTkEntry(c1, width=200)
        self.mysql_user_entry.insert(0, "user_sinc")  # Padrão TopSoft
        self.mysql_user_entry.pack(anchor="w")

        c2 = ctk.CTkFrame(cred_frame, fg_color="transparent")
        c2.pack(side="left", padx=10)
        ctk.CTkLabel(c2, text="Senha:").pack(anchor="w")
        self.mysql_pass_entry = ctk.CTkEntry(c2, width=200, show="*")
        self.mysql_pass_entry.insert(0, "51Ncr0n1z4d0r@2025@!@#")  # Padrão TopSoft
        self.mysql_pass_entry.pack(anchor="w")

        # Botão de teste
        self.test_mysql_btn = ctk.CTkButton(
            self.step2_frame,
            text="Testar Conexão",
            command=self._test_mysql
        )
        self.test_mysql_btn.pack(pady=10)

        self.mysql_status_label = ctk.CTkLabel(
            self.step2_frame,
            text="",
            text_color="gray"
        )
        self.mysql_status_label.pack()

    def _create_step3(self):
        """Etapa 3: Configuração FTP (opcional)"""
        self.step3_frame = ctk.CTkFrame(self.steps_container)

        ctk.CTkLabel(
            self.step3_frame,
            text="Configuração FTP (Opcional)",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        ctk.CTkLabel(
            self.step3_frame,
            text="Configure o servidor FTP para envio de backups remotos"
        ).pack(pady=5)

        # Checkbox habilitar
        self.ftp_enabled_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self.step3_frame,
            text="Habilitar backup remoto via FTP",
            variable=self.ftp_enabled_var,
            command=self._toggle_ftp_fields
        ).pack(pady=10)

        # Campos FTP
        self.ftp_fields_frame = ctk.CTkFrame(self.step3_frame, fg_color="transparent")
        self.ftp_fields_frame.pack(fill="x", pady=10)

        # Host e Porta
        h_frame = ctk.CTkFrame(self.ftp_fields_frame, fg_color="transparent")
        h_frame.pack(fill="x", pady=5)

        h1 = ctk.CTkFrame(h_frame, fg_color="transparent")
        h1.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(h1, text="Host:").pack(anchor="w")
        self.ftp_host_entry = ctk.CTkEntry(h1, width=250, state="disabled")
        self.ftp_host_entry.pack(anchor="w")

        h2 = ctk.CTkFrame(h_frame, fg_color="transparent")
        h2.pack(side="left", padx=10)
        ctk.CTkLabel(h2, text="Porta:").pack(anchor="w")
        self.ftp_port_entry = ctk.CTkEntry(h2, width=80, state="disabled")
        self.ftp_port_entry.insert(0, "21")
        self.ftp_port_entry.pack(anchor="w")

        # Credenciais
        c_frame = ctk.CTkFrame(self.ftp_fields_frame, fg_color="transparent")
        c_frame.pack(fill="x", pady=5)

        c1 = ctk.CTkFrame(c_frame, fg_color="transparent")
        c1.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(c1, text="Usuário:").pack(anchor="w")
        self.ftp_user_entry = ctk.CTkEntry(c1, width=200, state="disabled")
        self.ftp_user_entry.pack(anchor="w")

        c2 = ctk.CTkFrame(c_frame, fg_color="transparent")
        c2.pack(side="left", padx=10)
        ctk.CTkLabel(c2, text="Senha:").pack(anchor="w")
        self.ftp_pass_entry = ctk.CTkEntry(c2, width=200, show="*", state="disabled")
        self.ftp_pass_entry.pack(anchor="w")

        # Diretório remoto
        p_frame = ctk.CTkFrame(self.ftp_fields_frame, fg_color="transparent")
        p_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(p_frame, text="Diretório Remoto:").pack(anchor="w")
        self.ftp_path_entry = ctk.CTkEntry(p_frame, width=300, state="disabled")
        self.ftp_path_entry.insert(0, "/backups")
        self.ftp_path_entry.pack(anchor="w")

    def _create_step4(self):
        """Etapa 4: Resumo"""
        self.step4_frame = ctk.CTkFrame(self.steps_container)

        ctk.CTkLabel(
            self.step4_frame,
            text="Resumo da Configuração",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        self.summary_text = ctk.CTkTextbox(self.step4_frame, height=250)
        self.summary_text.pack(fill="both", expand=True, pady=10)
        self.summary_text.configure(state="disabled")

        # Opção de instalar como serviço
        self.service_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self.step4_frame,
            text="Instalar como Serviço Windows",
            variable=self.service_var
        ).pack(pady=10)

    # ============ NAVEGAÇÃO ============

    def _show_step(self, step: int):
        """Mostra etapa específica"""
        frames = [self.step1_frame, self.step2_frame, self.step3_frame, self.step4_frame]

        for f in frames:
            f.pack_forget()

        frames[step].pack(fill="both", expand=True)

        # Atualiza botões
        self.back_btn.configure(state="normal" if step > 0 else "disabled")

        if step == len(frames) - 1:
            self.next_btn.configure(text="Concluir")
        else:
            self.next_btn.configure(text="Próximo")

        # Atualiza resumo na última etapa
        if step == 3:
            self._update_summary()

    def _next_step(self):
        """Avança para próxima etapa"""
        if self._step == 0:
            # Valida Firebird
            if not self._validate_firebird():
                return
        elif self._step == 1:
            # Valida MySQL
            if not self._validate_mysql():
                return
        elif self._step == 3:
            # Finaliza
            self._finish()
            return

        self._step += 1
        self._show_step(self._step)

    def _prev_step(self):
        """Volta para etapa anterior"""
        if self._step > 0:
            self._step -= 1
            self._show_step(self._step)

    # ============ VALIDAÇÃO ============

    def _validate_firebird(self) -> bool:
        """Valida configuração Firebird"""
        db_path = self.db_path_entry.get()
        gbak_path = self._get_gbak_path()

        if not db_path:
            self.fb_status_label.configure(text="Informe o caminho do banco", text_color="red")
            return False

        if not os.path.exists(db_path):
            self.fb_status_label.configure(text="Banco não encontrado", text_color="red")
            return False

        if not gbak_path or not os.path.exists(gbak_path):
            self.fb_status_label.configure(text="gbak.exe não encontrado na pasta do Firebird", text_color="red")
            return False

        return True

    def _validate_mysql(self) -> bool:
        """Valida configuração MySQL"""
        host = self.mysql_host_entry.get()
        user = self.mysql_user_entry.get()

        if not host:
            self.mysql_status_label.configure(text="Informe o host", text_color="red")
            return False

        if not user:
            self.mysql_status_label.configure(text="Informe o usuário", text_color="red")
            return False

        return True

    def _test_firebird(self):
        """Testa conexão Firebird"""
        from ..config.settings import FirebirdConfig

        config = FirebirdConfig(
            database_path=self.db_path_entry.get(),
            gbak_path=self._get_gbak_path(),
            user=self.fb_user_entry.get(),
            password=self.fb_pass_entry.get()
        )

        client = FirebirdClient(config)
        success, msg = client.test_connection()

        if success:
            self.fb_status_label.configure(text="Conexão OK!", text_color="green")
        else:
            self.fb_status_label.configure(text=f"Erro: {msg}", text_color="red")

    def _test_mysql(self):
        """Testa conexão MySQL"""
        from ..config.settings import MySQLConfig

        try:
            port = int(self.mysql_port_entry.get())
        except ValueError:
            port = 3306

        config = MySQLConfig(
            host=self.mysql_host_entry.get(),
            port=port,
            database=self.mysql_db_entry.get(),
            user=self.mysql_user_entry.get(),
            password=self.mysql_pass_entry.get()
        )

        client = MySQLClient(config)
        success, msg = client.test_connection()

        if success:
            self.mysql_status_label.configure(text="Conexão OK!", text_color="green")
        else:
            self.mysql_status_label.configure(text=f"Erro: {msg}", text_color="red")

    # ============ HELPERS ============

    def _browse_database(self):
        """Abre diálogo para selecionar banco"""
        path = filedialog.askopenfilename(
            title="Selecione o banco de dados",
            filetypes=[("Firebird Database", "*.fdb *.gdb"), ("Todos", "*.*")]
        )
        if path:
            self.db_path_entry.delete(0, "end")
            self.db_path_entry.insert(0, path)

    def _browse_firebird_folder(self):
        """Abre diálogo para selecionar pasta do Firebird"""
        path = filedialog.askdirectory(
            title="Selecione a pasta do Firebird"
        )
        if path:
            self.fb_folder_entry.delete(0, "end")
            self.fb_folder_entry.insert(0, path)
            self._update_gbak_path_label()

    def _update_gbak_path_label(self):
        """Atualiza label mostrando caminho do gbak"""
        fb_folder = self.fb_folder_entry.get()
        if fb_folder:
            gbak_path = os.path.join(fb_folder, "bin", "gbak.exe")
            if os.path.exists(gbak_path):
                self.gbak_path_label.configure(
                    text=f"gbak.exe: {gbak_path}",
                    text_color="green"
                )
            else:
                self.gbak_path_label.configure(
                    text=f"gbak.exe não encontrado em: {gbak_path}",
                    text_color="orange"
                )
        else:
            self.gbak_path_label.configure(text="", text_color="gray")

    def _get_gbak_path(self) -> str:
        """Retorna caminho do gbak.exe baseado na pasta do Firebird"""
        fb_folder = self.fb_folder_entry.get()
        return os.path.join(fb_folder, "bin", "gbak.exe")

    def _toggle_ftp_fields(self):
        """Habilita/desabilita campos FTP"""
        state = "normal" if self.ftp_enabled_var.get() else "disabled"

        self.ftp_host_entry.configure(state=state)
        self.ftp_port_entry.configure(state=state)
        self.ftp_user_entry.configure(state=state)
        self.ftp_pass_entry.configure(state=state)
        self.ftp_path_entry.configure(state=state)

    def _update_summary(self):
        """Atualiza texto do resumo"""
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")

        summary = f"""
FIREBIRD
--------
Banco: {self.db_path_entry.get()}
Pasta Firebird: {self.fb_folder_entry.get()}
Gbak: {self._get_gbak_path()}
Usuário: {self.fb_user_entry.get()}

MYSQL
-----
Host: {self.mysql_host_entry.get()}:{self.mysql_port_entry.get()}
Database: {self.mysql_db_entry.get()}
Usuário: {self.mysql_user_entry.get()}
"""

        if self.ftp_enabled_var.get():
            summary += f"""
FTP
---
Host: {self.ftp_host_entry.get()}:{self.ftp_port_entry.get()}
Diretório: {self.ftp_path_entry.get()}
"""

        self.summary_text.insert("1.0", summary)
        self.summary_text.configure(state="disabled")

    def _finish(self):
        """Finaliza o wizard e salva configurações"""
        from ..config.settings import FirebirdConfig, MySQLConfig, FTPConfig

        self.settings = Settings()

        # Firebird
        self.settings.firebird = FirebirdConfig(
            database_path=self.db_path_entry.get(),
            gbak_path=self._get_gbak_path(),
            user=self.fb_user_entry.get(),
            password=self.fb_pass_entry.get()
        )

        # MySQL
        try:
            port = int(self.mysql_port_entry.get())
        except ValueError:
            port = 3306

        self.settings.mysql = MySQLConfig(
            host=self.mysql_host_entry.get(),
            port=port,
            database=self.mysql_db_entry.get(),
            user=self.mysql_user_entry.get(),
            password=self.mysql_pass_entry.get()
        )

        # FTP
        if self.ftp_enabled_var.get():
            try:
                ftp_port = int(self.ftp_port_entry.get())
            except ValueError:
                ftp_port = 21

            self.settings.ftp = FTPConfig(
                host=self.ftp_host_entry.get(),
                port=ftp_port,
                user=self.ftp_user_entry.get(),
                password=self.ftp_pass_entry.get(),
                remote_path=self.ftp_path_entry.get()
            )

            self.settings.backup.backup_remoto = True

        # App
        self.settings.app.first_run = False
        self.settings.app.run_as_service = self.service_var.get()

        # Salva
        self.settings.save()

        self.completed = True
        self.destroy()
