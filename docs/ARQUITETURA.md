# Arquitetura

Como o TopBackup e Dashboard funcionam por baixo dos panos.

---

## Visão Geral

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENTE (Windows)                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │  Firebird   │───>│  TopBackup  │───>│  Backup (.zip)          │  │
│  │  2.5 Local  │    │   App       │    │  - LOCAL_DESTINO1       │  │
│  │             │    │             │    │  - LOCAL_DESTINO2       │  │
│  │ - EMPRESA   │    │ - gbak.exe  │    │  - FTP (opcional)       │  │
│  │ - AGENDA    │    │ - ZIP       │    └─────────────────────────┘  │
│  └─────────────┘    │ - Sync      │                                 │
│                     └──────┬──────┘                                 │
└────────────────────────────│────────────────────────────────────────┘
                             │ MySQL Sync
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      NUVEM (MySQL + Django)                         │
│  ┌───────────────────────────────────────┐   ┌─────────────────┐   │
│  │  MySQL - PROJETO_BACKUPS              │   │    Dashboard    │   │
│  │  - EMPRESA (dados sincronizados)      │<──│    Django 6.0   │   │
│  │  - LOG_BACKUPS (histórico)            │   │                 │   │
│  │  - VERSAO_APP (atualizações)          │   │  - Status       │   │
│  └───────────────────────────────────────┘   │  - Alertas      │   │
│                                               │  - Histórico    │   │
│                                               └─────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## TopBackup - Estrutura de Módulos

```
TopBackup/src/
├── main.py                 # Entry point - CLI + GUI
├── version.py              # Versão atual (1.0.6)
│
├── core/                   # Núcleo da aplicação
│   ├── app_controller.py   # Orquestrador principal
│   ├── backup_engine.py    # Execução do gbak + compactação
│   ├── scheduler.py        # APScheduler wrapper
│   └── installer.py        # Instalação Windows
│
├── database/               # Conexões de banco
│   ├── firebird_client.py  # Lê dados do Firebird local
│   ├── mysql_client.py     # Grava logs no MySQL nuvem
│   ├── sync_manager.py     # Sincronização Firebird → MySQL
│   └── models.py           # Dataclasses (Empresa, LogBackup, etc)
│
├── gui/                    # Interface CustomTkinter
│   ├── main_window.py      # Janela principal
│   ├── setup_wizard.py     # Wizard de 4 passos
│   ├── dialogs.py          # Diálogos auxiliares
│   └── tray_icon.py        # Ícone na bandeja
│
├── service/                # Serviço Windows
│   ├── windows_service.py  # Instalação/controle do serviço
│   ├── ipc_client.py       # Cliente IPC (Named Pipes)
│   └── ipc_server.py       # Servidor IPC
│
├── network/                # Operações de rede
│   ├── ftp_client.py       # Upload FTP
│   ├── downloader.py       # Download de atualizações
│   └── update_checker.py   # Verificador de versão
│
├── config/                 # Configurações
│   ├── settings.py         # Loader do config.json
│   └── constants.py        # Constantes do sistema
│
└── utils/                  # Utilitários
    ├── logger.py           # Logger rotativo
    ├── firebird_loader.py  # Carrega fbclient.dll
    ├── file_utils.py       # Operações de arquivo
    └── resilience.py       # Retry, circuit breaker
```

---

## Fluxo de Backup (Passo a Passo)

```
1. INICIALIZAÇÃO
   │
   ├─> Carrega config.json
   ├─> Inicializa fbclient.dll
   ├─> Conecta Firebird local
   │   └─> Lê EMPRESA e AGENDA_BACKUP
   ├─> Conecta MySQL nuvem
   │   └─> Sincroniza dados da empresa
   └─> Agenda backups (APScheduler)
       └─> Um job por agenda configurada

2. NO HORÁRIO AGENDADO
   │
   ├─> Verifica se dia está ativo (dom/seg/ter...)
   ├─> Cria registro LOG_BACKUPS (status=P)
   │
   ├─> EXECUÇÃO DO GBAK
   │   ├─> Comando: [gbak, -b, -user, SYSDBA, -pass, X, banco.fdb, backup.fbk]
   │   ├─> Timeout: 1 hora
   │   └─> Output: arquivo .fbk no temp
   │
   ├─> VALIDAÇÃO
   │   └─> Verifica se arquivo > 0 bytes
   │
   ├─> COMPACTAÇÃO
   │   ├─> Cria ZIP com nome baseado no prefixo:
   │   │   ├─> V: CNPJ_20260215_230000.zip
   │   │   ├─> S: CNPJ_SEX.zip
   │   │   └─> U: CNPJ.zip
   │   └─> Remove .fbk temporário
   │
   ├─> CÓPIA
   │   ├─> LOCAL_DESTINO1 (obrigatório)
   │   └─> LOCAL_DESTINO2 (opcional)
   │
   ├─> FTP (se configurado)
   │   └─> Upload pro servidor remoto
   │
   └─> FINALIZAÇÃO
       ├─> Atualiza LOG_BACKUPS (status=S ou F)
       └─> Registra tamanho, duração, path
```

---

## Dashboard - Estrutura Django

```
DASHBOARD_CLIENTES/
├── manage.py
├── core/                           # Projeto Django
│   ├── settings.py                 # Configurações
│   ├── urls.py                     # Rotas principais
│   └── wsgi.py                     # WSGI entry
│
└── monitoramento_backup_topsoft/   # App de monitoramento
    ├── models.py                   # Mapeamento das tabelas MySQL
    ├── views.py                    # Views do dashboard
    ├── services.py                 # Lógica de negócio
    ├── urls.py                     # Rotas da app
    └── templates/
        └── dashboard.html          # Template principal
```

### Views e Endpoints

| Endpoint | View | Descrição |
|----------|------|-----------|
| `/` | MonitoramentoBackupDashboardView | Dashboard principal |
| `/api/status/` | StatusGeralAPIView | Contadores gerais (AJAX) |
| `/api/cards/` | CardsEmpresasAPIView | Cards das empresas (AJAX) |
| `/api/executando/` | BackupsEmExecucaoAPIView | Backups em execução |

### Lógica de Status (services.py)

```python
# Classificação das empresas no dashboard:

OK         = backup nas últimas 24h
ATENCAO    = backup entre 24h e 48h atrás
VERIFICAR  = sem backup há mais de 48h
FALHA      = último backup falhou
EXECUTANDO = backup em andamento (status='E')

# Prioridade de exibição nos cards:
1. Falha
2. Verificar
3. Sem dados
4. Atenção
5. OK
```

---

## Banco de Dados

### MySQL - PROJETO_BACKUPS (Nuvem)

```
┌─────────────────────┐       ┌─────────────────────┐
│      EMPRESA        │       │    LOG_BACKUPS      │
├─────────────────────┤       ├─────────────────────┤
│ ID (PK)             │──┐    │ ID (PK)             │
│ ID_AUX              │  │    │ ID_EMPRESA (FK) ────┘
│ FANTASIA            │  │    │ DATA_INICIO         │
│ RAZAO               │  │    │ DATA_FIM            │
│ CNPJ (UNIQUE)       │  │    │ NOME_ARQUIVO        │
│ DATA_ULTIMA_INTERACAO    │ │ CAMINHO_DESTINO     │
│ VERSAO_LOCAL        │  │    │ CAMINHO_DESTINO2    │
│ ATIVO (S/N)         │  │    │ TAMANHO_BYTES       │
└─────────────────────┘  │    │ TAMANHO_FORMATADO   │
                         │    │ STATUS (P/E/S/F)    │
┌─────────────────────┐  │    │ MENSAGEM_ERRO       │
│     VERSAO_APP      │  │    │ TIPO_BACKUP (V/S/U) │
├─────────────────────┤  │    │ ENVIADO_FTP (S/N)   │
│ ID (PK)             │  │    │ DATA_ENVIO_FTP      │
│ VERSAO (UNIQUE)     │  │    │ MANUAL (S/N)        │
│ DATA_LANCAMENTO     │  └────┴─────────────────────┘
│ URL_DOWNLOAD        │
│ HASH_SHA256         │
│ CHANGELOG           │
│ OBRIGATORIA (S/N)   │
└─────────────────────┘
```

### Firebird Local (Cliente)

```
┌─────────────────────┐       ┌─────────────────────┐
│      EMPRESA        │       │   AGENDA_BACKUP     │
├─────────────────────┤       ├─────────────────────┤
│ CODIGO / ID         │       │ ID (PK)             │
│ FANTASIA            │       │ HORARIO (HH:MM)     │
│ RAZAO / RAZAO_SOCIAL│       │ DOM (S/N)           │
│ CNPJ                │       │ SEG (S/N)           │
│ DATA_CADASTRO       │       │ TER (S/N)           │
└─────────────────────┘       │ QUA (S/N)           │
                              │ QUI (S/N)           │
                              │ SEX (S/N)           │
                              │ SAB (S/N)           │
                              │ LOCAL_DESTINO1      │
                              │ LOCAL_DESTINO2      │
                              │ BACKUP_REMOTO (S/N) │
                              │ PREFIXO_BACKUP      │
                              │ BANCO_ORIGEM        │
                              └─────────────────────┘
```

### Códigos de Status

| Código | Nome | Descrição |
|--------|------|-----------|
| P | Pendente | Backup agendado, ainda não iniciou |
| E | Executando | Backup em andamento |
| S | Sucesso | Backup concluído com sucesso |
| F | Falha | Backup falhou |

---

## Comunicação entre Componentes

### Sincronização (TopBackup → MySQL)

```
TopBackup                              MySQL Cloud
    │                                      │
    ├── Lê EMPRESA do Firebird             │
    │                                      │
    ├── INSERT/UPDATE em EMPRESA ─────────>│
    │   (CNPJ é chave única)               │
    │                                      │
    ├── Atualiza DATA_ULTIMA_INTERACAO ───>│
    │                                      │
    ├── A cada backup:                     │
    │   INSERT em LOG_BACKUPS ────────────>│
    │                                      │
    ├── Checa VERSAO_APP <─────────────────│
    │   (verifica se tem update)           │
    │                                      │
    └── Intervalo: 30 minutos              │
```

### Dashboard (MySQL → Django)

```
Django                                 MySQL Cloud
    │                                      │
    ├── SELECT EMPRESA ────────────────────│
    │   WHERE ATIVO = 'S'                  │
    │                                      │
    ├── SELECT LOG_BACKUPS <───────────────│
    │   (último por empresa)               │
    │                                      │
    ├── Calcula status (OK/ATENCAO/etc)    │
    │                                      │
    └── Renderiza dashboard                │
```

---

## Serviço Windows

O TopBackup pode rodar como serviço Windows:

```
┌─────────────────────────────────────────────────┐
│              TopBackupService                   │
│  ┌──────────────┐    ┌────────────────────┐     │
│  │ IPC Server   │<──>│ AppController      │     │
│  │ (Named Pipes)│    │ (lógica principal) │     │
│  └──────────────┘    └────────────────────┘     │
└─────────────────────────────────────────────────┘
        ↑
        │ Named Pipe: \\.\pipe\topbackup
        ↓
┌─────────────────────────────────────────────────┐
│              TopBackup GUI (opcional)           │
│  ┌──────────────┐                               │
│  │ IPC Client   │ Envia comandos pro serviço    │
│  └──────────────┘                               │
└─────────────────────────────────────────────────┘
```

### Comandos CLI

```bash
topbackup --install     # Instala o serviço
topbackup --uninstall   # Remove o serviço
topbackup --start       # Inicia o serviço
topbackup --stop        # Para o serviço
topbackup --status      # Verifica status
```

---

## Resiliência e Logs

### Padrões de Resiliência

- **Retry com backoff exponencial**: reconexão automática em caso de falha
- **Circuit breaker**: evita sobrecarga quando banco está fora
- **Timeout**: 1 hora máximo por backup (gbak pode demorar)

### Logs

```
C:\TOPBACKUP\logs\topbackup.log
├── Rotação: 5 arquivos x 5MB cada
├── Formato: timestamp - level - module - message
└── Níveis: DEBUG, INFO, WARNING, ERROR
```

---

## Constantes Importantes

```python
# Intervalos (segundos)
CONFIG_SYNC_INTERVAL = 1800    # 30 minutos
UPDATE_CHECK_INTERVAL = 600    # 10 minutos (teste)
BACKUP_TIMEOUT = 3600          # 1 hora

# Timezone
TIMEZONE = "America/Sao_Paulo"

# Diretórios
TEMP_DIR = "C:\\TOPBACKUP\\temp"
LOG_DIR = "C:\\TOPBACKUP\\logs"

# Estados da aplicação
INITIALIZING, RUNNING, BACKUP_RUNNING, PAUSED, ERROR, STOPPED
```
