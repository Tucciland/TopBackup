"""
TopBackup - Auto-Instalador
Gerencia a instalação automática do aplicativo em C:\TOPBACKUP
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple

# Diretório de instalação padrão
INSTALL_DIR = Path(r"C:\TOPBACKUP")


def get_embedded_path() -> Path:
    """Retorna o caminho dos arquivos embutidos no executável"""
    if getattr(sys, 'frozen', False):
        # Executável PyInstaller - arquivos estão em _MEIPASS
        return Path(sys._MEIPASS)
    else:
        # Desenvolvimento - arquivos estão no diretório do projeto
        return Path(__file__).parent.parent.parent


def get_install_dir() -> Path:
    """Retorna o diretório de instalação"""
    return INSTALL_DIR


def is_installed() -> bool:
    """Verifica se está rodando do diretório de instalação"""
    if not getattr(sys, 'frozen', False):
        # Em desenvolvimento, considera como "instalado"
        return True

    current_dir = Path(sys.executable).parent.resolve()
    install_dir = INSTALL_DIR.resolve()

    return current_dir == install_dir


def install() -> Tuple[bool, str]:
    """
    Instala o aplicativo em C:\TOPBACKUP

    Returns:
        Tuple[bool, str]: (precisa_reiniciar, mensagem)
    """
    if not getattr(sys, 'frozen', False):
        # Em desenvolvimento, não instala
        return False, "Modo desenvolvimento"

    if is_installed():
        # Já está no lugar certo
        return False, "Já instalado"

    try:
        # Cria diretório de instalação
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)

        # Caminho dos arquivos embutidos
        embedded = get_embedded_path()

        # 1. Copia o executável
        src_exe = Path(sys.executable)
        dst_exe = INSTALL_DIR / src_exe.name

        # Se já existe, remove para atualizar
        if dst_exe.exists():
            try:
                dst_exe.unlink()
            except PermissionError:
                # Arquivo em uso, tenta renomear
                old_exe = INSTALL_DIR / f"{src_exe.stem}_old.exe"
                if old_exe.exists():
                    old_exe.unlink()
                dst_exe.rename(old_exe)

        shutil.copy2(src_exe, dst_exe)

        # 2. Copia/extrai config
        src_config_dir = embedded / "config"
        dst_config_dir = INSTALL_DIR / "config"

        dst_config_dir.mkdir(parents=True, exist_ok=True)

        # Copia config.json.example
        src_example = src_config_dir / "config.json.example"
        dst_example = dst_config_dir / "config.json.example"

        if src_example.exists():
            shutil.copy2(src_example, dst_example)

        # Se não existe config.json, cria a partir do example
        dst_config = dst_config_dir / "config.json"
        if not dst_config.exists() and dst_example.exists():
            shutil.copy2(dst_example, dst_config)

        # 3. Copia/extrai assets
        src_assets = embedded / "assets"
        dst_assets = INSTALL_DIR / "assets"

        if src_assets.exists():
            if dst_assets.exists():
                shutil.rmtree(dst_assets)
            shutil.copytree(src_assets, dst_assets)

        # 4. Cria pasta de logs
        logs_dir = INSTALL_DIR / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # 5. Cria atalho no Desktop
        try:
            create_desktop_shortcut(dst_exe)
        except Exception:
            pass  # Não é crítico

        # 6. Inicia do local correto
        # Usa CREATE_NEW_PROCESS_GROUP para desassociar do processo atual
        subprocess.Popen(
            [str(dst_exe)],
            cwd=str(INSTALL_DIR),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )

        return True, f"Instalado em {INSTALL_DIR}"

    except PermissionError as e:
        return False, f"Sem permissão para instalar em {INSTALL_DIR}. Execute como administrador."

    except Exception as e:
        return False, f"Erro na instalação: {e}"


def create_desktop_shortcut(exe_path: Path) -> bool:
    """Cria atalho no Desktop do usuário"""
    try:
        import winreg

        # Obtém caminho do Desktop
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        desktop = Path(winreg.QueryValueEx(key, "Desktop")[0])
        winreg.CloseKey(key)

        shortcut_path = desktop / "TopBackup.lnk"

        # Se já existe, não recria
        if shortcut_path.exists():
            return True

        # Usa PowerShell para criar atalho
        ps_script = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{exe_path}"
$Shortcut.WorkingDirectory = "{exe_path.parent}"
$Shortcut.IconLocation = "{exe_path},0"
$Shortcut.Description = "TopBackup - Gerenciador de Backups"
$Shortcut.Save()
'''

        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        return result.returncode == 0

    except Exception as e:
        return False


def ensure_installed() -> Tuple[bool, str]:
    """
    Garante que o app está instalado.

    Returns:
        Tuple[bool, str]: (precisa_fechar, mensagem)
        - Se precisa_fechar=True, o app foi instalado e uma nova instância foi iniciada
        - Se precisa_fechar=False, continua normalmente
    """
    if is_installed():
        return False, "OK"

    return install()


def show_permission_error():
    """Mostra erro de permissão usando messagebox"""
    try:
        import customtkinter as ctk
        from tkinter import messagebox

        root = ctk.CTk()
        root.withdraw()

        messagebox.showerror(
            "Erro de Instalação",
            f"Não foi possível instalar em {INSTALL_DIR}.\n\n"
            "Por favor, execute o aplicativo como Administrador\n"
            "(clique direito → Executar como administrador)"
        )

        root.destroy()
    except Exception:
        print(f"ERRO: Não foi possível instalar em {INSTALL_DIR}")
        print("Execute como administrador.")
