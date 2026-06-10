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

**Versão Atual:** 1.1.4
**Última Atualização:** 2026-06-10

### ✅ Implementado e Funcionando

**Core:**
- AppController (orquestrador central)
- BackupEngine (gbak → validação → ZIP → destinos)
- BackupScheduler (APScheduler com múltiplas agendas)
- Três tipos de backup: Versionado (V), Semanal (S), Único (U)
- **Suporte a múltiplos bancos de dados** (v1.0.9)
- **ServReplicacaoManager** - Gerencia ServReplicacao.exe automaticamente (v1.1.0) — desabilitado em v1.1.2; em v1.1.3 (pre-stage) volta condicional via flag `AppConfig.sync_replicacao_enabled` (default `True` = retoma comportamento de v1.1.0/v1.1.1; `False` = comportamento passivo de v1.1.2)
- **StartupManager** - Gerencia atalhos no shell:startup (v1.1.0) — recebe `serv_exe_path` apenas quando o toggle está habilitado em v1.1.3+

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

- **v1.1.5 — Redesign do frontend ("escuro refinado")**: planejado, **não iniciado** (adiado em 2026-06-10 para depois de validar a v1.1.4 em campo). Escopo, direção, mapa atual da GUI e plano de execução na seção **"Próxima Release Planejada — v1.1.5"** logo antes do Histórico de Sessões.

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

## Próxima Release Planejada — v1.1.5: Redesign do Frontend

**Status:** planejada, **NÃO iniciada**. Decisão de 2026-06-10: adiada para depois de validar a v1.1.4 em campo. Esta seção é a **fonte canônica** do plano (o plano detalhado original ficou em `~/.claude/plans/chat-atue-como-um-kind-falcon.md`, que pode não existir em sessões futuras).

**Motivação.** Feedback de que a interface "parece genérica / cara de IA" — hoje é o tema **escuro + azul padrão do CustomTkinter** sem personalização. Objetivo: repaginação visual total, **mantendo performance, usabilidade e rapidez**, com a regra dura de que **nada pode quebrar**.

**Direção escolhida pelo usuário: "escuro refinado".**
- Mantém o modo escuro, mas com paleta intencional: fundo grafite (ex. `#1a1a1a` / `#212121`), **cinzas reais em vez do azul padrão**, **1 cor de destaque marcante** (verde/âmbar) para ações e status, cards com contraste, hierarquia tipográfica clara.
- Meta: sumir com o "cara de template".

**Restrição técnica (não negociável): manter CustomTkinter.**
- Zero troca de framework (trocar p/ PyQt etc. = risco alto, quebraria tudo). A mudança é **cosmética**: paleta, tipografia, espaçamento, corner radius, hierarquia de cards — **sem alterar lógica nem a estrutura de layout** (só atributos `fg_color` / `text_color` / `hover_color` / `font` / `corner_radius`).

**Abordagem: centralizar o tema.**
- Criar **`src/gui/theme.py`** com constantes de cor e tamanhos de fonte (hoje espalhados/hardcoded). Vira o **único ponto de mudança** → baixo risco. Importar e usar nos 4 arquivos da GUI.

**Mapa atual da GUI (levantado em 2026-06-10 — base para o redesign):**
- Framework: **CustomTkinter 5.2.2** (`requirements.txt`). Tkinter-based, **sem QSS** — estilo via parâmetros por widget (`fg_color`, `text_color`, `hover_color`).
- Arquivos: `src/gui/main_window.py` (~691 linhas — dashboard/status/controles), `dialogs.py` (~691 — progresso, logs, configurações, agendas), `setup_wizard.py` (~720 — wizard 4 etapas), `tray_icon.py` (~144 — bandeja).
- **Tema global** setado em **`main_window.py:44-45`**: `ctk.set_appearance_mode("dark")` + `ctk.set_default_color_theme("blue")` ← ponto único do "azul padrão".
- **Cores hardcoded espalhadas** (alvos do `theme.py`): `#1f538d` (header azul do wizard, `setup_wizard.py`), `#c0392b` / `#a93226` (botão "Limpar Arquivo" vermelho, `dialogs.py`), e literais `green` / `orange` / `red` para status em `main_window.py` / `dialogs.py`.
- **Fontes inline**: `CTkFont(size=24/18/14/12/11, weight="bold")` em títulos/seções; `("Consolas", 11)` no log viewer.
- Layout: `pack` geometry; `CTkScrollableFrame` nos forms longos (wizard, configurações). **Não** existe módulo de tema/estilo central hoje → por isso o passo 1 é criar `theme.py`.

**Plano de execução (quando retomar):**
1. Criar `src/gui/theme.py` (paleta grafite + cor de destaque + escala de fontes + corner radius).
2. Definir destaque/modo via `theme.py` em vez do `set_default_color_theme("blue")`.
3. Reaplicar nos 4 arquivos da GUI, trocando cores/fontes literais pelas constantes — **sem tocar em lógica/layout**.
4. Smoke test visual: `python src/main.py` → percorrer dashboard, wizard (4 etapas), Configurações (4 abas), log viewer, bandeja. Conferir contraste/legibilidade.
5. Release **v1.1.5** pelo runbook padrão (bump `version.py` → build PyInstaller → commit/push **sem co-autor** → INSERT em `VERSAO_APP`).

---

## Histórico de Sessões

### 2026-06-10 — Release v1.1.4: fix "Banco não encontrado" no wizard + toggle ServReplicacao na instalação

**Contexto.** Clientes reportaram erro na instalação: na etapa 1 do Setup Wizard (seleção de Banco Principal/Secundário/Pasta Firebird), "Testar Conexão" retornava **"Conexão OK!"** mas ao clicar **"Próximo" aparecia "Banco não encontrado"**. O usuário lembrava de uma correção codada e não lançada — mas a verificação mostrou que **não estava aplicada**: as únicas mudanças não commitadas eram o bump `version.py` 1.1.3→1.1.4 e a **re-adição da senha MySQL hardcoded** em `setup_wizard.py` (mantida nesta release por decisão explícita do usuário, ver abaixo).

**Causa-raiz (confirmada lendo o código).** Divergência entre teste e validação no `setup_wizard.py`:
- `_test_firebird()` usa o driver `fdb`, que **aceita strings de conexão** (`localhost:C:\TOPSOFT\Dados\dados.fdb`) → conecta → "OK".
- `_validate_firebird()` fazia `os.path.exists(db_path)` **na string crua** → `os.path.exists("localhost:C:\...")` == `False` → "Banco não encontrado".

O utilitário que resolve isso **já existia** desde v1.0.9: `BackupEngine._extract_file_path()` (`backup_engine.py:66`, regex `([A-Za-z]:[\\\/].+)$`), usado em `_execute_gbak()` mas nunca ligado à validação do wizard.

**Mudanças aplicadas:**

1. **Fix `_validate_firebird()`** (`src/gui/setup_wizard.py`): import lazy de `BackupEngine`; extrai o caminho real via `_extract_file_path()` **antes** do `os.path.exists`. Agora "Testar Conexão" OK → "Próximo" avança, consistente com o que o gbak/backup já fazem. Banco secundário (`db_path_2`) não é validado no wizard (sem `os.path.exists`), então não tinha o bug — inalterado.

2. **Checkbox "Manter sincronização (ServReplicacao) ativa" na etapa 4 (Resumo)** (`src/gui/setup_wizard.py`): `_create_step4()` ganhou o checkbox (default marcado = ativo) ao lado de "Instalar como Serviço Windows"; `_finish()` persiste `self.settings.app.sync_replicacao_enabled = self.sync_replicacao_var.get()`. Reusa a config `AppConfig.sync_replicacao_enabled` (já existente desde v1.1.3, antes só na aba Geral de Configurações).

3. **Senha MySQL pré-preenchida (decisão do usuário).** A linha não commitada `mysql_pass_entry.insert(0, "51Ncr0n1z4d0r@2025@!@#")` (`setup_wizard.py`) foi **mantida** a pedido do usuário (instalação "just works", aceitando o trade-off de a senha ficar visível enquanto o repo está público). ⚠️ Isso reintroduz no repo público a credencial removida na v1.1.3. Revisitar quando o repo voltar a privado (o fix do downloader v1.1.3 já suporta auth via Bearer).

**Decisão de escopo:** a **repaginação total do frontend** (tema "escuro refinado") foi adiada para a **v1.1.5** (separar o redesign grande/arriscado do fix crítico). Plano gravado em `~/.claude/plans/chat-atue-como-um-kind-falcon.md` (Parte 5): criar `src/gui/theme.py` centralizando cores/fontes hoje espalhadas e reaplicar nos 4 arquivos da GUI sem mexer em lógica/layout.

**Smoke tests (todos passaram):**
- `py_compile` em `setup_wizard.py`, `backup_engine.py`, `settings.py`.
- `_extract_file_path`: `localhost:C:\...` → `C:\...`; `192.168.1.5/3050:C:\...` → `C:\...`; path puro inalterado; `""` → `""`.
- `Settings.save(p)/load(p)` persiste `sync_replicacao_enabled=False` e relê `False`; default da dataclass = `True`.

**Build/release:**
- Rebuild PyInstaller: `..\venv\Scripts\pyinstaller.exe topbackup.spec --noconfirm` → `dist/TopBackup.exe` 38.263.863 bytes, VERSION=1.1.4. Este exe é a mídia de instalação → instalações novas já saem em 1.1.4 (sem auto-update forçado no 1º boot, que vinha causando transtorno).
- `src/version.py` = 1.1.4.
- Commit + push (sem co-autor) + INSERT em `VERSAO_APP`.

**Arquivos modificados:**
- `TopBackup/src/gui/setup_wizard.py` (fix validação + checkbox ServReplicacao + persistência; senha hardcoded mantida)
- `TopBackup/src/version.py` (1.1.4)
- `TopBackup/CLAUDE.md` (esta entrada + "Versão Atual")
- `TopBackup/dist/TopBackup.exe` (rebuild)

**Ajuste pós-release (mesma sessão, ainda v1.1.4).** A pedido do usuário, os **dois** checkboxes da etapa Resumo passam a vir **marcados por padrão**: `service_var` (Instalar como Serviço Windows) mudou de `value=False` → `value=True` (antes só o ServReplicacao vinha marcado). Verificado que `run_as_service` é apenas preferência gravada no config (lido só em `dialogs.py`/`setup_wizard._finish`); **nada no app age sobre ele automaticamente** (instalação real do serviço exige admin + `--install`), então marcar por padrão não dispara nada nem quebra. Mantida a versão **1.1.4** (mudança é só default de checkbox do wizard, invisível para clientes já configurados): rebuild do exe + commit/push **sem** alterar `VERSAO_APP` (URL inalterada já serve o binário novo para instalações novas / clientes não atualizados). Clientes já em 1.1.4 não rebaixam nem reexecutam o wizard, então não são afetados.

---

### 2026-05-08 — Release v1.1.3 publicada (com fixes adicionais do `<senha>`)

**Contexto.** O pre-stage de 2026-05-02 (commit `641c043`) adicionou ao `main` o toggle ServReplicacao e o fix do downloader urllib3, mas a release agendada para segunda 2026-05-04 não foi executada. Hoje (sexta, 6 dias depois) ao retomar a release, um cliente em campo reportou erro `Erro de conexão MySQL: 1045 (28000): Access denied for user 'user_sinc'@'187.86.30.81'`. Investigação descobriu causa-raiz **não relacionada ao pre-stage**: o `git filter-repo --replace-text` da limpeza de credenciais (sessão 2026-04-30 sessão 2) substituiu a senha real `51Ncr0n1z4d0r@2025@!@#` por `<senha>` literal em `setup_wizard.py:314` e `config.json.example:15`. Pendência registrada na ocasião mas esquecida no pre-stage. Cliente que rodou Setup Wizard pós-2026-04-30 sem digitar senha real ficou com `"password": "<senha>"` no `config.json` → MySQL 1045 → app trava em "Erro de Inicialização".

**Diagnóstico via consulta ao MySQL** (rodada hoje com credenciais válidas daqui):
- 75 empresas cadastradas; 64 (85%) já em v1.1.2 saudáveis sincronizando hoje.
- 18 paradas há 2+ dias, mas só 2 mostram padrão consistente do bug `<senha>` (heartbeat e backup param na mesma data exata): **ITAMAR DE FREITAS** (parou 2026-04-30 18:00) e **CASA DE CARNES REZENDE** (parou 2026-05-04 12:07). Outros são clientes em versões antigas inativos ou casos de Firebird local quebrado (DROGARIA POPULAR sincroniza heart hoje mas backup parou 2026-03-04).
- Detalhe importante: **`SettingsDialog` não tinha campo de senha MySQL** (antes desta release), então cliente travado pelo bug não tinha caminho UI para corrigir — só Setup Wizard ou edição manual de JSON.

**Mudanças aplicadas nesta release** (escopo expandido vs pre-stage):

1. **Pre-stage de 2026-05-02 (commit `641c043`) — promovido sem alterações de código.** Toggle `sync_replicacao_enabled` (default `True`) em `AppConfig`/`app_controller`/`dialogs`/`config.json.example`; helper `_split_url_and_auth` em `network/downloader.py` aplicado a `download()` e `download_to_memory()` (Authorization Bearer header).

2. **Fix `<senha>` literal (NOVO):**
   - `src/gui/setup_wizard.py:314`: removida linha `mysql_pass_entry.insert(0, "<senha>")`; adicionado `placeholder_text="Digite a senha"` ao Entry.
   - `config/config.json.example:15`: `"password": "<senha>"` → `"password": ""`.

3. **Campo de senha MySQL no SettingsDialog (NOVO):** aba Conexões do dialog ganhou User/Senha/Database além do Host (que já existia). Recuperação de cliente travado agora possível via Configurações → Conexões → MySQL → digitar senha → Salvar (sem precisar refazer Setup Wizard inteiro). `_load_values` ignora password=`<senha>` (não pré-preenche placeholder); `_save` só sobrescreve password se campo foi preenchido (proteção contra apagar acidentalmente).

4. **Detecção amigável de credencial não-configurada (NOVO):** em `src/main.py` (`run_gui()`), antes da checagem `is_configured()`, novo bloco trata `settings.mysql.password in ("<senha>", "")` forçando `settings.app.first_run = True` → Setup Wizard abre automaticamente em vez do popup críptico de 1045. Cliente quebrado pelo bug agora se auto-recupera no próximo boot sem necessidade de visita técnica (desde que ele tenha v1.1.3 instalada — limitação: clientes em campo já travados em v1.1.2 não recebem auto-update porque MySQL falha antes do update_checker; precisam intervenção manual; ver lista abaixo).

5. **Bump:** `src/version.py` 1.1.2 → 1.1.3. Rebuild do PyInstaller. Commit + push.

6. **`VERSAO_APP` MySQL:** INSERT executado com URL embutindo token de `GIT` (raiz). Repo está público hoje, então auth via header Bearer é cosmética — mas continua funcionando se voltar a privado.

**Smoke tests pré-rebuild (todos passaram):**
- `Settings.load()` carrega sem erro com config.json existente.
- Detector main.py: `<senha>` e `""` retornam `True`; senha real retorna `False`.
- Downloader `_split_url_and_auth` regex ainda OK em 3 casos (URL com token, sem token, falso positivo de @ em path).
- `py_compile` OK em settings.py, dialogs.py, setup_wizard.py, main.py, downloader.py, app_controller.py.
- `config.json.example.mysql.password` carrega como `""` (vazio).

**Pendência: recuperação manual dos clientes travados em v1.1.2 com `<senha>`.** Clientes confirmados/suspeitos de estarem com config.json corrompido **NÃO recebem v1.1.3 via auto-update** (MySQL falha antes do update_checker rodar). Procedimento manual:

| Cliente | Status | Última sync | Ação sugerida |
|---|---|---|---|
| ITAMAR DE FREITAS (CNPJ 3091***0184) | suspeito do bug `<senha>` | 2026-04-30 18:00 | TeamViewer → editar `C:\TOPBACKUP\config\config.json` (`password` real) OU Setup Wizard novo |
| CASA DE CARNES REZENDE (CNPJ 3499***0156) | suspeito do bug `<senha>` | 2026-05-04 12:07 | idem |
| Cliente do print (IP 187.86.30.81) | confirmado 1045 | desconhecido | identificar e aplicar mesmo procedimento |

Demais 16 paradas há 2+ dias têm causas variadas (versões antigas inativas, Firebird local, PCs desligados). Não relacionados.

**Adoção em massa esperada (24h):** dos 64 ativos em v1.1.2, espera-se >90% migrarem para v1.1.3 no próximo ciclo de update (10 min). Os 8 em v1.1.1 e 1 em v1.0.9 dependem de PC voltar ao ar. Repo público alivia o bug do downloader urllib3 dessas versões antigas (não precisam auth real).

**Arquivos modificados nesta sessão:**
- `TopBackup/src/version.py` (bump 1.1.2 → 1.1.3)
- `TopBackup/src/gui/setup_wizard.py` (remove `<senha>` literal)
- `TopBackup/src/gui/dialogs.py` (adiciona User/Senha/Database MySQL na aba Conexões)
- `TopBackup/src/main.py` (detecção `<senha>`/vazia → força first_run)
- `TopBackup/config/config.json.example` (`password: ""`)
- `TopBackup/CLAUDE.md` (esta entrada + atualização "Versão Atual"/"Última Atualização")
- `TopBackup/dist/TopBackup.exe` (rebuild com VERSION=1.1.3)
- `TopBackup/RELEASE_v1.1.3.md` (apagado — runbook cumpriu papel)

---

### 2026-05-02 — Pré-stage de v1.1.3: toggle ServReplicacao + fix downloader urllib3

**Objetivo da sessão.** Reintroduzir, de forma controlada por checkbox, o gerenciamento automático do `ServReplicacao.exe` que foi desabilitado em v1.1.2 — com **default = habilitado** (volta ao comportamento de v1.1.0/v1.1.1) e opção de desligar via UI quando o cliente preferir o comportamento passivo. Aproveitar a release para resolver a pendência do bug do downloader (urllib3 2.x removeu propagação automática de credenciais embutidas em URL).

**Restrição operacional.** Os apps em campo (v1.1.2) NÃO podem atualizar hoje — release efetiva planejada para segunda-feira (2026-05-04). Estratégia confirmada com o usuário: **pre-stage hoje** (commit + push + rebuild do exe **mantendo `version.py` em 1.1.2**); na segunda, **bump para 1.1.3 + rebuild + commit + push + INSERT em `VERSAO_APP`**. Como o auto-update compara `pkg_version.parse(remoto) > pkg_version.parse(local)` e ninguém vai inserir 1.1.3 no MySQL hoje, a comparação `1.1.2 > 1.1.2 == False` garante zero atualizações em campo.

**Mudanças aplicadas (commit `641c043`):**

1. **`src/config/settings.py`** — `AppConfig.sync_replicacao_enabled: bool = True` adicionado entre `auto_update` e `empresa_id`. Compatibilidade automática via default da dataclass: cliente v1.1.2 atualizando para v1.1.3 não tem o campo no `config.json`, então recebe `True` ao carregar (volta ao comportamento pré-v1.1.2 — exatamente o que o usuário decidiu).

2. **`src/core/app_controller.py`** — `_ensure_startup_components()` (linhas 489-540) descomentado e wrappeado:
   ```python
   serv_exe_path = None
   if self.settings.app.sync_replicacao_enabled:
       serv_manager = ServReplicacaoManager(self.settings)
       serv_exe_path = serv_manager.get_exe_path()
       success, msg = serv_manager.ensure_running()
       ... log ...
   else:
       self.logger.info("ServReplicacao desabilitado por configuração")
   results = startup_manager.ensure_all_shortcuts(serv_exe_path)
   ```
   Quando flag = `False`, `ensure_all_shortcuts(None)` pula internamente o atalho do ServReplicacao (`startup_manager.py:246`). Decisão deliberada: **NÃO matar processo nem remover atalho existente** quando a flag passa de `True` → `False`; cliente decide manualmente. Mantém princípio passivo da v1.1.2.

3. **`src/gui/dialogs.py`** — checkbox "Manter sincronização (ServReplicacao) ativa" na **aba Geral** (escolha do usuário, junto com `auto_update` e `start_minimized`), seguindo o padrão dos toggles existentes (`BooleanVar` → `CTkCheckBox` → `_load_values` → `_save`).

4. **`config/config.json.example`** — campo `"sync_replicacao_enabled": true` documentado na seção `app`.

5. **`src/network/downloader.py` (fix v1.1.3)** — helper `_split_url_and_auth(url)` extrai token de URLs `https://TOKEN@host/...` via regex `^(https?)://([^@/\s]+)@(.+)$` e retorna `(clean_url, {Authorization: Bearer TOKEN})`. Aplicado em `download()` e `download_to_memory()`. Permite voltar repo a privado no futuro sem quebrar auto-update. Solução validada em 4 cenários (URL com token, sem token, http puro, `@` em path como falso positivo).

**Smoke tests rodados (todos passaram):**

| Cenário | Resultado |
|---|---|
| `AppConfig()` default | `sync_replicacao_enabled = True` ✅ |
| `Settings.load()` em JSON sem o campo | fallback automático para `True` ✅ |
| `Settings.load()` em JSON com `False` | respeita o valor ✅ |
| `Settings.save()` persiste o campo | ✅ |
| `_split_url_and_auth("https://ghp_xxx@raw.githubusercontent.com/...")` | clean_url + Bearer header ✅ |
| `_split_url_and_auth("https://raw.githubusercontent.com/...")` | URL inalterada, headers vazios ✅ |
| `_split_url_and_auth("https://example.com/path/with@symbol/file")` | sem extração (regex previne falso positivo) ✅ |

**Build/push de hoje:**

- `dist/TopBackup.exe` regerado via `..\venv\Scripts\pyinstaller.exe topbackup.spec --noconfirm` → 38.264.212 bytes
- `git push origin main` → commit `641c043` em `Tucciland/TopBackup`
- Validação: `curl -I https://raw.githubusercontent.com/Tucciland/TopBackup/main/TopBackup/dist/TopBackup.exe` → HTTP 200, ETag novo `0c3beda73a1eea6d147c5b7bc508a630299e30aa83a6ff7ab25d64127115aa8d`
- `src/version.py` permanece `VERSION = "1.1.2"` (intencional — ver "Restrição operacional" acima)
- Nenhum INSERT em `VERSAO_APP` no MySQL — última versão registrada continua sendo ID=14 (v1.1.2, 2026-04-30)

**Pendência: release v1.1.3 — segunda-feira (2026-05-04).** Runbook completo gravado em `RELEASE_v1.1.3.md` na raiz de `TopBackup/`. Inclui: bump version.py → rebuild → commit → push → aguardar CDN → INSERT no MySQL com token de `GIT`. O arquivo deve ser apagado após executada a release.

**Decisões deliberadas:**

- Flag em `AppConfig` (não em `BackupConfig`) — segue o padrão `auto_update`/`start_minimized` (comportamento de inicialização, não de backup).
- Nome em snake_case `sync_replicacao_enabled` (consistente com `auto_update`/`run_as_service`); rótulo de UI em português ("Manter sincronização (ServReplicacao) ativa").
- Default `True` em vez de `False` — usuário **mudou de ideia durante a conversa**: inicialmente queria default `False` (sem sync), depois decidiu `True` (volta ao comportamento "como funcionava antes").
- Fix do downloader **junto** com o toggle — aproveita o ciclo de release; alternativa de fazer só na v1.1.4 foi rejeitada pelo usuário ("Sim, junto com o toggle (Recomendado)").

**Risco residual mitigado:** entre hoje e segunda, o exe no GitHub (com VERSION=1.1.2 mas código novo) está acessível. Nenhum cliente vai baixá-lo porque a comparação de versão retorna `False`. Se precisar reverter antes de segunda: `git revert 641c043 && git push` (sem precisar tocar em MySQL).

**Arquivos modificados nesta sessão:**
- `TopBackup/src/config/settings.py`
- `TopBackup/src/core/app_controller.py`
- `TopBackup/src/gui/dialogs.py`
- `TopBackup/src/network/downloader.py`
- `TopBackup/config/config.json.example`
- `TopBackup/dist/TopBackup.exe` (rebuild)
- `TopBackup/CLAUDE.md` (esta entrada)
- `TopBackup/RELEASE_v1.1.3.md` (novo — runbook para segunda)

---

### 2026-04-30 (sessão 2) — Pós-release: bug do downloader, limpeza de credenciais, repo público

Após publicar v1.1.2, cliente reportou erro `Falha no download: Erro HTTP: 404` no auto-update. Investigação aprofundada levou a duas decisões importantes (bug do downloader + tornar repo público) e uma operação de limpeza/reescrita de histórico do git.

**Root cause do 404 no download (NÃO ÓBVIO — anotar pra próxima vez):**

- O `Downloader.download()` (`src/network/downloader.py:78`) usa `requests.get(url, stream=True)`. A URL armazenada em `URL_DOWNLOAD` da `VERSAO_APP` tem o token embutido: `https://TOKEN@raw.githubusercontent.com/...`.
- A versão de `requests==2.31.0` (e qualquer versão posterior) usa `urllib3>=2.0`, que por mudança de **segurança** removeu a extração automática de credenciais embutidas em URLs. O `Authorization` header **não é mais enviado** quando o token está na URL.
- `curl` extrai e envia (Basic Auth `TOKEN:`); `requests` não.
- Resultado: GitHub raw responde **404** em repos privados (sem auth = não encontrado).

**Confirmação experimental** (gravar pra debugging futuro):
```python
import requests
url = "https://ghp_XXX@raw.githubusercontent.com/owner/repo/main/file.exe"
r = requests.get(url)
# r.status_code == 404 em repo privado
# r.request.headers tem Authorization vazio

# Soluções que FUNCIONAM:
# requests.get(plain_url, headers={"Authorization": f"Bearer {token}"})
# requests.get(plain_url, headers={"Authorization": f"token {token}"})
# requests.get(plain_url, auth=(token, ""))
```

**Implicação grave:** todos os clientes que rodavam v1.1.0/v1.1.1 ficaram **presos** — o downloader deles tem o bug, então não conseguem baixar nem v1.1.2 nem qualquer versão futura enquanto a URL tiver token embutido em repo privado.

**Decisão estratégica:** tornar `Tucciland/TopBackup` **público**. Alternativa seria fix do downloader em v1.1.3 + update manual nos clientes presos, mas isso exigiria visita técnica em cada máquina. Tornar público destrava todo mundo de uma vez (URL sem auth real necessária funciona em repo público; o token embutido é simplesmente ignorado).

**Bugs/leaks descobertos durante preparação para público:**

1. **Senha MySQL hardcoded em 2 arquivos** (commitada desde v1.0.6):
   - `TopBackup/config/config.json.example:15` — `"password": "51Ncr0n1z4d0r@2025@!@#"`
   - `TopBackup/src/gui/setup_wizard.py:314` — `mysql_pass_entry.insert(0, "51Ncr0n1z4d0r@2025@!@#")  # Padrão TopSoft`
   - Decisão do usuário: NÃO trocar a senha do MySQL, apenas remover do repo.

2. **`.gitignore` quebrado**: listava `@GIT` mas o arquivo real é `GIT` (sem `@`). Token GitHub não estava sendo gitignored. Por sorte, nunca foi commitado (sempre untracked).

**Limpeza executada (em ordem):**

1. `git filter-repo --replace-text` substituindo `51Ncr0n1z4d0r@2025@!@#` por `<senha>` em **todos os blobs texto** dos 15 commits. Limpou `config.json.example` e `setup_wizard.py` em todo o histórico (textual).

2. **Rebuild do `dist/TopBackup.exe`** com PyInstaller, agora compilando do source limpo. O exe novo (38.262.441 bytes) não tem mais a senha embutida no PYZ.

3. **`.gitignore` corrigido**: adicionado `GIT` (sem `@`) na linha 41-43.

4. **Auditoria multi-camada** (working tree + histórico + binários `dist/`) — varreu PATs, AWS keys, Slack, Stripe, Google API, OpenAI, private keys, connection strings, JWT, CNPJs reais, emails. Tudo limpo exceto risco residual nos exes antigos:

5. **Risco residual identificado**: exes binários antigos (`dist/TopBackup.exe` em commits pré-rebuild) tinham a senha embutida no **PYZ comprimido** do PyInstaller. `git filter-repo --replace-text` não toca em binários, e zlib esconde a string de busca textual. Extração exigiria `pyinstxtractor` + `uncompyle6` — não trivial, mas viável.

6. **Decisão**: usuário autorizou apagar tudo dos commits antigos (`pode apagar oque for dos commits antigos, só manter o commit`). Solução escolhida: **squash completo do histórico**.

7. **Squash via `git checkout --orphan`**:
   ```bash
   git checkout --orphan main-clean
   git add -A
   git commit -m "TopBackup v1.1.2 — estado limpo (squash)"
   git branch -D main && git branch -m main
   git push --force origin main
   ```

8. **`git gc --aggressive --prune=now`**: reduziu `.git` local de **177 MB → 38 MB**.

**Estado final do repo (pré-tornar-público):**

- **1 único commit** em `main`: `968b316 TopBackup v1.1.2 — estado limpo (squash)`
- Zero senhas, tokens ou credenciais em qualquer lugar do repo (texto ou binário)
- `dist/TopBackup.exe` atual (limpo, 38 MB)
- `dist/TopBackup_update.exe` antigo (verificado limpo, é helper diferente sem `setup_wizard.py`)
- URL de download HTTP 200 com novo ETag — auto-update funcionará assim que o repo virar público

**Pendências futuras:**

1. **✅ RESOLVIDO em v1.1.3 (2026-05-08).** Implementado via helper `_split_url_and_auth` em `src/network/downloader.py`, aplicado em `download()` e `download_to_memory()`. Pre-staged em 2026-05-02 (commit `641c043`), promovido a release em 2026-05-08.

   Solução original sugerida: trocar `requests.get(url_com_token)` por:
   ```python
   import re
   m = re.match(r"https://([^@/]+)@(.+)", url)
   if m:
       token, rest = m.group(1), m.group(2)
       url = f"https://{rest}"
       headers = {"Authorization": f"Bearer {token}"}
   else:
       headers = {}
   response = requests.get(url, stream=True, timeout=60, headers=headers)
   ```
   Isso permite manter repo privado no futuro (auth via header funciona).

2. **✅ RESOLVIDO em v1.1.3 (2026-05-08).** `setup_wizard.py:314` agora apenas configura `placeholder_text="Digite a senha"` em vez de `insert(0, "<senha>")`. Bug confirmado em campo (cliente IP 187.86.30.81 reportou 1045) e mitigado: detecção em `main.py` força Setup Wizard se senha == `<senha>` ou vazia; SettingsDialog ganhou campo de senha MySQL para recuperação rápida via TeamViewer.

3. **✅ RESOLVIDO em v1.1.3 (2026-05-08).** `config.json.example:15` agora `"password": ""`.

4. **Voltar repo a privado (opcional)**: após confirmação que todos os clientes migraram para v1.1.3+ (com downloader fixo), pode tornar privado de novo. Verificar via query `SELECT versao_local, COUNT(*) FROM EMPRESA GROUP BY versao_local`.

**Comandos úteis pra próxima sessão:**

```bash
# Verificar adoção da v1.1.2 nos clientes
mysql -h dashboard.topsoft.cloud -u user_sinc -p PROJETO_BACKUPS -e \
  "SELECT VERSAO_LOCAL, COUNT(*) FROM EMPRESA GROUP BY VERSAO_LOCAL ORDER BY 2 DESC"

# Revalidar URL de download
curl -I "https://raw.githubusercontent.com/Tucciland/TopBackup/main/TopBackup/dist/TopBackup.exe"
```

**Lições gravadas:**

- **Sempre usar `Authorization` header** em vez de URL com token embutido pra repos privados. urllib3 2.x quebrou a forma antiga.
- **Nunca hardcode credenciais** em `.example` ou em código (mesmo "default da empresa").
- **Filter-repo `--replace-text` não toca em binários** — pra binários, squash do histórico é a única forma prática.
- **PyInstaller `--onefile` comprime PYZ com zlib** — `grep` direto no exe não acha strings literais, mas elas estão lá.
- **`.gitignore` precisa casar exatamente o nome do arquivo** (case-sensitive). `@GIT` ≠ `GIT`.

---

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

### Prioridade Atual (2026-06-10)
- **v1.1.5 — redesign do frontend "escuro refinado"**: próxima tarefa principal. Escopo, direção, mapa da GUI e plano completos na seção **"Próxima Release Planejada — v1.1.5"**. Manter CustomTkinter, criar `src/gui/theme.py`, **nada pode quebrar**.
- **Acompanhar adoção da v1.1.4** em campo: clientes saindo do bug "Banco não encontrado" no wizard. Última versão em `VERSAO_APP` = ID=17, v1.1.4 (2026-06-10). Query útil: `SELECT VERSAO_LOCAL, COUNT(*) FROM EMPRESA GROUP BY VERSAO_LOCAL ORDER BY 2 DESC`.
- **Lembrete fixo:** todos os commits/pushes **sem co-autor** (`Co-Authored-By`).

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
