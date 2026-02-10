"""
TopBackup - Gerenciador de Configurações
Carrega e salva config.json
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict, field


@dataclass
class FirebirdConfig:
    """Configurações de conexão Firebird"""
    database_path: str = ""
    gbak_path: str = ""
    user: str = "SYSDBA"
    password: str = "masterkey"
    charset: str = "UTF8"


@dataclass
class MySQLConfig:
    """Configurações de conexão MySQL"""
    host: str = ""
    port: int = 3306
    database: str = "PROJETO_BACKUPS"
    user: str = ""
    password: str = ""


@dataclass
class FTPConfig:
    """Configurações de FTP"""
    host: str = ""
    port: int = 21
    user: str = ""
    password: str = ""
    remote_path: str = "/backups"
    passive_mode: bool = True


@dataclass
class AppConfig:
    """Configurações gerais do aplicativo"""
    first_run: bool = True
    run_as_service: bool = False
    start_minimized: bool = True
    auto_update: bool = True
    empresa_id: Optional[int] = None
    empresa_cnpj: str = ""


@dataclass
class BackupConfig:
    """Configurações de backup"""
    local_destino1: str = ""
    local_destino2: str = ""
    backup_remoto: bool = False
    prefixo_backup: str = "V"  # V=Versionado, S=Semanal, U=Unico
    compactar_zip: bool = True
    verificar_backup: bool = True


@dataclass
class Settings:
    """Configurações completas do aplicativo"""
    firebird: FirebirdConfig = field(default_factory=FirebirdConfig)
    mysql: MySQLConfig = field(default_factory=MySQLConfig)
    ftp: FTPConfig = field(default_factory=FTPConfig)
    app: AppConfig = field(default_factory=AppConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)

    _config_path: str = field(default="", repr=False)

    @classmethod
    def get_config_path(cls) -> Path:
        """Retorna o caminho do arquivo de configuração"""
        # Verifica se está rodando como executável empacotado
        if getattr(os.sys, 'frozen', False):
            # Executável - sempre usa C:\TOPBACKUP
            base_path = Path(r"C:\TOPBACKUP")
        else:
            # Desenvolvimento
            base_path = Path(__file__).parent.parent.parent

        return base_path / "config" / "config.json"

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Settings":
        """Carrega configurações do arquivo JSON"""
        if config_path is None:
            config_path = str(cls.get_config_path())

        settings = cls()
        settings._config_path = config_path

        # Se não existe config.json, copia do config.json.example
        if not os.path.exists(config_path):
            example_path = config_path.replace('config.json', 'config.json.example')
            if os.path.exists(example_path):
                import shutil
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                shutil.copy(example_path, config_path)

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Carrega Firebird config
                if 'firebird' in data:
                    settings.firebird = FirebirdConfig(**data['firebird'])

                # Carrega MySQL config
                if 'mysql' in data:
                    settings.mysql = MySQLConfig(**data['mysql'])

                # Carrega FTP config
                if 'ftp' in data:
                    settings.ftp = FTPConfig(**data['ftp'])

                # Carrega App config
                if 'app' in data:
                    settings.app = AppConfig(**data['app'])

                # Carrega Backup config
                if 'backup' in data:
                    backup_data = data['backup'].copy()
                    # Compatibilidade: renomeia campo antigo para novo
                    if 'prefixo_arquivo' in backup_data:
                        backup_data['prefixo_backup'] = backup_data.pop('prefixo_arquivo')
                    settings.backup = BackupConfig(**backup_data)

            except (json.JSONDecodeError, TypeError) as e:
                print(f"Erro ao carregar configurações: {e}")

        return settings

    def save(self, config_path: Optional[str] = None) -> bool:
        """Salva configurações no arquivo JSON"""
        if config_path is None:
            config_path = self._config_path or str(self.get_config_path())

        try:
            # Garante que o diretório existe
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            data = {
                'firebird': asdict(self.firebird),
                'mysql': asdict(self.mysql),
                'ftp': asdict(self.ftp),
                'app': asdict(self.app),
                'backup': asdict(self.backup)
            }

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")
            return False

    def is_configured(self) -> bool:
        """Verifica se as configurações básicas estão preenchidas"""
        return (
            bool(self.firebird.database_path) and
            bool(self.firebird.gbak_path) and
            bool(self.mysql.host) and
            bool(self.mysql.user)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Converte configurações para dicionário"""
        return {
            'firebird': asdict(self.firebird),
            'mysql': asdict(self.mysql),
            'ftp': asdict(self.ftp),
            'app': asdict(self.app),
            'backup': asdict(self.backup)
        }
