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
- gbak command uses `-g -ig -pas` flags for complete backup compatibility
- APScheduler timezone is `America/Sao_Paulo`

---

## Status do Desenvolvimento

**Versão Atual:** 1.0.4
**Última Atualização:** 2026-02-11

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

**Serviço Windows:**
- Instalação/desinstalação como serviço
- IPC via Named Pipes
- Auto-instalação em C:\TOPBACKUP

**Rede:**
- FTP Client (upload de backups, modo passivo, retry)
- Update Checker (verificação a cada 6h, SHA256)

**Infraestrutura:**
- Logger rotativo (5 backups de 5MB)
- Retry com backoff exponencial
- Circuit Breaker
- Timeout protection (gbak=1h, DB=30s)

### 🔄 Em Progresso

- (nenhum item no momento)

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

### 2026-02-11
- **v1.0.4**: Corrigido bug onde barra de progresso ficava carregando infinitamente após backup automático (agora esconde ao finalizar)

### 2026-02-11
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

Ao retomar o desenvolvimento:
1. Ler este arquivo para contexto
2. Verificar seção "Em Progresso" para tarefas iniciadas
3. Consultar "Pendente" para próximas features
4. Atualizar "Histórico de Sessões" ao final
