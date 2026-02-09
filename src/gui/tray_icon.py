"""
TopBackup - System Tray Icon
Ícone na bandeja do sistema usando pystray
"""

import threading
from typing import Optional, Callable
from PIL import Image
import pystray
from pystray import MenuItem, Menu

from ..utils.logger import get_logger


class TrayIcon:
    """Gerenciador do ícone na bandeja do sistema"""

    def __init__(
        self,
        icon_path: str,
        app_name: str = "TopBackup",
        on_show: Optional[Callable] = None,
        on_backup: Optional[Callable] = None,
        on_quit: Optional[Callable] = None
    ):
        self.icon_path = icon_path
        self.app_name = app_name
        self.logger = get_logger()

        # Callbacks
        self._on_show = on_show
        self._on_backup = on_backup
        self._on_quit = on_quit

        # Ícone
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def _create_image(self) -> Image.Image:
        """Cria ou carrega imagem do ícone"""
        try:
            return Image.open(self.icon_path)
        except Exception:
            # Cria ícone padrão se não encontrar arquivo
            self.logger.warning(f"Ícone não encontrado: {self.icon_path}")
            return self._create_default_icon()

    def _create_default_icon(self) -> Image.Image:
        """Cria ícone padrão (quadrado verde)"""
        from PIL import ImageDraw

        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Fundo verde
        draw.rectangle([4, 4, size-4, size-4], fill=(46, 204, 113, 255))

        # Letra B
        draw.text(
            (size//3, size//4),
            "B",
            fill=(255, 255, 255, 255)
        )

        return image

    def _create_menu(self) -> Menu:
        """Cria menu do tray"""
        return Menu(
            MenuItem("Abrir", self._show_action, default=True),
            MenuItem("Backup Agora", self._backup_action),
            Menu.SEPARATOR,
            MenuItem("Sair", self._quit_action)
        )

    def _show_action(self, icon, item):
        """Ação de mostrar janela"""
        if self._on_show:
            self._on_show()

    def _backup_action(self, icon, item):
        """Ação de backup"""
        if self._on_backup:
            self._on_backup()

    def _quit_action(self, icon, item):
        """Ação de sair"""
        self.stop()
        if self._on_quit:
            self._on_quit()

    def start(self):
        """Inicia o ícone na bandeja"""
        image = self._create_image()
        menu = self._create_menu()

        self._icon = pystray.Icon(
            name=self.app_name,
            icon=image,
            title=self.app_name,
            menu=menu
        )

        # Roda em thread separada
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

        self.logger.debug("System Tray iniciado")

    def stop(self):
        """Para o ícone na bandeja"""
        if self._icon:
            self._icon.stop()
            self._icon = None

        self.logger.debug("System Tray parado")

    def notify(self, title: str, message: str):
        """Mostra notificação toast"""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception as e:
                self.logger.warning(f"Erro ao enviar notificação: {e}")

    def update_icon(self, icon_path: str):
        """Atualiza ícone"""
        if self._icon:
            try:
                new_image = Image.open(icon_path)
                self._icon.icon = new_image
            except Exception as e:
                self.logger.warning(f"Erro ao atualizar ícone: {e}")

    def update_title(self, title: str):
        """Atualiza título do ícone"""
        if self._icon:
            self._icon.title = title

    @property
    def is_running(self) -> bool:
        """Verifica se tray está rodando"""
        return self._icon is not None and self._icon.visible
