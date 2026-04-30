# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TopBackup is a Windows backup automation system for Firebird 2.5 databases. It extracts backup schedules from a client's Firebird database (AGENDA_BACKUP table), executes `gbak` to create backups, and syncs status/logs to a central MySQL server.

## Key Commands

```bash
# Run the GUI application
python src/main.py

# Run backup immediately (CLI)
python src/main.py --backup

# Windows Service commands (requires admin)
python src/main.py --install    # Install service
python src/main.py --uninstall  # Remove service
python src/main.py --start      # Start service
python src/main.py --stop       # Stop service
python src/main.py --status     # Check status

# Build executable
pyinstaller topbackup.spec
```

## Architecture

### Core Flow
1. **FirebirdClient** reads EMPRESA and AGENDA_BACKUP tables from local Firebird DB
2. **SyncManager** syncs company data to central MySQL and loads backup schedules
3. **BackupScheduler** (APScheduler) triggers backups at configured times
4. **BackupEngine** executes `gbak -b` → validates → compresses to ZIP → moves to destination
5. **MySQLClient** logs backup results to central server

### Module Structure
- `src/core/` - AppController (orchestrator), BackupEngine, Scheduler, Heartbeat
- `src/database/` - FirebirdClient, MySQLClient, SyncManager, Models (dataclasses)
- `src/gui/` - MainWindow, SetupWizard, Dialogs (CustomTkinter)
- `src/config/` - Settings (JSON config loader), Constants
- `src/service/` - Windows Service implementation, IPC
- `src/network/` - FTP client, Update checker

### Database Tables (Firebird Source)
- **EMPRESA**: CODIGO, FANTASIA, RAZAO, CNPJ, DATA_CADASTRO
- **AGENDA_BACKUP**: ID, HORARIO, DOM-SAB (S/N), LOCAL_DESTINO1, LOCAL_DESTINO2, PREFIXO_BACKUP (V/S/U), BANCO_ORIGEM

### Backup Types (PREFIXO_BACKUP)
- `V` = Versioned: `CNPJ_YYYYMMDD_HHMMSS.zip`
- `S` = Weekly: `CNPJ_SEG.zip` (day of week)
- `U` = Unique: `CNPJ.zip` (always overwrites)

### Configuration
- Config file: `config/config.json` (gitignored, use `.example` as template)
- Local config has priority over Firebird values for backup destinations
- Multiple backup schedules supported (one job per AGENDA_BACKUP row)

## Technical Notes

- Firebird library (fbclient.dll) must be loaded before importing `fdb` module
- The app uses `assets/firebird/x64/` or `x86/` based on Python architecture
- **Comando gbak simplificado:** `gbak -b -user SYSDBA -pass masterkey banco destino` (sem -v, usando lista de argumentos)
- APScheduler timezone is `America/Sao_Paulo`
- Diretório temp do backup: `C:\TOPBACKUP\temp` (não usa %TEMP% do sistema)
- Caminho padrão Firebird: `C:\Program Files (x86)\Firebird\Firebird_2_5`

---

## Processo de Atualização (Release)

### Passos para lançar uma nova versão:

1. **Fazer os ajustes no código**
   - Implementar correções/features necessárias

2. **Atualizar a versão**
   - Editar `src/version.py` e incrementar `VERSION` (ex: "1.0.4" → "1.0.5")

3. **Fazer o build do executável**
   ```bash
   cd TopBackup
   ..\venv\Scripts\pyinstaller.exe topbackup.spec --noconfirm
   ```
   - O executável será gerado em `dist/TopBackup.exe`

4. **Commit e push para o GitHub**
   ```bash
   git add .
   git commit -m "release: vX.X.X - descrição das mudanças"
   git push
   ```

5. **Inserir a nova versão no banco MySQL (VERSAO_APP)**
   - Ver SQL completo na seção abaixo

---

### ⚠️ CHECKLIST OBRIGATÓRIO ANTES DE INSERIR NO BANCO ⚠️

**SEMPRE VERIFICAR ANTES DE EXECUTAR O SQL:**

- [ ] A URL contém `TopBackup/dist/TopBackup.exe` (com a pasta TopBackup)
- [ ] O token do GitHub está atualizado (verificar arquivo `@GIT` na raiz do projeto)
- [ ] A versão no SQL corresponde à versão em `src/version.py`

**ESTRUTURA DO REPOSITÓRIO (não esquecer!):**
```
PROJETO_BACKUP/           ← RAIZ DO GIT (não é TopBackup!)
├── TopBackup/
│   ├── dist/
│   │   └── TopBackup.exe  ← ARQUIVO DO EXECUTÁVEL
│   ├── src/
│   └── ...
└── ...
```

---

### URL de Download (CRÍTICO - LER COM ATENÇÃO)

A URL de download é **sempre a mesma** para todas as versões:

```
https://TOKEN@raw.githubusercontent.com/Tucciland/TopBackup/main/TopBackup/dist/TopBackup.exe
```

**🚨 ERRO COMUM:** Usar `/main/dist/TopBackup.exe` em vez de `/main/TopBackup/dist/TopBackup.exe`

O caminho DEVE incluir `TopBackup/dist/` porque:
- A raiz do repositório Git é `PROJETO_BACKUP`
- A pasta `TopBackup` está DENTRO do repositório
- O arquivo está em `TopBackup/dist/TopBackup.exe`

---

### SQL Completo para Inserir Nova Versão

**Copie e cole este SQL, substituindo apenas os valores indicados:**

```sql
-- Consultar token atual (se precisar)
-- SELECT * FROM CONFIG WHERE CHAVE = 'GITHUB_TOKEN';

-- Inserir nova versão (SUBSTITUIR: X.X.X e DESCRICAO)
INSERT INTO VERSAO_APP (VERSAO, DATA_LANCAMENTO, URL_DOWNLOAD, CHANGELOG, OBRIGATORIA)
VALUES (
    'X.X.X',                    -- ← Substituir pela versão (ex: '1.0.7')
    NOW(),
    'https://TOKEN_DO_ARQUIVO_@GIT@raw.githubusercontent.com/Tucciland/TopBackup/main/TopBackup/dist/TopBackup.exe',
    'DESCRICAO DAS MUDANÇAS',   -- ← Substituir pela descrição
    'N'
);

-- Verificar se inseriu corretamente
SELECT * FROM VERSAO_APP ORDER BY DATA_LANCAMENTO DESC LIMIT 1;
```

**Se o token do GitHub mudar:**
1. Atualizar o arquivo `@GIT` na raiz do projeto
2. Atualizar a URL no SQL acima
3. Se já tiver versão no banco, usar UPDATE:
   ```sql
   UPDATE VERSAO_APP
   SET URL_DOWNLOAD = 'https://NOVO_TOKEN@raw.githubusercontent.com/Tucciland/TopBackup/main/TopBackup/dist/TopBackup.exe'
   WHERE VERSAO = 'X.X.X';
   ```

---

### Fluxo de Atualização Automática

1. App verifica tabela `VERSAO_APP` no MySQL
2. Compara versão local (`src/version.py`) com a mais recente no banco
3. Se houver versão mais nova, baixa de `URL_DOWNLOAD`
4. Aplica atualização e reinicia o app

---

## Status do Desenvolvimento

**Versão Atual:** 1.1.2
**Última Atualização:** 2026-04-30

### ✅ Implementado e Funcionando

**Core:**
- AppController (orquestrador central)
- BackupEngine (gbak → validação → ZIP → destinos)
- BackupScheduler (APScheduler com múltiplas agendas)
- Três tipos de backup: Versionado (V), Semanal (S), Único (U)
- **Suporte a múltiplos bancos de dados** (v1.0.9)
- **ServReplicacaoManager** - Gerencia ServReplicacao.exe automaticamente (v1.1.0) — **DESABILITADO em v1.1.2** (chamadas comentadas no `_ensure_startup_components`; código preservado para reativar)
- **StartupManager** - Gerencia atalhos no shell:startup (v1.1.0) — em v1.1.2 só cria atalho do TopBackup (não mais do ServReplicacao)

**Database:**
- FirebirdClient (leitura EMPRESA, AGENDA_BACKUP)
- MySQLClient (sync com servidor cloud, log de backups)
- SyncManager (sincronização bidirecional)

**Interface:**
- GUI completa (CustomTkinter)
- Setup Wizard (4 etapas: Firebird, MySQL, FTP, Resumo)
- System Tray com minimize/restore
- Diálogos: progresso, logs, configurações, agendas
- **Seleção de pasta Firebird** no Setup Wizard e Configurações

**Serviço Windows:**
- Instalação/desinstalação como serviço
- IPC via Named Pipes
- Auto-instalação em C:\TOPBACKUP

**Rede:**
- FTP Client (upload de backups, modo passivo, retry)
- Update Checker (verificação a cada 10min)

**Infraestrutura:**
- Logger rotativo (5 backups de 5MB)
- Retry com backoff exponencial
- Circuit Breaker
- Timeout protection (gbak=1h, DB=30s)

### 🔄 Em Progresso

(Nenhum item no momento)

### 📋 Pendente / Futuro

- [ ] Testes automatizados (0% cobertura)
- [ ] Funcionalidade de Restore
- [ ] Notificações por email
- [ ] Criptografia de backups
- [ ] Dashboard web de monitoramento
- [ ] API REST para integração
- [ ] Suporte a cloud storage (S3, OneDrive)
- [ ] Agendamento avançado (exceções, feriados)

### 🐛 Bugs / Problemas Conhecidos

- fbclient.dll deve estar em `assets/firebird/x64/` ou `x86/`
- Credenciais MySQL em texto plano no config.json
- Paths com caracteres especiais podem causar issues
- Timeout de 1h para gbak pode não ser suficiente para DBs muito grandes

---

## Histórico de Sessões

### 2026-04-30
**v1.1.2: Desabilita inicialização automática do ServReplicacao**

**Problema:** Quando o `ServReplicacao.exe` está rodando, ele causa lentidão em outro sistema do cliente. O `_ensure_startup_components()` (introduzido na v1.1.0) iniciava o processo automaticamente e adicionava atalho no `shell:startup`, deixando o sync ligado a todo custo. Decisão: desabilitar temporariamente esse comportamento até o sync ser ajustado.

**Análise prévia (não pular nas próximas revisões):**

1. **Mapa do código antigo do ServReplicacao** — sustentação do entendimento:
   - `src/core/serv_replicacao_manager.py:34` `get_exe_path()` → calcula caminho do exe a partir do banco (ex.: `C:\GESTOR\Dados\DADOS.FDB` → `C:\GESTOR\ServReplicacao.exe`)
   - `src/core/serv_replicacao_manager.py:59` `is_running()` → `tasklist /fi "imagename eq ServReplicacao.exe"`
   - `src/core/serv_replicacao_manager.py:207` `start()` → `subprocess.Popen` com `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`, depois fecha janela via WM_SYSCOMMAND
   - `src/core/serv_replicacao_manager.py:435` `ensure_running()` → orquestra is_running → download (Google Drive ID `14wiP2IJLiqI_0BRuzSClrrUg1Yfrll-P`) → start
   - `src/core/startup_manager.py:75` `create_shortcut()` → PowerShell + WScript.Shell, gera `.lnk` em `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
   - `src/core/startup_manager.py:195` `ensure_servreplicacao_shortcut()` → cria atalho do ServReplicacao
   - `src/core/startup_manager.py:224` `ensure_all_shortcuts(servreplicacao_path=None)` → cria atalho TopBackup; só cria do ServReplicacao **se** o path for passado
   - **Único call site:** `src/core/app_controller.py:489` `_ensure_startup_components()` → roda em thread daemon a partir de `start()` (linha 301)

2. **Auto-update — fluxo independente do ServReplicacao** (continua funcionando 100%):
   - `app_controller.py:296-298` chama `_check_and_apply_update()` se `auto_update == True`
   - `update_checker.py:37` `check_for_updates()` → `MySQLClient.get_latest_version()` lê `VERSAO_APP` (ordena por DATA_LANCAMENTO DESC)
   - `update_checker.py:53-56` compara via `packaging.version.parse` — só baixa se `remote > current`. **Implicação:** URLs de versões antigas no banco com tokens vencidos NÃO são usadas; só importa o registro mais novo
   - `update_checker.py:115-216` `apply_update()` gera dinamicamente um `update.bat` que mata o processo, faz backup do exe antigo, copia o novo, reinicia
   - **Pré-requisito crítico do auto-update:** atalho do TopBackup precisa continuar no Startup — por isso só comentamos o pedaço do ServReplicacao, mantemos `ensure_topbackup_shortcut()`

**Solução implementada:** Comentar (não deletar) o bloco que chama `ServReplicacaoManager.ensure_running()` em `_ensure_startup_components()` e remover o argumento `serv_exe_path` da chamada de `StartupManager.ensure_all_shortcuts()`. Como `ensure_all_shortcuts(servreplicacao_path=None)` pula o branch do ServReplicacao internamente (`startup_manager.py:246`), o atalho do ServReplicacao deixa de ser criado. O atalho do TopBackup continua sendo criado (essencial para o auto-update).

**Decisões deliberadas (passivas, não destrutivas — confirmadas pelo usuário):**
- **Não remove** atalho `ServReplicacao.lnk` já existente no Startup (cliente/admin remove manualmente quando quiser).
- **Não mata** processo `ServReplicacao.exe` se já estiver rodando (cliente para manualmente / no próximo reboot).
- Código de `ServReplicacaoManager` e `ensure_servreplicacao_shortcut` mantido intacto no repositório.
- Imports de `ServReplicacaoManager` em `app_controller.py` mantidos (só as chamadas estão comentadas).

**Como reativar (quando o sync for corrigido):**
1. Em `src/core/app_controller.py`, no método `_ensure_startup_components()`, descomentar o bloco delimitado por `# === DESABILITADO em v1.1.2 ===`.
2. Trocar `startup_manager.ensure_all_shortcuts()` para `startup_manager.ensure_all_shortcuts(serv_exe_path)`.
3. Restaurar o docstring para mencionar `ServReplicacaoManager.ensure_running()` ativo.
4. Bumpar versão (ex.: `1.1.3`) e seguir processo de release abaixo.

**Token GitHub renovado e validado:** o token antigo embutido na `URL_DOWNLOAD` das versões anteriores (linhas v1.1.0 / v1.1.1 da `VERSAO_APP`) provavelmente expirou. Token novo lido do arquivo `GIT` na raiz do projeto (atenção: o nome do arquivo é apenas `GIT`, sem `@`, apesar do que o CLAUDE.md histórico chamava de `@GIT`). Validações feitas com `curl` antes do INSERT:

| Teste | Resultado |
|---|---|
| URL sem token | HTTP 404 → repo é privado |
| URL com token novo (HEAD) | HTTP 200, Content-Length 38.262.977, Content-Type `application/octet-stream`, ETag `b83d90ed...` |
| Range `bytes=0-4095` | HTTP 206 com 4096 bytes |
| HEAD após push | X-Cache MISS, Source-Age 3 → CDN refrescou |

**Fluxo de release executado:**

1. `src/version.py` → `VERSION = "1.1.2"`
2. `src/core/app_controller.py` → bloco ServReplicacao comentado em `_ensure_startup_components()`, docstring ajustado
3. `CLAUDE.md` → entrada desta sessão + atualização de "Versão Atual"
4. Build: `..\venv\Scripts\pyinstaller.exe topbackup.spec --noconfirm` → `dist/TopBackup.exe` regerado (38.262.977 bytes)
5. `git add` específico (4 arquivos), `git commit`, `git push origin main` (commit `41f5839`, depois reescrito sem co-autor)
6. Aguardado refresh do CDN raw.githubusercontent.com, re-validação via curl
7. **MySQL INSERT** em `dashboard.topsoft.cloud:3306` / DB `PROJETO_BACKUPS`:
   ```sql
   INSERT INTO VERSAO_APP (VERSAO, DATA_LANCAMENTO, URL_DOWNLOAD, CHANGELOG, OBRIGATORIA)
   VALUES ('1.1.2', NOW(), 'https://<TOKEN>@raw.githubusercontent.com/Tucciland/TopBackup/main/TopBackup/dist/TopBackup.exe',
           'Desabilita inicializacao automatica do ServReplicacao (estava causando lentidao em outro sistema). Auto-update e backups inalterados.', 'N');
   ```
   - Resultado: `ID=14`, `DATA_LANCAMENTO=2026-04-30 14:30:02`, `OBRIGATORIA=N`

**Schema de `VERSAO_APP`** (descoberto em probe — útil pra próximas releases):
- `ID` int PK auto_increment
- `VERSAO` varchar(20) UNIQUE NOT NULL
- `DATA_LANCAMENTO` datetime DEFAULT CURRENT_TIMESTAMP
- `URL_DOWNLOAD` varchar(500) NOT NULL
- `HASH_SHA256` varchar(64) NULL (não preenchemos; o `Downloader.download` aceita `None` e pula validação)
- `CHANGELOG` text NULL
- `OBRIGATORIA` char(1) DEFAULT 'N'

**Observação sobre o nome do arquivo do token:** o CLAUDE.md histórico se refere ao arquivo como `@GIT`, mas o arquivo real na raiz do projeto se chama apenas `GIT` (sem `@`). Os outros arquivos sensíveis seguem o padrão com `@` (`@BANCO__NUVEM`, `@BANCO_LOCAL`). Não renomeamos para não quebrar workflow do usuário.

**Credenciais MySQL nuvem (referência rápida — vêm de `@BANCO__NUVEM`):**
- Host: `dashboard.topsoft.cloud:3306`
- User: `user_sinc`
- Senha: armazenada em `@BANCO__NUVEM` (não documentar inline)
- Database: `PROJETO_BACKUPS`

**Arquivos modificados:**
- `src/core/app_controller.py` — bloco ServReplicacao comentado em `_ensure_startup_components()` (linhas 503-517 do estado pós-edição), docstring atualizado
- `src/version.py` — VERSION = "1.1.2"
- `dist/TopBackup.exe` — regerado via PyInstaller
- `CLAUDE.md` — esta entrada + atualização de "Versão Atual" e seção "Implementado e Funcionando"

**Verificação esperada nos clientes:**
- Logs no boot do app **não devem** mais conter linhas `ServReplicacao: ...`
- Logs **devem** continuar mostrando `Atalho TopBackup: OK` e `Verificando atualizações na inicialização...`
- Task Manager: `ServReplicacao.exe` não é iniciado pelo TopBackup (se já estava rodando, continua até reboot)
- `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`: `TopBackup.lnk` presente; nenhum `ServReplicacao.lnk` novo é criado

**Versão publicada no MySQL:** VERSAO_APP `ID=14`, v1.1.2

---

### 2026-02-25 (sessão 2)
**v1.1.1: Corrige erro firebird.msg em backups paralelos**

**Problema:** Quando dois backups estavam agendados para o mesmo horário (ex: 15:00), o backup do banco principal falhava com erro:
```
gbak falhou: can't format message 12:256 -- message file C:\Users\user\AppData\Local\Temp\1\_MEI84802\assets\firebird\x64\firebird.msg not found
```

**Causa:** O subprocess do `gbak` herdava a variável de ambiente `FIREBIRD` do PyInstaller, que apontava para o diretório temporário `_MEI84802`. Quando dois backups rodavam em paralelo, havia condição de corrida onde o diretório temporário podia ser alterado/limpo durante a execução.

**Solução:** Criar ambiente limpo para o subprocess, removendo a variável `FIREBIRD`:
```python
clean_env = os.environ.copy()
clean_env.pop('FIREBIRD', None)  # Remove variável FIREBIRD se existir
result = subprocess.run(cmd, ..., env=clean_env)
```

**Arquivo modificado:**
- `src/core/backup_engine.py` - Remove FIREBIRD do ambiente do subprocess gbak

**Commit:** `4ef99c2` - "fix: corrige erro firebird.msg not found em backups paralelos"

**Versão publicada no MySQL:** VERSAO_APP ID=13, v1.1.1

---

### 2026-02-25
**v1.1.0: ServReplicacao Manager e Startup Manager**

Implementado gerenciamento automático do ServReplicacao.exe e atalhos de inicialização do Windows.

**Novas funcionalidades:**

1. **ServReplicacaoManager** (`src/core/serv_replicacao_manager.py`):
   - Verifica se ServReplicacao.exe está rodando via `tasklist`
   - Calcula caminho do exe baseado no banco (ex: `C:\GESTOR\Dados\DADOS.FDB` → `C:\GESTOR\ServReplicacao.exe`)
   - Baixa do Google Drive se não existir (com tratamento de confirmação de vírus)
   - Inicia o processo silenciosamente (fecha janela automaticamente, vai para bandeja)
   - Usa API Windows (EnumWindows, WM_SYSCOMMAND) para fechar a janela após iniciar

2. **StartupManager** (`src/core/startup_manager.py`):
   - Gerencia atalhos na pasta `shell:startup` do Windows
   - Cria atalhos via PowerShell + WScript.Shell
   - Detecta atalhos existentes (ex: "TopBackup - Atalho") para evitar duplicatas
   - `ensure_topbackup_shortcut()` - Cria atalho para C:\TOPBACKUP\TopBackup.exe
   - `ensure_servreplicacao_shortcut()` - Cria atalho para ServReplicacao.exe

3. **Integração no AppController**:
   - Novo método `_ensure_startup_components()` executado em thread daemon no `start()`
   - Verifica ServReplicacao e atalhos na inicialização do app
   - Apenas loga resultados (não mostra pop-ups)

**Correções:**

1. **Empresa do banco secundário sincronizava com NULL**:
   - Campos `versao_local` e `data_ultima_interacao` não eram preenchidos
   - Corrigido em `_initialize_secondary_database()` para preencher antes de sincronizar

**Constantes adicionadas** (`src/config/constants.py`):
- `SERV_REPLICACAO_EXE` = "ServReplicacao.exe"
- `SERV_REPLICACAO_GOOGLE_DRIVE_ID` = "14wiP2IJLiqI_0BRuzSClrrUg1Yfrll-P"
- `TOPBACKUP_INSTALL_DIR` = r"C:\TOPBACKUP"
- `TOPBACKUP_EXE` = "TopBackup.exe"

**Arquivos criados:**
- `src/core/serv_replicacao_manager.py`
- `src/core/startup_manager.py`

**Arquivos modificados:**
- `src/config/constants.py` - Novas constantes
- `src/core/__init__.py` - Exports dos novos managers
- `src/core/app_controller.py` - Integração dos managers + correção banco secundário
- `src/version.py` - Versão 1.1.0

**Técnicas usadas para fechar janela do ServReplicacao:**
1. WM_SYSCOMMAND + SC_CLOSE (funcionou)
2. WM_CLOSE (fallback)
3. Alt+F4 simulado via keybd_event (fallback)

**Commit:** `b5a12ae` - "release: v1.1.0 - ServReplicacao Manager e Startup Manager"

**Versão publicada no MySQL:** VERSAO_APP ID=12, v1.1.0

---

### 2026-02-24
**v1.0.9: Suporte a Múltiplos Bancos de Dados**

Implementado suporte opcional a um segundo banco Firebird na configuração do app. Cada banco tem suas próprias rotinas e empresa. O app lê rotinas de ambos os bancos e agenda backups separadamente.

**Cenário de uso:**
- Cliente com Banco1 (Empresa A) e Banco2 (Empresa B)
- Configura Banco1 como principal e Banco2 como secundário (opcional)
- Rotinas do Banco1 vão para destinos configurados no Banco1
- Rotinas do Banco2 vão para destinos configurados no Banco2
- Dashboard mostra ambas as empresas separadamente

**Mudanças implementadas:**

1. **FirebirdConfig** - Adicionado `database_path_2` (campo opcional)
2. **MySQLClient** - Adicionado método `get_empresa_id_by_cnpj()`
3. **BackupEngine** - Usa `banco_origem` e `id_empresa` da agenda para determinar qual banco fazer backup
4. **BackupScheduler** - Usa `functools.partial` para associar agenda específica a cada job
5. **AppController** - Novos métodos:
   - `_initialize_secondary_database()` - Inicializa conexão com banco secundário
   - `_get_all_agendas_from_all_databases()` - Obtém agendas de todos os bancos
   - Callbacks modificados para aceitar `agenda` como parâmetro
6. **Setup Wizard** - Campo "Banco Secundário (Opcional)" na Etapa 1
7. **Configurações** - Campo "Banco Secundário" na aba Conexões
8. **config.json.example** - Campo `database_path_2` adicionado

**Arquivos modificados:**
- `src/config/settings.py` - Novo campo `database_path_2`
- `src/database/mysql_client.py` - Método `get_empresa_id_by_cnpj()`
- `src/core/backup_engine.py` - Usa banco_origem e id_empresa da agenda
- `src/core/scheduler.py` - Usa partial para associar agenda ao job
- `src/core/app_controller.py` - Suporte a segundo banco
- `src/gui/setup_wizard.py` - Campo banco secundário
- `src/gui/dialogs.py` - Campo banco secundário nas configurações
- `config/config.json.example` - Campo database_path_2

**Compatibilidade:** 100% retrocompatível. Se `database_path_2` estiver vazio, funciona igual à versão anterior.

**Correção de UI (mesma sessão):**
- Setup Wizard agora usa `CTkScrollableFrame` em todas as etapas
- Janela redimensionável com tamanho mínimo (500x400)
- Altura dinâmica (máximo 85% da tela)
- Botões de navegação sempre visíveis (altura fixa)
- Compatível com resoluções baixas (Windows Server)

**Interface Principal com Seletor de Banco:**
- Dropdown para selecionar qual banco visualizar (aparece se houver 2+ bancos)
- Status, agendas e logs filtrados pelo banco selecionado
- "Backup Agora" faz backup apenas do banco selecionado
- Backups automáticos continuam funcionando para todos os bancos

**Métodos adicionados no AppController:**
- `get_configured_databases()` - Lista bancos configurados
- `get_status_for_db(db_index)` - Status de um banco específico
- `get_agendas_for_db(db_index)` - Agendas de um banco específico
- `get_backup_logs_for_db(db_index)` - Logs de um banco específico
- `execute_backup_manual_for_db(db_index)` - Backup manual de um banco

**Correções adicionais (mesma sessão):**

1. **Correção do parsing de BANCO_ORIGEM:**
   - Campo `BANCO_ORIGEM` contém formato de conexão Firebird (ex: `localhost:C:\Dados\BANCO.FDB`)
   - Adicionado método `_extract_file_path()` no BackupEngine
   - Extrai caminho real do arquivo para verificação de existência
   - Regex: procura por `[A-Za-z]:[\\\/]...` no final da string

2. **Botão "Limpar Arquivo" funcional:**
   - Renomeado de "Limpar" para "Limpar Arquivo" (cor vermelha)
   - Agora limpa realmente o arquivo de log (com confirmação)
   - Adicionado método `clear_logs()` no Logger
   - Remove arquivo principal e backups (.log.1, .log.2, etc.)

3. **Limpeza automática de logs:**
   - Novo job diário às 03:00 que remove logs com mais de 30 dias
   - Adicionado método `cleanup_old_logs(days=30)` no Logger
   - Callback `_on_cleanup_logs()` no AppController
   - Configurado no BackupScheduler via `set_cleanup_logs_callback()`

4. **"Backup Agora" corrigido:**
   - Antes: Executava backup de TODAS as agendas do banco
   - Agora: Executa apenas UM backup usando a primeira agenda

**Build gerado:** TopBackup.exe (~38MB)

**Commit:** `59bd437` - "release: v1.0.9 - Suporte a múltiplos bancos de dados"

---

### 2026-02-23
**Correção de backups "travados" - Status E (executando) eterno**

**Problema:** Backups ficavam eternamente mostrando "em execução" (status='E') no painel, mesmo após concluídos. Causas identificadas:
1. App crashou ou PC desligou durante backup → registro fica com status='E' para sempre
2. Falha na atualização do status no MySQL (conexão perdida, etc.)

**Solução implementada:**

**1. Limpeza automática de backups órfãos (TopBackup):**
- Adicionado método `cleanup_orphan_backups()` no MySQLClient
- Limpeza executada em 2 momentos:
  - Na inicialização do app
  - A cada verificação de updates (periódica, a cada 10 min)
- Backups com status='E' há mais de 2 horas são marcados como falha
- Constante `ORPHAN_BACKUP_TIMEOUT_HOURS = 2` em constants.py

**2. Update de status com retry (TopBackup):**
- `update_log_backup()` agora tem retry automático (3 tentativas)
- Logs detalhados para debug do fluxo de atualização
- Verificação de log.id antes de tentar atualizar

**3. Dashboard limpo - removida seção "Travados":**
- Removido KPI de "Travados" (agora são apenas 6 KPIs)
- Removida seção de "Backups Travados" do dashboard
- Removidas funções, views e URLs relacionadas a travados
- Dashboard mostra apenas backups legítimos em execução

**Arquivos modificados (TopBackup):**
- `src/database/mysql_client.py` - Métodos de limpeza + retry no update
- `src/core/app_controller.py` - Limpeza na inicialização e verificação periódica
- `src/core/backup_engine.py` - Logs detalhados do fluxo de update
- `src/config/constants.py` - Nova constante ORPHAN_BACKUP_TIMEOUT_HOURS

**Arquivos modificados (DASHBOARD_CLIENTES/monitoramento_backup_topsoft):**
- `services.py` - Removidas funções de travados
- `views.py` - Removidas views de travados
- `urls.py` - Removidas URLs de travados
- `templates/.../dashboard.html` - Removida seção de travados, grid ajustado para 6 KPIs

**Commit:** `b913923` - "release: v1.0.8 - Corrige backups travados (status E eterno)"

**Versão publicada no MySQL:** VERSAO_APP ID=10, v1.0.8

---

### 2026-02-19
**v1.0.7: Remove notificação ao minimizar para bandeja**

- Removida notificação do Windows "Minimizado para a bandeja do sistema" ao fechar a janela
- App agora minimiza silenciosamente para o system tray sem exibir toast notification

**Arquivos modificados:**
- `src/gui/main_window.py` - Removida chamada `tray_icon.notify()` no método `_on_close()`
- `src/version.py` - Versão atualizada para 1.0.7

**Commit:** `6f3cdbd` - "release: v1.0.7 - Remove notificação ao minimizar para bandeja"

**Versão publicada no MySQL:** VERSAO_APP ID=9, v1.0.7

### 2026-02-12 (sessão 2 - tarde)
**v1.0.6: App silencioso - Remove notificações de backup**

- Removido bloco de notificação (`_notification_callback`) após backup em `app_controller.py`
- Pop-ups de "Backup Concluído" e "Falha no Backup" não aparecem mais
- Log continua registrando normalmente via `BackupEngine`
- Demais avisos do sistema permanecem inalterados (erros de inicialização, configurações salvas, etc.)

**Arquivos modificados:**
- `src/core/app_controller.py` - Removido bloco de notificação (linhas 252-263)
- `src/version.py` - Versão atualizada para 1.0.6

**Commit:** `7d8b18c` - "release: v1.0.6 - Remove notificações de backup (app silencioso)"

**Versão publicada no MySQL:** VERSAO_APP ID=8, v1.0.6

### 2026-02-12 (sessão 1 - manhã)
**Bug do gbak RESOLVIDO!** Backup funcionando corretamente no cliente ARMAZEM SANTO ANTONIO.

**Correções aplicadas (v1.0.5):**
1. **Comando gbak simplificado** - Usa lista de argumentos ao invés de string com shell
   - Antes: `f'"{gbak}" -b -v -user {user} -pas {pass} "{db}" "{fbk}"'` com `shell=True`
   - Agora: `[gbak, "-b", "-user", user, "-pass", password, db, fbk]` sem shell
2. **Removido -v (verbose)** - Não precisa de output detalhado
3. **Usando -pass** ao invés de -pas (compatibilidade)
4. **Removido ambiente complexo** - Sem variáveis FIREBIRD, TEMP customizadas
5. **Validação simplificada** - Removido `gbak -z`, só verifica tamanho do arquivo

**Nova funcionalidade: Seleção de pasta Firebird**
- Setup Wizard: Campo "Pasta do Firebird" ao invés de selecionar gbak.exe diretamente
- Configurações (aba Conexões): Mesmo campo adicionado
- Padrão: `C:\Program Files (x86)\Firebird\Firebird_2_5`
- gbak.exe detectado automaticamente em `pasta/bin/gbak.exe`
- Status visual (verde/laranja) mostrando se gbak foi encontrado

**Arquivos modificados:**
- `src/core/backup_engine.py` - Comando gbak simplificado, validação simples
- `src/gui/setup_wizard.py` - Campo pasta Firebird
- `src/gui/dialogs.py` - Campo pasta Firebird nas configurações
- `src/config/constants.py` - Caminho x86 como padrão

**Commit:** `9cd4141` - "fix: Simplifica comando gbak e adiciona seleção de pasta Firebird"

**Versão publicada no MySQL:** VERSAO_APP ID=7, v1.0.5

### 2026-02-11 (sessão 2 - tarde)
**Problema investigado:** gbak falha com "bad parameters on attach or create database" quando executado pelo TopBackup, mas funciona manualmente no CMD.

**Correções tentadas:**
1. Corrigido erro "firebird.msg not found" - remove variável FIREBIRD do ambiente do subprocess
2. Normaliza caminhos com `os.path.normpath()` para barras invertidas no Windows
3. Alterado diretório temp de `%TEMP%\1\topbackup_temp` (PyInstaller) para `C:\TOPBACKUP\temp`
4. Usa `shell=True` com aspas nos caminhos do comando gbak
5. Ambiente mínimo para subprocess (apenas SYSTEMROOT, PATH, FIREBIRD, TEMP, TMP)
6. Removidos flags `-g -ig` do comando gbak

**Resultado:** Ainda falhava. Resolvido na sessão de 2026-02-12.

### 2026-02-11 (sessão 1 - manhã)
- **v1.0.4**: Corrigido bug onde barra de progresso ficava carregando infinitamente após backup automático (agora esconde ao finalizar)

### 2026-02-11 (anterior)
- **v1.0.3**: Removidos pop-ups de atualização (versão disponível, download, erro) - mantido apenas no log
- Ajustado intervalo de verificação de atualizações de 6h para 10min (para testes)
- Adicionado campo CAMINHO_DESTINO2 na tabela LOG_BACKUPS para registrar ambos os destinos
- Atualizado modelo LogBackup, MySQLClient (insert/update/get) e BackupEngine
- Adicionada migração automática da coluna CAMINHO_DESTINO2 no ensure_schema

### 2026-02-10
- Documentação do estado atual do projeto no CLAUDE.md
- Análise completa de todos os módulos implementados

---

## Notas para Próxima Sessão

### Rotina Normal
1. Ler este arquivo para contexto
2. Verificar seção "Em Progresso" para tarefas iniciadas
3. Consultar "Pendente" para próximas features
4. Atualizar "Histórico de Sessões" ao final

### Possíveis Melhorias
- Adicionar testes automatizados (pytest)
- Implementar funcionalidade de Restore
- Criar dashboard web para monitoramento central
- Adicionar notificações por email em caso de falha
