# TopBackup + Dashboard

![Version](https://img.shields.io/badge/version-1.0.6-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![Django](https://img.shields.io/badge/django-6.0.1-green)
![License](https://img.shields.io/badge/license-MIT-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

Backup automático de bancos Firebird 2.5 com monitoramento centralizado via web.

Na real, é o seguinte: você instala o TopBackup no cliente, configura horário e destino, e pronto. Ele faz backup automático todo dia, sincroniza com a nuvem, e você acompanha tudo pelo Dashboard.

---

## Se liga no que faz

**TopBackup (App Windows)**
- Backup automático do Firebird 2.5 usando gbak nativo
- Agendamento flexível (múltiplos horários, dias específicos)
- Compactação ZIP com 3 modos: versionado, semanal ou único
- Cópia pra dois destinos locais + upload FTP
- Sincronização automática com MySQL na nuvem
- Roda como serviço Windows ou na bandeja do sistema
- Auto-update integrado

**Dashboard (Web Django)**
- Visão centralizada de todos os clientes
- Status em tempo real: OK, atenção, verificar, falha
- Histórico completo de backups
- Alertas visuais pra backups atrasados

---

## Quick Start

### TopBackup (no cliente)

```bash
# Baixa o .exe da release mais recente
# Roda como administrador
# Segue o wizard de 4 passos
```

O wizard configura:
1. Conexão com Firebird local
2. Sincronização MySQL (já vem preenchido)
3. FTP (opcional)
4. Revisão e pronto

Depois é só deixar rodando. Ele agenda os backups conforme a tabela AGENDA_BACKUP do Firebird.

### Dashboard (no servidor)

```bash
# Clone o repositório
git clone https://github.com/seuuser/dashboard-clientes.git
cd dashboard-clientes

# Cria ambiente virtual
python -m venv venv
venv\Scripts\activate

# Instala dependências
pip install -r requirements.txt

# Configura o .env
copy .env.example .env
# Edita com suas credenciais

# Roda migrations
python manage.py migrate

# Inicia
python manage.py runserver
```

Acessa `http://localhost:8000` e pronto.

---

## Estrutura do Projeto

```
PROJETO_BACKUP/
├── TopBackup/              # App Windows (Python/CustomTkinter)
│   ├── src/
│   │   ├── core/           # Lógica principal
│   │   ├── database/       # Conexões Firebird/MySQL
│   │   ├── gui/            # Interface gráfica
│   │   ├── service/        # Serviço Windows
│   │   └── network/        # FTP, updates
│   └── config/
│       └── config.json     # Configurações locais
│
└── DASHBOARD_CLIENTES/     # Web app Django
    ├── core/               # Settings Django
    └── monitoramento_backup_topsoft/
        ├── models.py       # Mapeamento MySQL
        ├── views.py        # Dashboard views
        └── services.py     # Lógica de negócio
```

---

## Documentação

| Doc | O que tem |
|-----|-----------|
| [Instalação](docs/INSTALACAO.md) | Passo a passo completo |
| [Configuração](docs/CONFIGURACAO.md) | Todas as opções do config.json |
| [Arquitetura](docs/ARQUITETURA.md) | Como funciona por baixo |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Deu erro? Olha aqui |
| [FAQ](docs/FAQ.md) | Perguntas frequentes |

---

## Requisitos

**TopBackup**
- Windows 10/11
- Firebird 2.5 instalado (precisa do gbak.exe)
- Acesso admin pra rodar como serviço

**Dashboard**
- Python 3.10+
- MySQL 8.0+
- Conexão com o banco PROJETO_BACKUPS

---

## Tipos de Backup

| Prefixo | Nome | Arquivo gerado | Uso típico |
|---------|------|----------------|------------|
| V | Versionado | `CNPJ_20260215_230000.zip` | Histórico completo |
| S | Semanal | `CNPJ_SEX.zip` | Uma cópia por dia da semana |
| U | Único | `CNPJ.zip` | Sempre sobrescreve |

---

## Stack Técnico

**TopBackup**
- Python 3.10+
- CustomTkinter (GUI moderna)
- APScheduler (agendamento)
- fdb 2.0.2 (Firebird)
- mysql-connector-python (MySQL)
- PyInstaller (compilação)

**Dashboard**
- Django 6.0.1
- MySQL 8.0
- Gunicorn (produção)
- WhiteNoise (arquivos estáticos)

---

## Contribuindo

Quer ajudar? Lê o [CONTRIBUTING.md](CONTRIBUTING.md).

Bugs e sugestões: abre uma [issue](https://github.com/seuuser/topbackup/issues).

---

## Licença

MIT - veja [LICENSE](LICENSE) pra detalhes.

---

## Changelog

Veja [CHANGELOG.md](CHANGELOG.md) pro histórico completo.

**Última versão: 1.0.6**
- App silencioso - removidas notificações de backup
- Fix crítico no comando gbak (v1.0.5)
