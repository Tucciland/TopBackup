"""
TopBackup - Gerenciador do ServReplicacao.exe
Verifica, baixa e inicia o processo ServReplicacao
"""

import subprocess
import re
import time
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Tuple, Optional, List

from ..config.settings import Settings
from ..config.constants import SERV_REPLICACAO_EXE, SERV_REPLICACAO_GOOGLE_DRIVE_ID
from ..utils.logger import get_logger


# Windows API - constantes para fechar janelas
WM_CLOSE = 0x0010
WM_SYSCOMMAND = 0x0112
SC_CLOSE = 0xF060
VK_MENU = 0x12  # Alt key
VK_F4 = 0x73    # F4 key


class ServReplicacaoManager:
    """Gerenciador do processo ServReplicacao.exe"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger()

    def get_exe_path(self) -> Optional[Path]:
        """
        Calcula o caminho do ServReplicacao.exe baseado no banco de dados.

        Exemplo: banco em "C:\\GESTOR\\Dados\\DADOS.FDB" → exe em "C:\\GESTOR\\ServReplicacao.exe"

        Returns:
            Path do executável ou None se não houver banco configurado
        """
        db_path = self.settings.firebird.database_path

        if not db_path:
            self.logger.warning("ServReplicacao: Nenhum banco de dados configurado")
            return None

        try:
            # Exemplo: C:\GESTOR\Dados\DADOS.FDB → C:\GESTOR\
            db_path_obj = Path(db_path)
            # parent = Dados, parent.parent = GESTOR
            exe_path = db_path_obj.parent.parent / SERV_REPLICACAO_EXE
            return exe_path
        except Exception as e:
            self.logger.error(f"ServReplicacao: Erro ao calcular caminho: {e}")
            return None

    def is_running(self) -> bool:
        """
        Verifica se ServReplicacao.exe está rodando.

        Returns:
            True se o processo estiver em execução
        """
        try:
            # tasklist /fi "imagename eq ServReplicacao.exe"
            result = subprocess.run(
                ["tasklist", "/fi", f"imagename eq {SERV_REPLICACAO_EXE}"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Se o processo existe, a saída conterá o nome do executável
            return SERV_REPLICACAO_EXE.lower() in result.stdout.lower()

        except Exception as e:
            self.logger.error(f"ServReplicacao: Erro ao verificar processo: {e}")
            return False

    def exe_exists(self) -> bool:
        """
        Verifica se o executável existe no disco.

        Returns:
            True se o arquivo existir
        """
        exe_path = self.get_exe_path()
        if exe_path is None:
            return False
        return exe_path.exists()

    def _find_windows_by_pid(self, pid: int) -> List[int]:
        """
        Encontra todas as janelas pertencentes a um processo específico.

        Args:
            pid: Process ID

        Returns:
            Lista de handles (HWND) das janelas encontradas
        """
        result = []

        try:
            user32 = ctypes.windll.user32

            # Callback para EnumWindows
            def enum_callback(hwnd, _):
                # Verifica se a janela é visível
                if not user32.IsWindowVisible(hwnd):
                    return True

                # Obtém o PID da janela
                window_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))

                if window_pid.value == pid:
                    # Obtém título para log
                    length = user32.GetWindowTextLengthW(hwnd)
                    title = ""
                    if length > 0:
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buffer, length + 1)
                        title = buffer.value

                    self.logger.debug(f"ServReplicacao: Janela encontrada - hwnd={hwnd}, title='{title}'")
                    result.append(hwnd)

                return True

            # Define o tipo do callback
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

        except Exception as e:
            self.logger.error(f"ServReplicacao: Erro ao enumerar janelas: {e}")

        return result

    def _close_window_aggressive(self, hwnd: int) -> bool:
        """
        Fecha uma janela usando múltiplos métodos.

        Tenta em ordem:
        1. WM_SYSCOMMAND + SC_CLOSE (simula clique no X)
        2. WM_CLOSE
        3. Alt+F4 simulado

        Args:
            hwnd: Handle da janela

        Returns:
            True se algum método foi executado
        """
        try:
            user32 = ctypes.windll.user32

            # Primeiro, traz a janela para frente (necessário para Alt+F4)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.1)

            # Método 1: WM_SYSCOMMAND + SC_CLOSE (mais confiável para apps Delphi/VB)
            self.logger.debug("ServReplicacao: Tentando WM_SYSCOMMAND + SC_CLOSE")
            user32.PostMessageW(hwnd, WM_SYSCOMMAND, SC_CLOSE, 0)
            time.sleep(0.3)

            # Verifica se a janela ainda existe
            if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
                self.logger.info("ServReplicacao: Janela fechada via WM_SYSCOMMAND")
                return True

            # Método 2: WM_CLOSE
            self.logger.debug("ServReplicacao: Tentando WM_CLOSE")
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            time.sleep(0.3)

            if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
                self.logger.info("ServReplicacao: Janela fechada via WM_CLOSE")
                return True

            # Método 3: Simular Alt+F4
            self.logger.debug("ServReplicacao: Tentando Alt+F4")
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.1)

            # Simula pressionar Alt+F4
            user32.keybd_event(VK_MENU, 0, 0, 0)  # Alt down
            user32.keybd_event(VK_F4, 0, 0, 0)    # F4 down
            user32.keybd_event(VK_F4, 0, 2, 0)    # F4 up (KEYEVENTF_KEYUP = 2)
            user32.keybd_event(VK_MENU, 0, 2, 0)  # Alt up

            time.sleep(0.3)

            if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
                self.logger.info("ServReplicacao: Janela fechada via Alt+F4")
                return True

            self.logger.warning("ServReplicacao: Nenhum método conseguiu fechar a janela")
            return False

        except Exception as e:
            self.logger.error(f"ServReplicacao: Erro ao fechar janela: {e}")
            return False

    def start(self, silent: bool = True) -> Tuple[bool, str]:
        """
        Inicia o ServReplicacao.exe.

        Args:
            silent: Se True, fecha a janela após iniciar (vai para bandeja)

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        exe_path = self.get_exe_path()

        if exe_path is None:
            return False, "Caminho do executável não determinado"

        if not exe_path.exists():
            return False, f"Executável não encontrado: {exe_path}"

        try:
            # Inicia o processo e captura o PID
            process = subprocess.Popen(
                [str(exe_path)],
                cwd=str(exe_path.parent),
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            pid = process.pid
            self.logger.info(f"ServReplicacao: Processo iniciado PID={pid} - {exe_path}")

            # Se modo silencioso, aguarda a janela aparecer e fecha ela
            if silent:
                self._close_servreplicacao_window_by_pid(pid)

            return True, f"Processo iniciado: {exe_path}"

        except Exception as e:
            self.logger.error(f"ServReplicacao: Erro ao iniciar: {e}")
            return False, str(e)

    def _close_servreplicacao_window_by_pid(self, pid: int, max_attempts: int = 10, delay: float = 0.3):
        """
        Aguarda a janela do ServReplicacao aparecer e fecha ela.

        Usa o PID do processo para encontrar a janela correta.

        Args:
            pid: Process ID do ServReplicacao
            max_attempts: Número máximo de tentativas
            delay: Tempo de espera entre tentativas (segundos)
        """
        self.logger.info(f"ServReplicacao: Aguardando janela do PID {pid} para fechar...")

        for attempt in range(max_attempts):
            time.sleep(delay)

            # Encontra janelas do processo
            windows = self._find_windows_by_pid(pid)

            if windows:
                self.logger.info(f"ServReplicacao: Encontrada(s) {len(windows)} janela(s) do processo")

                for hwnd in windows:
                    if self._close_window_aggressive(hwnd):
                        self.logger.info("ServReplicacao: Janela fechada, app deve estar na bandeja")
                        return

                # Se chegou aqui, nenhuma janela foi fechada com sucesso
                # Tenta mais uma vez na próxima iteração
                continue

        self.logger.warning(f"ServReplicacao: Não foi possível fechar a janela após {max_attempts} tentativas")

    def _get_google_drive_download_url(self, file_id: str) -> str:
        """
        Gera URL de download direto do Google Drive.

        Args:
            file_id: ID do arquivo no Google Drive

        Returns:
            URL de download
        """
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    def download(self) -> Tuple[bool, str]:
        """
        Baixa o ServReplicacao.exe do Google Drive.

        Trata o aviso de vírus do Google Drive para arquivos > 100MB.

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        import requests

        exe_path = self.get_exe_path()

        if exe_path is None:
            return False, "Caminho do executável não determinado"

        try:
            # Garante que o diretório existe
            exe_path.parent.mkdir(parents=True, exist_ok=True)

            file_id = SERV_REPLICACAO_GOOGLE_DRIVE_ID
            url = self._get_google_drive_download_url(file_id)

            self.logger.info(f"ServReplicacao: Iniciando download de {url}")

            # Sessão para manter cookies
            session = requests.Session()

            # Primeira requisição
            response = session.get(url, stream=True, timeout=60)

            # Verifica se há aviso de vírus (arquivo grande)
            # Google redireciona para página de confirmação
            confirm_token = None

            # Método 1: Procura nos cookies
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    confirm_token = value
                    self.logger.info(f"ServReplicacao: Token encontrado no cookie: {confirm_token}")
                    break

            # Método 2: Se é HTML, procura o token no conteúdo
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                content = response.text

                # Procura por vários padrões de confirmação
                patterns = [
                    r'confirm=([a-zA-Z0-9_-]+)',
                    r'confirm=t&',
                    r'/uc\?export=download[^"]*confirm=([^&"]+)',
                    r'id="download-form"[^>]*action="([^"]+)"',
                ]

                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        if match.lastindex:
                            confirm_token = match.group(1)
                        else:
                            confirm_token = 't'
                        self.logger.info(f"ServReplicacao: Token encontrado no HTML: {confirm_token}")
                        break

                # Método 3: Procura pelo UUID do arquivo e tenta download direto
                if confirm_token is None:
                    # Tenta com confirm=t (funciona para alguns arquivos)
                    confirm_token = 't'
                    self.logger.info("ServReplicacao: Usando confirm=t como fallback")

            # Se há token de confirmação, faz segunda requisição
            if confirm_token:
                self.logger.info(f"ServReplicacao: Confirmando download com token: {confirm_token}")
                url_with_confirm = f"{url}&confirm={confirm_token}"

                # Adiciona headers para parecer um navegador
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/octet-stream,*/*',
                }

                response = session.get(url_with_confirm, stream=True, timeout=120, headers=headers)

            # Verifica se a resposta agora é binária
            content_type = response.headers.get('content-type', '')
            content_disp = response.headers.get('content-disposition', '')

            # Se ainda é HTML, tenta mais uma vez com parâmetros adicionais
            if 'text/html' in content_type and 'attachment' not in content_disp:
                self.logger.info("ServReplicacao: Tentando download alternativo...")

                # URL alternativa com mais parâmetros
                alt_url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                }

                response = session.get(alt_url, stream=True, timeout=120, headers=headers)

                content_type = response.headers.get('content-type', '')
                content_disp = response.headers.get('content-disposition', '')

            # Verifica se finalmente temos um arquivo binário
            if 'text/html' in content_type and 'attachment' not in content_disp:
                self.logger.error("ServReplicacao: Download retornou HTML ao invés de binário")
                self.logger.error(f"ServReplicacao: Content-Type: {content_type}")
                return False, "Falha no download - Google Drive requer confirmação manual"

            # Salva o arquivo
            total_size = int(response.headers.get('content-length', 0))
            bytes_downloaded = 0

            with open(exe_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bytes_downloaded += len(chunk)

            # Verifica se o download foi bem sucedido
            if exe_path.exists() and exe_path.stat().st_size > 0:
                # Verifica se não é HTML disfarçado
                with open(exe_path, 'rb') as f:
                    header = f.read(100)
                    if b'<!DOCTYPE' in header or b'<html' in header.lower():
                        exe_path.unlink()
                        return False, "Download resultou em HTML ao invés de executável"

                self.logger.info(f"ServReplicacao: Download concluído - {exe_path} ({bytes_downloaded} bytes)")
                return True, str(exe_path)
            else:
                return False, "Download resultou em arquivo vazio"

        except requests.exceptions.Timeout:
            return False, "Timeout no download"
        except requests.exceptions.ConnectionError:
            return False, "Erro de conexão"
        except Exception as e:
            self.logger.error(f"ServReplicacao: Erro no download: {e}")
            return False, str(e)

    def ensure_running(self) -> Tuple[bool, str]:
        """
        Garante que o ServReplicacao está rodando.

        Fluxo:
        1. Verifica se já está rodando → OK
        2. Se exe não existe → download()
        3. Inicia o processo

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        # 1. Verifica se já está rodando
        if self.is_running():
            self.logger.info("ServReplicacao: Já está em execução")
            return True, "Processo já está em execução"

        # 2. Verifica se o executável existe
        if not self.exe_exists():
            self.logger.info("ServReplicacao: Executável não encontrado, iniciando download")
            success, msg = self.download()

            if not success:
                self.logger.warning(f"ServReplicacao: Falha no download - {msg}")
                return False, f"Falha no download: {msg}"

        # 3. Inicia o processo
        return self.start()
