# Instalação

Guia completo pra instalar o TopBackup e o Dashboard.

---

## TopBackup (App Windows)

### Pré-requisitos

- Windows 10 ou 11
- Firebird 2.5 instalado (precisa do gbak.exe)
- Permissão de administrador (pra rodar como serviço)
- Conexão com internet (pra sincronizar com MySQL)

### Instalação Rápida

1. Baixa o `TopBackup.exe` da [release mais recente](https://github.com/seuuser/topbackup/releases)
2. Roda como administrador
3. Segue o wizard de configuração

O wizard tem 4 passos:

**Passo 1 - Firebird**
- Caminho do banco de dados (.FDB)
- Pasta do Firebird (onde tá o gbak.exe)
- Usuário e senha (padrão: SYSDBA / masterkey)

**Passo 2 - MySQL Cloud**
- Já vem preenchido com os dados padrão
- Só confirma

**Passo 3 - FTP (opcional)**
- Se quiser enviar backup pra servidor FTP
- Pode pular se não usar

**Passo 4 - Revisão**
- Confere tudo e finaliza

### Instalação Manual (se der pau no wizard)

Se o wizard não funcionar, você pode configurar manualmente:

1. Cria a pasta `C:\TOPBACKUP`
2. Copia o `TopBackup.exe` pra lá
3. Cria o arquivo `config\config.json`:

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
        "password": "sua_senha_aqui"
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
        "first_run": false,
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

4. Roda o `TopBackup.exe`

### Instalação como Serviço Windows

Pra rodar backup mesmo sem ninguém logado:

```bash
# Abre prompt como admin
cd C:\TOPBACKUP

# Instala o serviço
TopBackup.exe --install

# Inicia
TopBackup.exe --start

# Verifica se tá rodando
TopBackup.exe --status
```

O serviço fica configurado pra iniciar automaticamente com o Windows.

**Pra remover o serviço:**

```bash
TopBackup.exe --stop
TopBackup.exe --uninstall
```

### Verificando se tá funcionando

1. Abre o TopBackup
2. Confere se aparece o nome da empresa no card
3. Veja se tem próximo backup agendado
4. Faz um backup manual (botão "Backup Agora")
5. Confere no Dashboard se apareceu

---

## Dashboard (Django)

### Pré-requisitos

- Python 3.10 ou superior
- MySQL 8.0 (ou acesso ao banco PROJETO_BACKUPS)
- pip atualizado

### Instalação Local (Desenvolvimento)

```bash
# Clona o repositório
git clone https://github.com/seuuser/dashboard-clientes.git
cd dashboard-clientes

# Cria ambiente virtual
python -m venv venv

# Ativa (Windows)
venv\Scripts\activate

# Ativa (Linux/Mac)
source venv/bin/activate

# Instala dependências
pip install -r requirements.txt
```

### Configuração do .env

Cria um arquivo `.env` na raiz do projeto:

```env
# Django
SECRET_KEY=gera-uma-chave-aleatoria-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Banco de dados
DB_ENGINE=django.db.backends.mysql
DB_NAME=PROJETO_BACKUPS
DB_USER=user_sinc
DB_PASSWORD=sua_senha_aqui
DB_HOST=dashboard.topsoft.cloud
DB_PORT=3306
```

Pra gerar o SECRET_KEY:

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Rodando Migrations

```bash
python manage.py migrate
```

Se liga: as tabelas EMPRESA, LOG_BACKUPS e VERSAO_APP já existem no MySQL (criadas pelo TopBackup). O Django usa `managed = False` pra não mexer nelas.

### Iniciando o Servidor

```bash
# Desenvolvimento
python manage.py runserver

# Ou numa porta específica
python manage.py runserver 0.0.0.0:8080
```

Acessa `http://localhost:8000` e pronto.

### Deploy em Produção (Gunicorn)

```bash
# Instala Gunicorn
pip install gunicorn

# Coleta arquivos estáticos
python manage.py collectstatic

# Roda com Gunicorn
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

**Configuração Nginx (exemplo):**

```nginx
server {
    listen 80;
    server_name dashboard.seudominio.com;

    location /static/ {
        alias /path/to/dashboard/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Rodando com Systemd (Linux)

Cria `/etc/systemd/system/dashboard.service`:

```ini
[Unit]
Description=Dashboard Backup Monitoring
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/dashboard
Environment="PATH=/path/to/dashboard/venv/bin"
ExecStart=/path/to/dashboard/venv/bin/gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable dashboard
sudo systemctl start dashboard
```

---

## Troubleshooting de Instalação

### TopBackup não encontra o gbak.exe

**Problema:** Mensagem de erro sobre gbak não encontrado.

**Solução:** No wizard, clica em "Selecionar Pasta" e aponta pro diretório correto do Firebird. Geralmente é:
- `C:\Program Files\Firebird\Firebird_2_5\bin\`
- `C:\Program Files (x86)\Firebird\Firebird_2_5\bin\`

### TopBackup não conecta no MySQL

**Problema:** Erro de conexão com banco de dados.

**Soluções:**
1. Verifica se tem internet
2. Confere se as credenciais no config.json estão certas
3. Testa conexão: telnet dashboard.topsoft.cloud 3306

### Dashboard não mostra dados

**Problema:** Dashboard carrega mas não mostra empresas.

**Soluções:**
1. Verifica se o .env tá configurado certo
2. Confere se consegue conectar no MySQL
3. Roda `python manage.py shell` e testa:

```python
from monitoramento_backup_topsoft.models import Empresa
print(Empresa.objects.count())
```

Se retornar 0, o TopBackup ainda não sincronizou nenhuma empresa.
