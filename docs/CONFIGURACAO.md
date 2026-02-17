# Configuração

Referência completa das configurações do TopBackup e Dashboard.

---

## TopBackup - config.json

O arquivo fica em `C:\TOPBACKUP\config\config.json`.

### Estrutura Completa

```json
{
    "firebird": {
        "database_path": "C:\\Dados\\BANCO.FDB",
        "gbak_path": "C:\\Program Files\\Firebird\\Firebird_2_5\\bin\\gbak.exe",
        "user": "SYSDBA",
        "password": "masterkey",
        "charset": "UTF8"
    },
    "mysql": {
        "host": "dashboard.topsoft.cloud",
        "port": 3306,
        "database": "PROJETO_BACKUPS",
        "user": "user_sinc",
        "password": "51Ncr0n1z4d0r@2025@!@#"
    },
    "ftp": {
        "host": "",
        "port": 21,
        "user": "",
        "password": "",
        "remote_path": "/backups",
        "passive_mode": true
    },
    "app": {
        "first_run": true,
        "run_as_service": false,
        "start_minimized": true,
        "auto_update": true,
        "empresa_id": null,
        "empresa_cnpj": ""
    },
    "backup": {
        "local_destino1": "C:\\Backups",
        "local_destino2": "",
        "backup_remoto": false,
        "prefixo_backup": "V",
        "compactar_zip": true,
        "verificar_backup": true
    }
}
```

---

## Seção: firebird

Conexão com o banco Firebird local.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `database_path` | string | Caminho completo do arquivo .FDB |
| `gbak_path` | string | Caminho do executável gbak.exe |
| `user` | string | Usuário do Firebird (geralmente SYSDBA) |
| `password` | string | Senha do Firebird |
| `charset` | string | Charset da conexão (UTF8 ou WIN1252) |

**Exemplo:**
```json
"firebird": {
    "database_path": "C:\\Dados\\TOPSOFT.FDB",
    "gbak_path": "C:\\Program Files\\Firebird\\Firebird_2_5\\bin\\gbak.exe",
    "user": "SYSDBA",
    "password": "masterkey",
    "charset": "UTF8"
}
```

Se liga: o `gbak_path` aponta pro executável do gbak, não pro diretório. Tipo: `C:\...\bin\gbak.exe`, não `C:\...\bin\`.

---

## Seção: mysql

Conexão com o MySQL na nuvem (PROJETO_BACKUPS).

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `host` | string | Endereço do servidor MySQL |
| `port` | int | Porta (padrão 3306) |
| `database` | string | Nome do banco (PROJETO_BACKUPS) |
| `user` | string | Usuário MySQL |
| `password` | string | Senha MySQL |

O TopBackup usa essa conexão pra:
- Sincronizar dados da empresa
- Gravar logs de backup
- Verificar atualizações

---

## Seção: ftp

Upload de backup pra servidor FTP (opcional).

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `host` | string | Endereço do servidor FTP |
| `port` | int | Porta (padrão 21) |
| `user` | string | Usuário FTP |
| `password` | string | Senha FTP |
| `remote_path` | string | Diretório remoto (ex: /backups) |
| `passive_mode` | bool | Usar modo passivo (recomendado) |

Se não usar FTP, deixa o `host` vazio e `backup_remoto` como false.

---

## Seção: app

Configurações gerais da aplicação.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `first_run` | bool | Indica se é primeira execução (abre wizard) |
| `run_as_service` | bool | Rodar como serviço Windows |
| `start_minimized` | bool | Iniciar minimizado na bandeja |
| `auto_update` | bool | Verificar atualizações automáticas |
| `empresa_id` | int/null | ID da empresa no MySQL (preenchido automaticamente) |
| `empresa_cnpj` | string | CNPJ da empresa (preenchido automaticamente) |

Os campos `empresa_id` e `empresa_cnpj` são preenchidos automaticamente na primeira sincronização. Não edita manualmente.

---

## Seção: backup

Configurações do processo de backup.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `local_destino1` | string | Diretório principal de destino |
| `local_destino2` | string | Diretório secundário (opcional) |
| `backup_remoto` | bool | Enviar pro FTP após backup |
| `prefixo_backup` | string | Tipo de backup: V, S ou U |
| `compactar_zip` | bool | Compactar em ZIP |
| `verificar_backup` | bool | Validar integridade do backup |

### Tipos de Backup (prefixo_backup)

| Valor | Nome | Arquivo Gerado | Quando usar |
|-------|------|----------------|-------------|
| `V` | Versionado | `12345678000199_20260215_230000.zip` | Histórico completo, uma versão por execução |
| `S` | Semanal | `12345678000199_SEX.zip` | Uma cópia por dia da semana (sobrescreve) |
| `U` | Único | `12345678000199.zip` | Sempre sobrescreve o mesmo arquivo |

**Versionado (V)** - Ideal pra quem quer histórico completo. Cada backup gera um arquivo novo com timestamp.

**Semanal (S)** - Mantém 7 arquivos (um por dia da semana). Bom pra economia de espaço mantendo uma semana de histórico.

**Único (U)** - Sempre sobrescreve. Usa menos espaço, mas só tem a última versão.

---

## AGENDA_BACKUP (Firebird)

Os horários de backup vêm da tabela AGENDA_BACKUP do Firebird local. O TopBackup lê e agenda automaticamente.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `HORARIO` | TIME | Horário do backup (HH:MM) |
| `DOM` a `SAB` | CHAR(1) | Dias ativos (S/N) |
| `LOCAL_DESTINO1` | VARCHAR | Sobrescreve config se preenchido |
| `LOCAL_DESTINO2` | VARCHAR | Sobrescreve config se preenchido |
| `BACKUP_REMOTO` | CHAR(1) | Enviar pro FTP (S/N) |
| `PREFIXO_BACKUP` | CHAR(1) | Tipo: V, S ou U |
| `BANCO_ORIGEM` | VARCHAR | Identificador do banco |

O lance é que você pode ter múltiplas agendas. Tipo: backup às 12h e às 23h, cada um com destino diferente.

---

## Dashboard - Django Settings

### Arquivo .env

```env
# Django
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=False
ALLOWED_HOSTS=dashboard.seudominio.com,localhost

# Banco de dados
DB_ENGINE=django.db.backends.mysql
DB_NAME=PROJETO_BACKUPS
DB_USER=user_sinc
DB_PASSWORD=sua_senha_aqui
DB_HOST=dashboard.topsoft.cloud
DB_PORT=3306
```

### Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SECRET_KEY` | Chave secreta Django | `django-insecure-xyz...` |
| `DEBUG` | Modo debug | `True` ou `False` |
| `ALLOWED_HOSTS` | Hosts permitidos | `localhost,dashboard.com` |
| `DB_ENGINE` | Engine do banco | `django.db.backends.mysql` |
| `DB_NAME` | Nome do banco | `PROJETO_BACKUPS` |
| `DB_USER` | Usuário | `user_sinc` |
| `DB_PASSWORD` | Senha | `...` |
| `DB_HOST` | Host | `dashboard.topsoft.cloud` |
| `DB_PORT` | Porta | `3306` |

### Database Routers

O Dashboard usa `managed = False` nos models. Isso significa que o Django não tenta criar ou alterar as tabelas - elas já existem e são gerenciadas pelo TopBackup.

```python
# monitoramento_backup_topsoft/models.py
class Empresa(models.Model):
    class Meta:
        managed = False
        db_table = 'EMPRESA'
```

Na real, o MySQL já tem as tabelas criadas. O Django só lê e exibe.

---

## Configurações de Produção

### settings.py para produção

```python
DEBUG = False
ALLOWED_HOSTS = ['dashboard.seudominio.com']

# HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

### Coletando arquivos estáticos

```bash
python manage.py collectstatic
```

### Usando WhiteNoise

O WhiteNoise serve arquivos estáticos sem precisar do Nginx:

```python
# settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Adiciona aqui
    # ...
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```
