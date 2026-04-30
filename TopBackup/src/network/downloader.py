"""
TopBackup - Downloader de Arquivos
Download de atualizações e outros recursos
"""

import os
import tempfile
import hashlib
from pathlib import Path
from typing import Optional, Callable, Tuple
import requests

from ..config.constants import UPDATE_DIR_NAME
from ..utils.logger import get_logger


class Downloader:
    """Gerenciador de downloads"""

    def __init__(self):
        self.logger = get_logger()
        self._progress_callback: Optional[Callable[[int, int], None]] = None
        self._cancel_requested = False

    def set_progress_callback(self, callback: Callable[[int, int], None]):
        """
        Define callback para progresso do download

        Args:
            callback: Função (bytes_baixados, total_bytes)
        """
        self._progress_callback = callback

    def cancel(self):
        """Solicita cancelamento do download"""
        self._cancel_requested = True

    def download(
        self,
        url: str,
        destination: Optional[str] = None,
        expected_hash: Optional[str] = None,
        chunk_size: int = 8192
    ) -> Tuple[bool, str]:
        """
        Faz download de arquivo

        Args:
            url: URL do arquivo
            destination: Caminho de destino (opcional, usa temp se não fornecido)
            expected_hash: Hash SHA256 esperado para validação
            chunk_size: Tamanho do chunk para download

        Returns:
            Tuple[bool, str]: (sucesso, caminho_arquivo ou mensagem_erro)
        """
        self._cancel_requested = False

        try:
            # Define destino
            if destination:
                dest_path = destination
            else:
                # Usa diretório temporário
                temp_dir = Path(tempfile.gettempdir()) / UPDATE_DIR_NAME
                temp_dir.mkdir(exist_ok=True)

                # Extrai nome do arquivo da URL
                filename = url.split('/')[-1].split('?')[0]
                if not filename:
                    filename = "download.tmp"

                dest_path = str(temp_dir / filename)

            self.logger.info(f"Iniciando download: {url}")

            # Faz requisição com streaming
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            # Obtém tamanho total
            total_size = int(response.headers.get('content-length', 0))

            # Hash para validação
            sha256_hash = hashlib.sha256() if expected_hash else None

            # Download com progresso
            bytes_downloaded = 0

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self._cancel_requested:
                        f.close()
                        os.remove(dest_path)
                        return False, "Download cancelado"

                    if chunk:
                        f.write(chunk)
                        bytes_downloaded += len(chunk)

                        if sha256_hash:
                            sha256_hash.update(chunk)

                        if self._progress_callback:
                            self._progress_callback(bytes_downloaded, total_size)

            # Valida hash se fornecido
            if expected_hash and sha256_hash:
                calculated_hash = sha256_hash.hexdigest().lower()
                expected_hash = expected_hash.lower()

                if calculated_hash != expected_hash:
                    os.remove(dest_path)
                    return False, f"Hash inválido. Esperado: {expected_hash}, Obtido: {calculated_hash}"

            self.logger.info(f"Download concluído: {dest_path}")
            return True, dest_path

        except requests.exceptions.Timeout:
            return False, "Timeout no download"

        except requests.exceptions.HTTPError as e:
            return False, f"Erro HTTP: {e.response.status_code}"

        except requests.exceptions.ConnectionError:
            return False, "Erro de conexão"

        except Exception as e:
            self.logger.error(f"Erro no download: {e}")
            return False, str(e)

    def download_to_memory(self, url: str, max_size: int = 10 * 1024 * 1024) -> Tuple[bool, bytes]:
        """
        Faz download para memória (para arquivos pequenos)

        Args:
            url: URL do arquivo
            max_size: Tamanho máximo permitido (default 10MB)

        Returns:
            Tuple[bool, bytes]: (sucesso, dados ou mensagem_erro)
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            content_length = int(response.headers.get('content-length', 0))

            if content_length > max_size:
                return False, f"Arquivo muito grande: {content_length} bytes"

            return True, response.content

        except Exception as e:
            self.logger.error(f"Erro no download: {e}")
            return False, str(e).encode()

    @staticmethod
    def cleanup_temp_downloads():
        """Remove downloads temporários antigos"""
        import shutil
        from datetime import datetime

        temp_dir = Path(tempfile.gettempdir()) / UPDATE_DIR_NAME

        if not temp_dir.exists():
            return

        # Remove arquivos com mais de 24h
        max_age = 24 * 3600  # 24 horas em segundos
        now = datetime.now().timestamp()

        for item in temp_dir.iterdir():
            try:
                age = now - item.stat().st_mtime
                if age > max_age:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
            except Exception:
                continue
