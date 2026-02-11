"""
TopBackup - Utilitários de Arquivo
"""

import os
import shutil
import zipfile
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple


class FileUtils:
    """Utilitários para operações de arquivo"""

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Formata tamanho em bytes para formato legível"""
        if size_bytes == 0:
            return "0 B"

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.2f} {units[unit_index]}"

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Retorna o tamanho do arquivo em bytes"""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0

    @staticmethod
    def compress_to_zip(source_path: str, zip_path: str) -> Tuple[bool, str]:
        """
        Compacta um arquivo para ZIP

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Adiciona o arquivo com apenas o nome, sem o caminho completo
                arcname = os.path.basename(source_path)
                zipf.write(source_path, arcname)

            return True, "Compactação concluída"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def safe_move(source: str, destination: str, overwrite: bool = True) -> Tuple[bool, str]:
        """
        Move arquivo de forma segura

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Cria diretório de destino se não existir
            dest_dir = os.path.dirname(destination)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)

            # Remove arquivo existente se overwrite=True
            if os.path.exists(destination):
                if overwrite:
                    os.remove(destination)
                else:
                    return False, "Arquivo de destino já existe"

            shutil.move(source, destination)
            return True, "Arquivo movido com sucesso"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def safe_copy(source: str, destination: str, overwrite: bool = True) -> Tuple[bool, str]:
        """
        Copia arquivo de forma segura

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Cria diretório de destino se não existir
            dest_dir = os.path.dirname(destination)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)

            # Remove arquivo existente se overwrite=True
            if os.path.exists(destination):
                if overwrite:
                    os.remove(destination)
                else:
                    return False, "Arquivo de destino já existe"

            shutil.copy2(source, destination)
            return True, "Arquivo copiado com sucesso"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def safe_delete(file_path: str) -> Tuple[bool, str]:
        """
        Remove arquivo de forma segura

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return True, "Arquivo removido"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def calculate_sha256(file_path: str) -> Optional[str]:
        """Calcula hash SHA256 do arquivo"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception:
            return None

    @staticmethod
    def generate_backup_filename(
        cnpj: str,
        prefixo: str = 'V',
        extensao: str = '.zip'
    ) -> str:
        """
        Gera nome do arquivo de backup baseado no prefixo

        Args:
            cnpj: CNPJ da empresa (apenas números)
            prefixo: V (versionado), S (semanal), U (único)
            extensao: Extensão do arquivo

        Returns:
            Nome do arquivo formatado
        """
        # Remove caracteres especiais do CNPJ
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))

        if prefixo == 'V':
            # Versionado: CNPJ_YYYYMMDD_HHMMSS.zip
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f"{cnpj_limpo}_{timestamp}{extensao}"

        elif prefixo == 'S':
            # Semanal: CNPJ_SEG.zip
            dias = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'DOM']
            dia_semana = dias[datetime.now().weekday()]
            return f"{cnpj_limpo}_{dia_semana}{extensao}"

        else:  # prefixo == 'U'
            # Único: CNPJ.zip
            return f"{cnpj_limpo}{extensao}"

    @staticmethod
    def ensure_directory(directory: str) -> bool:
        """Garante que o diretório existe"""
        try:
            os.makedirs(directory, exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def get_temp_directory() -> Path:
        """Retorna diretório temporário para backups"""
        import sys
        # Usa C:\TOPBACKUP\temp quando executável (evita problemas com temp do PyInstaller)
        # Em desenvolvimento usa o temp do sistema
        if getattr(sys, 'frozen', False):
            return Path(r"C:\TOPBACKUP\temp")
        else:
            import tempfile
            return Path(tempfile.gettempdir()) / "topbackup_temp"

    @staticmethod
    def cleanup_temp_files(max_age_hours: int = 24):
        """Remove arquivos temporários antigos"""
        temp_dir = FileUtils.get_temp_directory()
        if not temp_dir.exists():
            return

        now = datetime.now().timestamp()
        max_age_seconds = max_age_hours * 3600

        for file_path in temp_dir.iterdir():
            try:
                file_age = now - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
            except Exception:
                continue

    @staticmethod
    def find_gbak_executable() -> Optional[str]:
        """Tenta encontrar o executável gbak.exe automaticamente"""
        from ..config.constants import FIREBIRD_PATHS

        for path in FIREBIRD_PATHS:
            if os.path.isfile(path):
                return path

        # Tenta encontrar em Program Files
        program_files = [
            os.environ.get('PROGRAMFILES', r'C:\Program Files'),
            os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)'),
        ]

        for pf in program_files:
            if pf:
                firebird_dir = Path(pf) / "Firebird"
                if firebird_dir.exists():
                    for gbak in firebird_dir.rglob("gbak.exe"):
                        return str(gbak)

        return None
