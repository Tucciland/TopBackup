# Troubleshooting

Deu pau? Olha aqui primeiro.

---

## TopBackup

### "gbak falhou: bad parameters on attach"

**Sintoma:** Backup falha com erro de parâmetros.

**Causa:** Isso acontecia nas versões anteriores a 1.0.5. O comando gbak tava sendo montado de forma errada.

**Solução:** Atualiza pro 1.0.5 ou superior. Essa versão simplificou o comando gbak:
- Usa lista de argumentos em vez de string com shell
- Removeu flag `-v` (verbose) que causava problemas
- Usa `-pass` em vez de `-pas`

Se ainda tiver problemas, verifica se:
1. O caminho do gbak.exe tá correto no config.json
2. O caminho do banco .FDB existe e tá acessível
3. Usuário e senha do Firebird estão certos

---

### Backup demora muito / timeout

**Sintoma:** Backup fica travado ou dá timeout após 1 hora.

**Causa:** Banco muito grande ou lento pra fazer backup.

**Soluções:**
1. O timeout padrão é 1 hora - pra maioria dos bancos é suficiente
2. Se o banco for muito grande (> 5GB), considera fazer backup em horário de baixo uso
3. Verifica se não tem transações travadas no Firebird:
   ```sql
   SELECT * FROM MON$TRANSACTIONS WHERE MON$STATE = 1
   ```

---

### Erro de DLL: fbclient.dll não encontrado

**Sintoma:** Aplicação não inicia, erro sobre fbclient.dll.

**Causa:** Firebird não tá instalado ou a DLL não tá no PATH.

**Soluções:**
1. Verifica se o Firebird 2.5 tá instalado
2. A DLL geralmente fica em:
   - `C:\Program Files\Firebird\Firebird_2_5\bin\fbclient.dll`
   - `C:\Program Files (x86)\Firebird\Firebird_2_5\bin\fbclient.dll`
3. Se precisar, copia a fbclient.dll pra pasta do TopBackup

---

### Não sincroniza com MySQL

**Sintoma:** Empresa não aparece no Dashboard, logs não são gravados.

**Causa:** Problemas de conexão com MySQL na nuvem.

**Soluções:**
1. Verifica se tem internet
2. Testa a conexão:
   ```bash
   telnet dashboard.topsoft.cloud 3306
   ```
3. Confere as credenciais no config.json seção `mysql`
4. Se tiver firewall, libera a porta 3306 pro host do MySQL

**Pra debugar:**
1. Abre o arquivo de log: `C:\TOPBACKUP\logs\topbackup.log`
2. Procura por erros de conexão MySQL
3. Se tiver "Access denied", a senha tá errada

---

### Backup executa mas arquivo fica com 0 bytes

**Sintoma:** Backup "sucesso" mas arquivo tá vazio.

**Causa:** gbak falhou silenciosamente.

**Soluções:**
1. Verifica se o banco não tá corrompido
2. Testa fazer backup manual:
   ```bash
   "C:\Program Files\Firebird\Firebird_2_5\bin\gbak.exe" -b -user SYSDBA -pass masterkey "C:\Dados\BANCO.FDB" "C:\Temp\teste.fbk"
   ```
3. Se der erro, o problema é no Firebird, não no TopBackup

---

### Serviço não inicia

**Sintoma:** `TopBackup.exe --start` não funciona.

**Causa:** Problema de permissão ou configuração.

**Soluções:**
1. Roda o prompt como administrador
2. Verifica se o serviço foi instalado:
   ```bash
   sc query TopBackupService
   ```
3. Se der erro, reinstala:
   ```bash
   TopBackup.exe --uninstall
   TopBackup.exe --install
   TopBackup.exe --start
   ```
4. Olha o Event Viewer do Windows pra ver o erro

---

### App trava na inicialização

**Sintoma:** Abre e fecha sozinho, ou fica na tela branca.

**Causa:** config.json corrompido ou inválido.

**Soluções:**
1. Abre o `C:\TOPBACKUP\config\config.json` num editor
2. Valida se é um JSON válido (usa jsonlint.com)
3. Se tiver corrompido, apaga e deixa o app recriar

---

## Dashboard

### Login não funciona

**Sintoma:** Credenciais não são aceitas.

**Causa:** django-axes bloqueou após muitas tentativas.

**Soluções:**
1. Reseta os bloqueios:
   ```bash
   python manage.py axes_reset
   ```
2. Ou reseta um usuário específico:
   ```bash
   python manage.py axes_reset_user admin
   ```

---

### Dashboard carrega mas dados não aparecem

**Sintoma:** Página carrega, mas sem cards de empresas.

**Causa:** Problema de conexão com banco ou dados não sincronizados.

**Soluções:**
1. Testa a conexão no shell:
   ```python
   python manage.py shell
   >>> from monitoramento_backup_topsoft.models import Empresa
   >>> Empresa.objects.count()
   ```
2. Se retornar 0, nenhum TopBackup sincronizou ainda
3. Se der erro de conexão, confere o .env

---

### Erro: "no such table" ou "doesn't exist"

**Sintoma:** Erro SQL sobre tabela que não existe.

**Causa:** Tabelas ainda não foram criadas no MySQL.

**Soluções:**
1. As tabelas são criadas pelo TopBackup na primeira execução
2. Se precisar criar manualmente:

```sql
CREATE TABLE EMPRESA (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    ID_AUX INT,
    FANTASIA VARCHAR(60) NOT NULL,
    RAZAO VARCHAR(60) NOT NULL,
    CNPJ VARCHAR(18) UNIQUE NOT NULL,
    DATA_ULTIMA_INTERACAO DATETIME,
    VERSAO_LOCAL VARCHAR(20),
    DATA_CADASTRO DATETIME DEFAULT CURRENT_TIMESTAMP,
    ATIVO CHAR(1) DEFAULT 'S'
);

CREATE TABLE LOG_BACKUPS (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    ID_EMPRESA INT NOT NULL,
    DATA_INICIO DATETIME NOT NULL,
    DATA_FIM DATETIME,
    NOME_ARQUIVO VARCHAR(200),
    CAMINHO_DESTINO VARCHAR(500),
    CAMINHO_DESTINO2 VARCHAR(500),
    TAMANHO_BYTES BIGINT,
    TAMANHO_FORMATADO VARCHAR(20),
    STATUS CHAR(1) DEFAULT 'P',
    MENSAGEM_ERRO TEXT,
    TIPO_BACKUP CHAR(1),
    ENVIADO_FTP CHAR(1) DEFAULT 'N',
    DATA_ENVIO_FTP DATETIME,
    MANUAL CHAR(1) DEFAULT 'N',
    FOREIGN KEY (ID_EMPRESA) REFERENCES EMPRESA(ID) ON DELETE CASCADE
);

CREATE TABLE VERSAO_APP (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    VERSAO VARCHAR(20) UNIQUE NOT NULL,
    DATA_LANCAMENTO DATETIME DEFAULT CURRENT_TIMESTAMP,
    URL_DOWNLOAD VARCHAR(500) NOT NULL,
    HASH_SHA256 VARCHAR(64),
    CHANGELOG TEXT,
    OBRIGATORIA CHAR(1) DEFAULT 'N'
);
```

---

### Status sempre "Verificar" mesmo com backup recente

**Sintoma:** Dashboard mostra empresa como "Verificar" mas teve backup hoje.

**Causa:** Timezone diferente entre TopBackup e Dashboard.

**Soluções:**
1. Confere se ambos usam America/Sao_Paulo
2. Verifica DATA_INICIO do último backup:
   ```sql
   SELECT * FROM LOG_BACKUPS WHERE ID_EMPRESA = X ORDER BY DATA_INICIO DESC LIMIT 1;
   ```
3. Se a hora tiver errada, ajusta o timezone do servidor

---

### AJAX não atualiza

**Sintoma:** Dashboard não atualiza automaticamente.

**Causa:** Erro JavaScript ou endpoint fora.

**Soluções:**
1. Abre o console do navegador (F12) e olha erros
2. Testa os endpoints manualmente:
   - `/api/status/`
   - `/api/cards/`
   - `/api/executando/`
3. Se der 500, olha o log do Django

---

## Logs Úteis

### TopBackup
```
C:\TOPBACKUP\logs\topbackup.log
```

### Django (desenvolvimento)
```
# Saída no terminal onde rodou runserver
```

### Django (produção)
```
# Depende de como configurou logging no settings.py
# Comum: /var/log/gunicorn/dashboard.log
```

---

## Precisa de mais ajuda?

1. Abre uma [issue](https://github.com/seuuser/topbackup/issues) com:
   - Versão do TopBackup
   - Versão do Windows
   - Mensagem de erro completa
   - Trecho relevante do log

2. Se for urgente, manda o arquivo de log completo (`topbackup.log`)
