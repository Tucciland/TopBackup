# Runbook: Release v1.1.3 (segunda-feira, 2026-05-04)

> **Objetivo.** Promover o pre-stage de 2026-05-02 (commit `641c043` em `main`) a release efetiva: bumpar `version.py` para `1.1.3`, regerar o exe com a versão nova embedada, publicar no MySQL e disparar auto-update nos clientes.
>
> **Pré-stage já feito** (não repetir). Os arquivos de código já estão no `main`:
> - Toggle `sync_replicacao_enabled` (default `True`) — `settings.py`, `app_controller.py`, `dialogs.py`, `config.json.example`.
> - Fix do downloader urllib3 (`_split_url_and_auth`) — `downloader.py`.
> - `dist/TopBackup.exe` no repo é o build de 2026-05-02 (com VERSION=1.1.2 ainda).
>
> **O que falta** (este runbook): bumpar VERSION → rebuild → commit → push → aguardar CDN → INSERT MySQL.
>
> **Importante.** Apagar este arquivo (`RELEASE_v1.1.3.md`) e atualizar `CLAUDE.md` ao final, marcando a release como concluída.

---

## 0. Pré-checks (3 minutos)

Rode estes comandos e confirme cada saída antes de prosseguir:

```bash
cd /c/Users/User/Desktop/Tucciland/PROJETO_BACKUP

# 0.1 — branch correto e working tree limpo
git status
# esperado: "On branch main", "nothing to commit, working tree clean"

# 0.2 — sincronizado com remote (sem commits novos do GitHub que você ainda não tem)
git fetch origin
git log --oneline origin/main..main
git log --oneline main..origin/main
# esperado: ambos os logs vazios

# 0.3 — último commit é o pre-stage de 2026-05-02
git log -1 --oneline
# esperado: 641c043 feat: toggle de sincronizacao (ServReplicacao) e fix downloader urllib3

# 0.4 — version.py ainda em 1.1.2
cat TopBackup/src/version.py | grep VERSION
# esperado: VERSION = "1.1.2"

# 0.5 — token do GitHub presente
test -f TopBackup/GIT && echo "token file presente" || echo "ERRO: arquivo GIT ausente"
# se ausente: gerar PAT novo no GitHub com escopo `repo` e salvar em TopBackup/GIT (uma linha, sem aspas)

# 0.6 — última versão no MySQL ainda é 1.1.2 (sanity)
# user lê/executa manualmente — apenas confirmar que ID mais recente em VERSAO_APP é ID=14, v1.1.2
```

**Se qualquer pré-check falhar, PARAR. Investigar antes de prosseguir.**

---

## 1. Bumpar versão (30 segundos)

```bash
cd /c/Users/User/Desktop/Tucciland/PROJETO_BACKUP
```

Editar **`TopBackup/src/version.py`** linha 5:

```python
VERSION = "1.1.3"
```

Validar:
```bash
cat TopBackup/src/version.py | grep VERSION
# esperado: VERSION = "1.1.3"
```

---

## 2. Atualizar CLAUDE.md (2 minutos)

Editar **`TopBackup/CLAUDE.md`** em três lugares:

**2.1 — linha "Versão Atual" (linha ~183):**

De:
```
**Versão Atual:** 1.1.2 *(v1.1.3 pré-staged em `main` — release prevista para 2026-05-04, ver `RELEASE_v1.1.3.md`)*
**Última Atualização:** 2026-05-02
```

Para:
```
**Versão Atual:** 1.1.3
**Última Atualização:** 2026-05-04
```

**2.2 — em "Histórico de Sessões", adicionar entrada nova ANTES de "### 2026-05-02":**

Modelo a seguir:

```markdown
### 2026-05-04 — Release v1.1.3 publicada

**Bumpa `version.py` para 1.1.3, rebuild, commit `<HASH>`, push, INSERT em `VERSAO_APP`.** Build do PyInstaller ficou com `<TAMANHO_BYTES>` bytes. Curl HEAD na URL raw retornou HTTP 200 com ETag novo `<ETAG>`. INSERT registrado como `ID=<ID>`, `DATA_LANCAMENTO=2026-05-04 <HH:MM:SS>`, `OBRIGATORIA='N'`. Comparação de versão nos clientes agora retorna `1.1.3 > 1.1.2 = True` → todos baixam o exe novo no próximo ciclo de update (10 min). Conteúdo já documentado na entrada de 2026-05-02 (toggle ServReplicacao + fix downloader); nada novo de código nesta release, apenas promoção do pre-stage.

**Validação pós-release:**
- [ ] `SELECT * FROM VERSAO_APP ORDER BY DATA_LANCAMENTO DESC LIMIT 1` retorna v1.1.3.
- [ ] Cliente de teste reinicia → log mostra `Atualização encontrada: 1.1.3` → download → restart → `version.py` local = 1.1.3.
- [ ] Cliente atualizado abre Configurações → aba Geral mostra checkbox "Manter sincronização (ServReplicacao) ativa" marcado por padrão.
- [ ] Cliente sem `sync_replicacao_enabled` no config.json antigo recebe `True` como default → ServReplicacao volta a ser gerenciado.

**Arquivo `RELEASE_v1.1.3.md` removido após release confirmada.**
```

Preencher `<HASH>`, `<TAMANHO_BYTES>`, `<ETAG>`, `<ID>`, `<HH:MM:SS>` após cada passo abaixo.

**2.3 — atualizar "Pendências futuras" da entrada 2026-04-30 (sessão 2)** (linha ~290 aproximadamente):

Adicionar **antes** do item "1. v1.1.3 — corrigir downloader.py":

```markdown
> **✅ RESOLVIDO em v1.1.3 (2026-05-04).** Implementação via helper `_split_url_and_auth` em `src/network/downloader.py`, aplicado em `download()` e `download_to_memory()`. Pre-staged em 2026-05-02 (commit `641c043`), promovido a release em 2026-05-04.
```

(Manter o texto original logo abaixo, como histórico do que foi feito.)

---

## 3. Rebuild do exe (2-3 minutos)

```bash
cd /c/Users/User/Desktop/Tucciland/PROJETO_BACKUP/TopBackup
../venv/Scripts/pyinstaller.exe topbackup.spec --noconfirm
```

Aguardar até ver `Build complete!`. Validar:

```bash
ls -la dist/TopBackup.exe
# esperado: tamanho ~38.2 MB, timestamp recente (de agora)

# confirmar que o exe novo tem VERSION=1.1.3 embutida (sem extração — só sanity)
# o arquivo é binário; trust the build. Validação real é nos clientes.
```

---

## 4. Commit + push (30 segundos)

```bash
cd /c/Users/User/Desktop/Tucciland/PROJETO_BACKUP

git add TopBackup/src/version.py TopBackup/dist/TopBackup.exe TopBackup/CLAUDE.md
# IMPORTANTE: NÃO adicionar TopBackup/RELEASE_v1.1.3.md ainda — vamos apagar esse arquivo no passo 8

git status
# esperado: 3 arquivos staged (version.py, TopBackup.exe, CLAUDE.md)

git commit -m "$(cat <<'EOF'
release: v1.1.3 - toggle ServReplicacao + fix downloader

Promove pre-stage de 2026-05-02 (commit 641c043) a release efetiva.
Bump version.py 1.1.2 -> 1.1.3, exe regerado com VERSION embutida nova.
Conteudo de codigo identico ao pre-stage; nada de novo nesta release
alem do bump + rebuild.

Apos push, aguardar refresh do CDN e executar INSERT em VERSAO_APP
no MySQL para disparar auto-update nos clientes.
EOF
)"
# IMPORTANTE: sem Co-Authored-By (preferencia do usuario)

git push origin main
```

Capturar o hash do commit:
```bash
git log -1 --oneline
# anotar: <HASH>  release: v1.1.3 - toggle ServReplicacao + fix downloader
```

---

## 5. Aguardar refresh do CDN (3-5 minutos)

O `raw.githubusercontent.com` tem cache CDN de até alguns minutos. Aguardar e validar:

```bash
# Polling até X-Cache MISS (CDN refrescou e tem o exe novo) ou ETag mudar
curl -sI "https://raw.githubusercontent.com/Tucciland/TopBackup/main/TopBackup/dist/TopBackup.exe" | grep -E "HTTP|ETag|Content-Length|X-Cache"
```

Esperado:
- `HTTP/1.1 200 OK`
- `Content-Length: <NUMERO>` (deve bater com `ls -la dist/TopBackup.exe`)
- `ETag: "<NOVO_HASH>"` (diferente do ETag de 2026-05-02 que era `0c3beda73a1eea6d147c5b7bc508a630299e30aa83a6ff7ab25d64127115aa8d`)
- `X-Cache: MISS` (nas primeiras vezes; depois HIT é OK)

Repetir o curl a cada 1 min até confirmar ETag novo. Anotar `<ETAG>` e `<TAMANHO_BYTES>` para o CLAUDE.md.

---

## 6. INSERT em VERSAO_APP no MySQL (1 minuto)

```bash
# Pegar token do arquivo
TOKEN=$(cat TopBackup/GIT | tr -d '[:space:]')
echo "Token (primeiros 10 chars): ${TOKEN:0:10}..."
# sanity: deve começar com ghp_ ou github_pat_

# Pegar credenciais MySQL do arquivo @BANCO__NUVEM
cat TopBackup/@BANCO__NUVEM
# Esperado: dashboard.topsoft.cloud:3306, user_sinc, <senha>, PROJETO_BACKUPS
```

Executar SQL no MySQL (use o cliente que preferir — `mysql` CLI, DBeaver, MySQL Workbench, etc.):

```sql
-- Conectar em dashboard.topsoft.cloud:3306, user_sinc, db PROJETO_BACKUPS

INSERT INTO VERSAO_APP (VERSAO, DATA_LANCAMENTO, URL_DOWNLOAD, CHANGELOG, OBRIGATORIA)
VALUES (
    '1.1.3',
    NOW(),
    'https://<TOKEN_AQUI>@raw.githubusercontent.com/Tucciland/TopBackup/main/TopBackup/dist/TopBackup.exe',
    'Toggle de sincronizacao (ServReplicacao) na aba Geral, default habilitado (volta ao comportamento de v1.1.0/v1.1.1). Fix downloader: Authorization header em vez de token na URL (urllib3 2.x).',
    'N'
);

-- Validação imediata
SELECT ID, VERSAO, DATA_LANCAMENTO, OBRIGATORIA FROM VERSAO_APP ORDER BY DATA_LANCAMENTO DESC LIMIT 3;
-- esperado: nova linha v1.1.3 no topo (ID > 14), seguida de v1.1.2 (ID=14), v1.1.1 (ID=13)
```

> **⚠️ Substituir `<TOKEN_AQUI>` pelo conteúdo de `TopBackup/GIT` literalmente.** A URL fica `https://ghp_xxxxx@raw.githubusercontent.com/...`. O fix do downloader em v1.1.3 já trata esse formato via `_split_url_and_auth`, então mesmo se o repo for fechado de novo no futuro, o auto-update continuará funcionando.

Anotar `<ID>` e `<HH:MM:SS>` da linha inserida para preencher o CLAUDE.md.

---

## 7. Validação end-to-end (5-10 minutos)

**7.1 — verificação remota (exe acessível com auth):**
```bash
TOKEN=$(cat TopBackup/GIT | tr -d '[:space:]')
curl -sI -H "Authorization: Bearer $TOKEN" "https://raw.githubusercontent.com/Tucciland/TopBackup/main/TopBackup/dist/TopBackup.exe" | head -5
# esperado: HTTP 200 (independente de o repo estar publico ou privado)
```

**7.2 — teste em cliente real (reboot ou aguardar 10 min):**

Em um cliente v1.1.2 conhecido:
- Reiniciar o TopBackup (fechar pela bandeja + abrir novamente).
- Abrir o log: `C:\TOPBACKUP\logs\topbackup.log`.
- Procurar por linha `Atualização encontrada: 1.1.3` → `Iniciando download da versão 1.1.3...` → `Download concluído` → `Atualização aplicada com sucesso - reiniciando aplicativo...`.
- Confirmar que o app reabre. Abrir Configurações → aba Geral → checkbox novo presente, marcado por padrão.

**7.3 — verificar adoção em massa (24h depois):**
```sql
SELECT VERSAO_LOCAL, COUNT(*) AS clientes
FROM EMPRESA
GROUP BY VERSAO_LOCAL
ORDER BY clientes DESC;
-- esperado em ~24h: maioria em '1.1.3'
```

---

## 8. Limpeza pós-release (1 minuto)

```bash
cd /c/Users/User/Desktop/Tucciland/PROJETO_BACKUP

# Remover este runbook (já cumpriu seu papel)
rm TopBackup/RELEASE_v1.1.3.md

# Atualizar CLAUDE.md com hash/etag/id reais coletados nos passos anteriores
# (já foi feito no passo 2.2, mas se ficou pendente algum campo, completar agora)

git add TopBackup/RELEASE_v1.1.3.md TopBackup/CLAUDE.md
git status
# esperado: 1 deletion (RELEASE_v1.1.3.md), 1 modification (CLAUDE.md, se faltavam campos)

git commit -m "$(cat <<'EOF'
chore: limpa runbook v1.1.3 e finaliza CLAUDE.md

Release v1.1.3 publicada com sucesso (ID=<ID> em VERSAO_APP).
Runbook RELEASE_v1.1.3.md cumpriu seu papel; remove do repo.
EOF
)"

git push origin main
```

---

## Plano de rollback

Se algo der errado **antes** do INSERT no MySQL (passos 1-5), o impacto é zero — basta reverter os commits:

```bash
git revert <HASH_DO_RELEASE> --no-edit
git push origin main
# clientes ficam parados em 1.1.2 (status quo); ninguem foi para 1.1.3 ainda
```

Se algo der errado **depois** do INSERT (passos 6+) e os clientes começarem a baixar uma versão problemática:

```sql
-- Marcar a versao como nao mais disponivel (pegar o ID correto)
UPDATE VERSAO_APP SET VERSAO = 'OFFLINE-1.1.3' WHERE VERSAO = '1.1.3';
-- ou simplesmente deletar
-- DELETE FROM VERSAO_APP WHERE VERSAO = '1.1.3';
```

Clientes que já atualizaram para 1.1.3 ficam em 1.1.3 (não há downgrade automático). Se for crítico, fazer hotfix v1.1.4 e nova entrada em VERSAO_APP.

---

## Cronograma sugerido

| Hora | Ação | Tempo estimado |
|---|---|---|
| 08:00 | Pré-checks (passo 0) | 3 min |
| 08:05 | Bump version + atualizar CLAUDE.md (passos 1-2) | 5 min |
| 08:10 | Rebuild PyInstaller (passo 3) | 3 min |
| 08:15 | Commit + push (passo 4) | 1 min |
| 08:16 | Aguardar refresh CDN (passo 5) | 5 min (passivo) |
| 08:25 | INSERT MySQL (passo 6) | 2 min |
| 08:30 | Validação inicial (passo 7.1, 7.2) | 10 min |
| 08:40 | Limpeza (passo 8) | 2 min |
| **Total** | | **~45 min** |

Validação de adoção em massa (passo 7.3) é assíncrona — checar em 24h.

---

## Notas

- **Sem `Co-Authored-By` em commits** — preferência registrada (`feedback_no_coauthor.md`).
- **Não usar `--no-verify`** — se hooks falharem, investigar antes de bypass.
- **Não force-push em main** — release usa fast-forward normal.
- O exe que está no `main` desde 2026-05-02 (commit `641c043`, 38.264.212 bytes) **NÃO** será o exe distribuído na release; o passo 3 regenera o exe agora com VERSION=1.1.3 embutida. Sem isso, clientes baixariam o exe atual e ficariam em loop infinito (versão remota MySQL=1.1.3 vs versão local exe=1.1.2 → baixa de novo → ainda 1.1.2 → ...).
