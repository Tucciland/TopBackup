"""
TopBackup - Firebird Library Loader
Carrega automaticamente a versão correta do fbclient.dll baseado na arquitetura do Python
"""

import os
import sys
import struct
from pathlib import Path
from typing import Optional, Tuple


def get_python_architecture() -> int:
    """Retorna a arquitetura do Python (32 ou 64 bits)"""
    return struct.calcsize('P') * 8


def get_base_dir() -> Path:
    """Retorna o diretório base do aplicativo"""
    if getattr(sys, 'frozen', False):
        # Executável - sempre usa C:\TOPBACKUP (onde os assets são instalados)
        return Path(r"C:\TOPBACKUP")
    else:
        # Executando como script Python
        return Path(__file__).parent.parent.parent


def get_embedded_dir() -> Path:
    """Retorna o diretório dos arquivos embutidos no executável"""
    if getattr(sys, 'frozen', False):
        # Arquivos embutidos estão em _MEIPASS
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).parent.parent.parent


def find_fbclient_dll() -> Optional[str]:
    """
    Procura o fbclient.dll na seguinte ordem:
    1. Arquivos embutidos no executável (_MEIPASS)
    2. Pasta de instalação (C:\TOPBACKUP\assets)
    3. Variável de ambiente FIREBIRD
    4. Instalação padrão do Firebird
    5. PATH do sistema

    Returns:
        Caminho para o fbclient.dll ou None se não encontrado
    """
    arch = get_python_architecture()
    arch_folder = "x64" if arch == 64 else "x86"

    # Lista de locais para procurar
    search_paths = []

    # 1. Arquivos embutidos no executável (para primeira execução antes de instalar)
    if getattr(sys, 'frozen', False):
        embedded_dir = get_embedded_dir()
        embedded_path = embedded_dir / "assets" / "firebird" / arch_folder / "fbclient.dll"
        search_paths.append(embedded_path)

    # 2. Pasta de instalação (C:\TOPBACKUP ou diretório de desenvolvimento)
    base_dir = get_base_dir()
    installed_path = base_dir / "assets" / "firebird" / arch_folder / "fbclient.dll"
    search_paths.append(installed_path)

    # 2. Variável de ambiente FIREBIRD
    firebird_env = os.environ.get('FIREBIRD')
    if firebird_env:
        search_paths.append(Path(firebird_env) / "bin" / "fbclient.dll")
        search_paths.append(Path(firebird_env) / "fbclient.dll")

    # 3. Instalações padrão do Firebird (Windows)
    program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
    program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')

    if arch == 64:
        # Python 64-bit: procura Firebird 64-bit primeiro
        firebird_locations = [
            Path(program_files) / "Firebird" / "Firebird_2_5" / "bin" / "fbclient.dll",
            Path(program_files) / "Firebird" / "Firebird_2_5" / "WOW64" / "fbclient.dll",
            Path(program_files) / "Firebird" / "Firebird_3_0" / "fbclient.dll",
        ]
    else:
        # Python 32-bit: procura Firebird 32-bit
        firebird_locations = [
            Path(program_files_x86) / "Firebird" / "Firebird_2_5" / "bin" / "fbclient.dll",
            Path(program_files) / "Firebird" / "Firebird_2_5" / "bin" / "fbclient.dll",
        ]

    search_paths.extend(firebird_locations)

    # 4. Diretório do sistema Windows
    system_root = os.environ.get('SystemRoot', 'C:\\Windows')
    if arch == 64:
        search_paths.append(Path(system_root) / "System32" / "fbclient.dll")
    else:
        search_paths.append(Path(system_root) / "SysWOW64" / "fbclient.dll")

    # Procura em todos os caminhos
    for path in search_paths:
        if path.exists():
            return str(path)

    return None


def initialize_firebird() -> Tuple[bool, str]:
    """
    Inicializa a biblioteca Firebird carregando o fbclient.dll correto.

    Esta função DEVE ser chamada ANTES de qualquer import do fdb.

    Returns:
        Tuple[bool, str]: (sucesso, mensagem)
    """
    arch = get_python_architecture()

    # Procura o fbclient.dll
    dll_path = find_fbclient_dll()

    if not dll_path:
        return False, (
            f"fbclient.dll ({arch}-bit) não encontrado. "
            f"Copie o arquivo para: assets/firebird/{'x64' if arch == 64 else 'x86'}/fbclient.dll"
        )

    try:
        # Define a variável de ambiente para o fdb encontrar a DLL
        os.environ['FIREBIRD'] = str(Path(dll_path).parent)

        # Adiciona o diretório da DLL ao PATH
        dll_dir = str(Path(dll_path).parent)
        current_path = os.environ.get('PATH', '')
        if dll_dir not in current_path:
            os.environ['PATH'] = dll_dir + os.pathsep + current_path

        # Tenta carregar a DLL via fdb
        import fdb
        fdb.load_api(dll_path)

        return True, f"Firebird inicializado: {dll_path}"

    except Exception as e:
        return False, f"Erro ao carregar fbclient.dll: {e}"


def get_embedded_dll_path() -> Path:
    """Retorna o caminho onde a DLL embutida deveria estar"""
    arch = get_python_architecture()
    arch_folder = "x64" if arch == 64 else "x86"
    # Usa diretório de instalação (C:\TOPBACKUP)
    base_dir = get_base_dir()
    return base_dir / "assets" / "firebird" / arch_folder / "fbclient.dll"


def is_firebird_available() -> bool:
    """Verifica se o Firebird está disponível"""
    return find_fbclient_dll() is not None
