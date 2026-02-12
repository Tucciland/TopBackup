"""
TopBackup - Constantes do Sistema
"""

# Intervalos de tempo (em segundos)
CONFIG_SYNC_INTERVAL = 1800  # 30 minutos
UPDATE_CHECK_INTERVAL = 600  # 10 minutos (teste) - após testes mudar para 3600 (1 hora)

# Timeouts (em segundos)
FIREBIRD_TIMEOUT = 30
MYSQL_TIMEOUT = 30
FTP_TIMEOUT = 60
BACKUP_TIMEOUT = 3600  # 1 hora para backups grandes

# Tamanhos de buffer
IPC_BUFFER_SIZE = 65536
FTP_CHUNK_SIZE = 8192

# Dias da semana (Firebird → Python)
DIAS_SEMANA = {
    'DOM': 6,
    'SEG': 0,
    'TER': 1,
    'QUA': 2,
    'QUI': 3,
    'SEX': 4,
    'SAB': 5
}

# Status do backup
STATUS_PENDENTE = 'P'
STATUS_EXECUTANDO = 'E'
STATUS_SUCESSO = 'S'
STATUS_FALHA = 'F'

# Tipos de backup
TIPO_VERSIONADO = 'V'  # CNPJ_YYYYMMDD_HHMMSS.zip
TIPO_SEMANAL = 'S'     # CNPJ_SEG.zip
TIPO_UNICO = 'U'       # CNPJ.zip

# Caminhos padrão do Firebird (x86 primeiro pois é mais comum)
FIREBIRD_PATHS = [
    r"C:\Program Files (x86)\Firebird\Firebird_2_5\bin\gbak.exe",
    r"C:\Program Files\Firebird\Firebird_2_5\bin\gbak.exe",
    r"C:\Firebird\Firebird_2_5\bin\gbak.exe",
]

# Named Pipe para IPC
IPC_PIPE_NAME = r"\\.\pipe\TopBackupIPC"

# Nome do serviço Windows
SERVICE_NAME = "TopBackupService"
SERVICE_DISPLAY_NAME = "TopBackup Backup Service"
SERVICE_DESCRIPTION = "Serviço de backup automático TopBackup"

# Diretórios de trabalho
TEMP_DIR_NAME = "topbackup_temp"
UPDATE_DIR_NAME = "topbackup_update"

# Extensões de arquivo
BACKUP_EXTENSION = ".fbk"
ZIP_EXTENSION = ".zip"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos
