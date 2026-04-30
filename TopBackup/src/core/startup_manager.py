"""
TopBackup - Gerenciador de Atalhos de Inicialização
Gerencia atalhos no shell:startup do Windows
"""

import os
import subprocess
from pathlib import Path
from typing import Tuple, Optional

from ..config.constants import TOPBACKUP_INSTALL_DIR, TOPBACKUP_EXE, SERV_REPLICACAO_EXE
from ..utils.logger import get_logger


class StartupManager:
    """Gerenciador de atalhos no shell:startup do Windows"""

    def __init__(self):
        self.logger = get_logger()

    def _get_startup_folder(self) -> Path:
        """
        Retorna o caminho da pasta shell:startup.

        Returns:
            Path da pasta Startup
        """
        # %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
        appdata = os.environ.get('APPDATA', '')
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    def shortcut_exists(self, name: str) -> bool:
        """
        Verifica se um atalho existe na pasta Startup.

        Args:
            name: Nome do atalho (sem extensão .lnk)

        Returns:
            True se o atalho existir
        """
        startup_folder = self._get_startup_folder()
        shortcut_path = startup_folder / f"{name}.lnk"
        return shortcut_path.exists()

    def any_shortcut_contains(self, substring: str) -> bool:
        """
        Verifica se existe algum atalho cujo nome contém a substring.

        Útil para detectar atalhos manuais como "TopBackup - Atalho".

        Args:
            substring: Texto a procurar no nome do atalho (case insensitive)

        Returns:
            True se algum atalho contiver a substring
        """
        startup_folder = self._get_startup_folder()

        if not startup_folder.exists():
            return False

        substring_lower = substring.lower()

        for item in startup_folder.iterdir():
            if item.suffix.lower() == '.lnk':
                # Remove extensão e verifica se contém a substring
                name_without_ext = item.stem.lower()
                if substring_lower in name_without_ext:
                    self.logger.info(f"StartupManager: Atalho existente encontrado: {item.name}")
                    return True

        return False

    def create_shortcut(
        self,
        name: str,
        target: str,
        description: str = "",
        working_dir: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Cria um atalho na pasta Startup usando PowerShell.

        Args:
            name: Nome do atalho (sem extensão .lnk)
            target: Caminho completo do executável
            description: Descrição do atalho
            working_dir: Diretório de trabalho (opcional)

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        startup_folder = self._get_startup_folder()

        # Garante que a pasta existe
        if not startup_folder.exists():
            self.logger.warning(f"StartupManager: Pasta Startup não existe: {startup_folder}")
            return False, f"Pasta Startup não encontrada: {startup_folder}"

        shortcut_path = startup_folder / f"{name}.lnk"

        # Se já existe, não recria
        if shortcut_path.exists():
            self.logger.info(f"StartupManager: Atalho já existe: {shortcut_path}")
            return True, "Atalho já existe"

        # Define working_dir se não fornecido
        if working_dir is None:
            working_dir = str(Path(target).parent)

        try:
            # Usa PowerShell + WScript.Shell para criar atalho
            ps_script = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target}"
$Shortcut.WorkingDirectory = "{working_dir}"
$Shortcut.Description = "{description}"
$Shortcut.Save()
'''

            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                self.logger.info(f"StartupManager: Atalho criado: {shortcut_path}")
                return True, str(shortcut_path)
            else:
                error_msg = result.stderr.strip() if result.stderr else "Erro desconhecido"
                self.logger.error(f"StartupManager: Falha ao criar atalho: {error_msg}")
                return False, error_msg

        except Exception as e:
            self.logger.error(f"StartupManager: Erro ao criar atalho: {e}")
            return False, str(e)

    def remove_shortcut(self, name: str) -> Tuple[bool, str]:
        """
        Remove um atalho da pasta Startup.

        Args:
            name: Nome do atalho (sem extensão .lnk)

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        startup_folder = self._get_startup_folder()
        shortcut_path = startup_folder / f"{name}.lnk"

        if not shortcut_path.exists():
            return True, "Atalho não existia"

        try:
            shortcut_path.unlink()
            self.logger.info(f"StartupManager: Atalho removido: {shortcut_path}")
            return True, "Atalho removido"
        except Exception as e:
            self.logger.error(f"StartupManager: Erro ao remover atalho: {e}")
            return False, str(e)

    def ensure_topbackup_shortcut(self) -> Tuple[bool, str]:
        """
        Garante que o atalho do TopBackup existe no Startup.

        Verifica se já existe qualquer atalho contendo "TopBackup" no nome
        (ex: "TopBackup - Atalho") para evitar duplicatas.

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        # Verifica se já existe algum atalho com "TopBackup" no nome
        # Isso evita criar duplicata quando já existe "TopBackup - Atalho" manual
        if self.any_shortcut_contains("TopBackup"):
            return True, "Atalho TopBackup já existe (manual ou automático)"

        target = Path(TOPBACKUP_INSTALL_DIR) / TOPBACKUP_EXE

        # Verifica se o executável existe
        if not target.exists():
            self.logger.warning(f"StartupManager: TopBackup não encontrado: {target}")
            return False, f"Executável não encontrado: {target}"

        return self.create_shortcut(
            name="TopBackup",
            target=str(target),
            description="TopBackup - Gerenciador de Backups Automáticos",
            working_dir=TOPBACKUP_INSTALL_DIR
        )

    def ensure_servreplicacao_shortcut(self, exe_path: Path) -> Tuple[bool, str]:
        """
        Garante que o atalho do ServReplicacao existe no Startup.

        Verifica se já existe qualquer atalho contendo "ServReplicacao" no nome
        para evitar duplicatas.

        Args:
            exe_path: Caminho completo do ServReplicacao.exe

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        # Verifica se já existe algum atalho com "ServReplicacao" no nome
        if self.any_shortcut_contains("ServReplicacao"):
            return True, "Atalho ServReplicacao já existe (manual ou automático)"

        # Verifica se o executável existe
        if not exe_path.exists():
            self.logger.warning(f"StartupManager: ServReplicacao não encontrado: {exe_path}")
            return False, f"Executável não encontrado: {exe_path}"

        return self.create_shortcut(
            name="ServReplicacao",
            target=str(exe_path),
            description="Servico de Replicacao de Dados",
            working_dir=str(exe_path.parent)
        )

    def ensure_all_shortcuts(self, servreplicacao_path: Optional[Path] = None) -> dict:
        """
        Garante que todos os atalhos necessários existem.

        Args:
            servreplicacao_path: Caminho do ServReplicacao.exe (opcional)

        Returns:
            dict com resultados: {'topbackup': (bool, str), 'servreplicacao': (bool, str)}
        """
        results = {}

        # TopBackup
        success, msg = self.ensure_topbackup_shortcut()
        results['topbackup'] = (success, msg)

        if success:
            self.logger.info(f"StartupManager: Atalho TopBackup OK")
        else:
            self.logger.warning(f"StartupManager: Atalho TopBackup falhou: {msg}")

        # ServReplicacao (se path fornecido)
        if servreplicacao_path:
            success, msg = self.ensure_servreplicacao_shortcut(servreplicacao_path)
            results['servreplicacao'] = (success, msg)

            if success:
                self.logger.info(f"StartupManager: Atalho ServReplicacao OK")
            else:
                self.logger.warning(f"StartupManager: Atalho ServReplicacao falhou: {msg}")

        return results
