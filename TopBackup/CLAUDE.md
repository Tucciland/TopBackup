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

**Versão Atual:** 1.0.7
**Última Atualização:** 2026-02-19

### ✅ Implementado e Funcionando

**Core:**
- AppController (orquestrador central)
- BackupEngine (gbak → validação → ZIP → destinos)
- BackupScheduler (APScheduler com múltiplas agendas)
- Três tipos de backup: Versionado (V), Semanal (S), Único (U)

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
