# Documentacao do Banco de Dados - TopBackup

Este documento descreve a estrutura completa do banco de dados do sistema TopBackup, incluindo tabelas, colunas, relacionamentos e fluxos de dados. Utilize esta documentacao como referencia para desenvolver a pagina web de monitoramento.

---

## 1. Visao Geral da Arquitetura

O sistema utiliza uma arquitetura **hibrida** com dois bancos de dados:

| Banco | Tipo | Localizacao | Funcao |
|-------|------|-------------|--------|
| **MySQL** | Relacional | Cloud (`dashboard.topsoft.cloud:3306`) | Banco central de monitoramento e logs |
| **Firebird 2.5** | Relacional | Local (cliente) | Fonte dos dados de empresa e agendamentos |

### Fluxo de Dados
```
[Firebird Local]  -->  [Sync Manager]  -->  [MySQL Cloud]
   (Origem)              (Python)           (Destino)
```

---

## 2. Conexao MySQL Cloud

```
Host:     dashboard.topsoft.cloud
Porta:    3306
Database: PROJETO_BACKUPS
Usuario:  user_sinc
Charset:  utf8mb4_unicode_ci
```

---

## 3. Tabelas MySQL (Banco Central)

### 3.1 Tabela: `EMPRESA`

Armazena informacoes das empresas clientes. Cada empresa e identificada pelo CNPJ (unico).

| Coluna | Tipo | Chave | Restricao | Descricao |
|--------|------|-------|-----------|-----------|
| `ID` | INT | PK | AUTO_INCREMENT | Identificador unico |
| `ID_AUX` | INT | - | NULL | ID no sistema local Firebird |
| `FANTASIA` | VARCHAR(60) | - | NOT NULL | Nome fantasia da empresa |
| `RAZAO` | VARCHAR(60) | - | NOT NULL | Razao social |
| `CNPJ` | VARCHAR(18) | UNIQUE | NOT NULL | CNPJ formatado (XX.XXX.XXX/XXXX-XX) |
| `DATA_ULTIMA_INTERACAO` | DATETIME | - | NULL | Ultima vez que o app abriu ou fez backup |
| `VERSAO_LOCAL` | VARCHAR(20) | - | NULL | Versao do TopBackup instalado no cliente |
| `DATA_CADASTRO` | DATETIME | - | DEFAULT CURRENT_TIMESTAMP | Data de registro |
| `ATIVO` | CHAR(1) | INDEX | DEFAULT 'S' | Status ativo (S=Sim, N=Nao) |

**Indices:**
- `idx_cnpj` em `CNPJ` - Busca rapida por CNPJ
- `idx_ativo` em `ATIVO` - Filtro de empresas ativas

**Exemplo de registro:**
```sql
INSERT INTO EMPRESA (FANTASIA, RAZAO, CNPJ, VERSAO_LOCAL, ATIVO)
VALUES ('Loja Exemplo', 'Loja Exemplo LTDA', '12.345.678/0001-90', '1.0.3', 'S');
```

---

### 3.2 Tabela: `LOG_BACKUPS`

Historico completo de execucao de backups. Cada backup executado gera um registro nesta tabela.

| Coluna | Tipo | Chave | Restricao | Descricao |
|--------|------|-------|-----------|-----------|
| `ID` | INT | PK | AUTO_INCREMENT | Identificador unico |
| `ID_EMPRESA` | INT | FK | NOT NULL | Referencia para EMPRESA(ID) |
| `DATA_INICIO` | DATETIME | INDEX | NOT NULL | Data/hora inicio do backup |
| `DATA_FIM` | DATETIME | - | NULL | Data/hora fim do backup |
| `NOME_ARQUIVO` | VARCHAR(200) | - | NULL | Nome do arquivo gerado |
| `CAMINHO_DESTINO` | VARCHAR(500) | - | NULL | Caminho destino principal |
| `CAMINHO_DESTINO2` | VARCHAR(500) | - | NULL | Caminho destino secundario |
| `TAMANHO_BYTES` | BIGINT | - | NULL | Tamanho em bytes |
| `TAMANHO_FORMATADO` | VARCHAR(20) | - | NULL | Tamanho legivel (ex: "125 MB") |
| `STATUS` | CHAR(1) | INDEX | DEFAULT 'P' | Status do backup (ver codigos abaixo) |
| `MENSAGEM_ERRO` | TEXT | - | NULL | Mensagem de erro se falhou |
| `TIPO_BACKUP` | CHAR(1) | - | NULL | Tipo (V/S/U) |
| `ENVIADO_FTP` | CHAR(1) | - | DEFAULT 'N' | Enviado para FTP (S/N) |
| `DATA_ENVIO_FTP` | DATETIME | - | NULL | Quando foi enviado ao FTP |
| `MANUAL` | CHAR(1) | - | DEFAULT 'N' | Backup manual (S) ou agendado (N) |

**Chave Estrangeira:**
```sql
FOREIGN KEY (ID_EMPRESA) REFERENCES EMPRESA(ID) ON DELETE CASCADE
```

**Indices:**
- `idx_empresa` em `ID_EMPRESA`
- `idx_data` em `DATA_INICIO`
- `idx_status` em `STATUS`
- `idx_log_empresa_status` em `(ID_EMPRESA, STATUS)` - Composto

---

### 3.3 Tabela: `VERSAO_APP`

Gerenciamento de versoes do aplicativo para atualizacao automatica.

| Coluna | Tipo | Chave | Restricao | Descricao |
|--------|------|-------|-----------|-----------|
| `ID` | INT | PK | AUTO_INCREMENT | Identificador unico |
| `VERSAO` | VARCHAR(20) | UNIQUE | NOT NULL | Numero da versao (ex: "1.0.3") |
| `DATA_LANCAMENTO` | DATETIME | - | DEFAULT CURRENT_TIMESTAMP | Data de lancamento |
| `URL_DOWNLOAD` | VARCHAR(500) | - | NOT NULL | URL para download do .exe |
| `HASH_SHA256` | VARCHAR(64) | - | NULL | Hash para verificacao de integridade |
| `CHANGELOG` | TEXT | - | NULL | Notas da versao |
| `OBRIGATORIA` | CHAR(1) | - | DEFAULT 'N' | Atualizacao obrigatoria (S/N) |

**Indice:**
- `idx_versao` em `VERSAO`

---

## 4. Codigos de Status

### 4.1 Status de Backup (`LOG_BACKUPS.STATUS`)

| Codigo | Nome | Descricao | Cor Sugerida |
|--------|------|-----------|--------------|
| `P` | Pendente | Backup agendado, aguardando execucao | Cinza |
| `E` | Executando | Backup em andamento | Amarelo |
| `S` | Sucesso | Backup concluido com sucesso | Verde |
| `F` | Falha | Backup falhou | Vermelho |

### 4.2 Status Ativo (`EMPRESA.ATIVO`)

| Codigo | Descricao |
|--------|-----------|
| `S` | Empresa ativa no sistema |
| `N` | Empresa inativa/desabilitada |

### 4.3 Status FTP (`LOG_BACKUPS.ENVIADO_FTP`)

| Codigo | Descricao |
|--------|-----------|
| `S` | Arquivo enviado para servidor FTP |
| `N` | Nao enviado para FTP |

---

## 5. Tipos de Backup

O campo `TIPO_BACKUP` e `PREFIXO_BACKUP` define como o arquivo e nomeado:

| Codigo | Nome | Padrao do Nome | Exemplo | Comportamento |
|--------|------|----------------|---------|---------------|
| `V` | Versionado | CNPJ_YYYYMMDD_HHMMSS.zip | 12345678901234_20260211_230145.zip | Mantem multiplas versoes |
| `S` | Semanal | CNPJ_DIA.zip | 12345678901234_SEG.zip | Um arquivo por dia da semana |
| `U` | Unico | CNPJ.zip | 12345678901234.zip | Sempre sobrescreve o mesmo arquivo |

---

## 6. Views (Consultas Pre-definidas)

### 6.1 View: `vw_ultimos_backups`

Retorna o ultimo backup de cada empresa.

```sql
-- Colunas retornadas:
-- EMPRESA_ID, FANTASIA, CNPJ, DATA_INICIO, STATUS,
-- NOME_ARQUIVO, TAMANHO_FORMATADO, MENSAGEM_ERRO
```

**Uso na pagina de monitoramento:** Exibir dashboard com status atual de cada empresa.

### 6.2 View: `vw_status_empresas`

Dashboard de status das empresas mostrando "saude" da conexao.

```sql
-- Colunas retornadas:
-- Informacoes da empresa
-- Ultima interacao
-- Horas desde ultimo contato
-- Indicador de status (OK / ATENCAO / VERIFICAR)
```

**Logica de status:**
- **OK**: Contato nas ultimas 24 horas
- **ATENCAO**: Sem contato entre 24-48 horas
- **VERIFICAR**: Sem contato ha mais de 48 horas

---

## 7. Stored Procedure

### 7.1 `sp_relatorio_backups_mes(p_mes INT, p_ano INT)`

Gera relatorio mensal de backups por empresa.

**Parametros:**
- `p_mes`: Mes (1-12)
- `p_ano`: Ano (ex: 2026)

**Retorno:**
| Coluna | Descricao |
|--------|-----------|
| `FANTASIA` | Nome da empresa |
| `CNPJ` | CNPJ |
| `BACKUPS_SUCESSO` | Quantidade de backups com sucesso |
| `BACKUPS_FALHA` | Quantidade de backups com falha |
| `TOTAL_BACKUPS` | Total de backups no periodo |
| `TAMANHO_TOTAL_BYTES` | Soma dos tamanhos |
| `ULTIMO_BACKUP` | Data do ultimo backup |

**Exemplo de chamada:**
```sql
CALL sp_relatorio_backups_mes(2, 2026);
```

---

## 8. Relacionamentos

### Diagrama de Entidades

```
+------------------+          +------------------+
|     EMPRESA      |          |   VERSAO_APP     |
+------------------+          +------------------+
| PK: ID           |          | PK: ID           |
| CNPJ (unique)    |          | VERSAO (unique)  |
| FANTASIA         |          | URL_DOWNLOAD     |
| RAZAO            |          | DATA_LANCAMENTO  |
| DATA_ULTIMA_INT  |          | HASH_SHA256      |
| VERSAO_LOCAL     |          | CHANGELOG        |
| DATA_CADASTRO    |          | OBRIGATORIA      |
| ATIVO            |          +------------------+
+--------+---------+
         |
         | 1:N (uma empresa pode ter varios backups)
         |
+--------v---------+
|   LOG_BACKUPS    |
+------------------+
| PK: ID           |
| FK: ID_EMPRESA   |-----> EMPRESA.ID (ON DELETE CASCADE)
| DATA_INICIO      |
| DATA_FIM         |
| NOME_ARQUIVO     |
| CAMINHO_DESTINO  |
| CAMINHO_DESTINO2 |
| TAMANHO_BYTES    |
| TAMANHO_FORMATADO|
| STATUS           |
| MENSAGEM_ERRO    |
| TIPO_BACKUP      |
| ENVIADO_FTP      |
| DATA_ENVIO_FTP   |
| MANUAL           |
+------------------+
```

---

## 9. Queries Uteis para Monitoramento

### 9.1 Listar todas as empresas ativas
```sql
SELECT ID, FANTASIA, CNPJ, DATA_ULTIMA_INTERACAO, VERSAO_LOCAL
FROM EMPRESA
WHERE ATIVO = 'S'
ORDER BY FANTASIA;
```

### 9.2 Ultimos 10 backups de uma empresa
```sql
SELECT DATA_INICIO, DATA_FIM, NOME_ARQUIVO, TAMANHO_FORMATADO, STATUS, MENSAGEM_ERRO
FROM LOG_BACKUPS
WHERE ID_EMPRESA = ?
ORDER BY DATA_INICIO DESC
LIMIT 10;
```

### 9.3 Backups com falha nas ultimas 24 horas
```sql
SELECT e.FANTASIA, e.CNPJ, l.DATA_INICIO, l.MENSAGEM_ERRO
FROM LOG_BACKUPS l
JOIN EMPRESA e ON l.ID_EMPRESA = e.ID
WHERE l.STATUS = 'F'
AND l.DATA_INICIO >= NOW() - INTERVAL 24 HOUR
ORDER BY l.DATA_INICIO DESC;
```

### 9.4 Empresas sem backup ha mais de 24 horas
```sql
SELECT e.ID, e.FANTASIA, e.CNPJ, e.DATA_ULTIMA_INTERACAO,
       TIMESTAMPDIFF(HOUR, e.DATA_ULTIMA_INTERACAO, NOW()) as HORAS_SEM_CONTATO
FROM EMPRESA e
WHERE e.ATIVO = 'S'
AND (e.DATA_ULTIMA_INTERACAO IS NULL
     OR e.DATA_ULTIMA_INTERACAO < NOW() - INTERVAL 24 HOUR)
ORDER BY HORAS_SEM_CONTATO DESC;
```

### 9.5 Estatisticas gerais do dia
```sql
SELECT
    COUNT(CASE WHEN STATUS = 'S' THEN 1 END) as SUCESSO,
    COUNT(CASE WHEN STATUS = 'F' THEN 1 END) as FALHA,
    COUNT(CASE WHEN STATUS = 'E' THEN 1 END) as EXECUTANDO,
    COUNT(*) as TOTAL
FROM LOG_BACKUPS
WHERE DATE(DATA_INICIO) = CURDATE();
```

### 9.6 Taxa de sucesso por empresa (ultimo mes)
```sql
SELECT
    e.FANTASIA,
    e.CNPJ,
    COUNT(*) as TOTAL_BACKUPS,
    SUM(CASE WHEN l.STATUS = 'S' THEN 1 ELSE 0 END) as SUCESSO,
    ROUND(SUM(CASE WHEN l.STATUS = 'S' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as TAXA_SUCESSO
FROM EMPRESA e
LEFT JOIN LOG_BACKUPS l ON e.ID = l.ID_EMPRESA
WHERE l.DATA_INICIO >= NOW() - INTERVAL 30 DAY
GROUP BY e.ID, e.FANTASIA, e.CNPJ
ORDER BY TAXA_SUCESSO ASC;
```

### 9.7 Espaco total utilizado por empresa
```sql
SELECT
    e.FANTASIA,
    e.CNPJ,
    COUNT(l.ID) as TOTAL_ARQUIVOS,
    SUM(l.TAMANHO_BYTES) as BYTES_TOTAL,
    CONCAT(ROUND(SUM(l.TAMANHO_BYTES) / 1073741824, 2), ' GB') as TAMANHO_TOTAL
FROM EMPRESA e
LEFT JOIN LOG_BACKUPS l ON e.ID = l.ID_EMPRESA
WHERE l.STATUS = 'S'
GROUP BY e.ID, e.FANTASIA, e.CNPJ
ORDER BY BYTES_TOTAL DESC;
```

---

## 10. Tabelas Firebird (Origem Local)

O aplicativo TopBackup le dados das seguintes tabelas Firebird no cliente:

### 10.1 Tabela: `EMPRESA` (Firebird)

| Coluna | Descricao |
|--------|-----------|
| `CODIGO` ou `ID` | ID interno |
| `FANTASIA` | Nome fantasia |
| `RAZAO` ou `RAZAO_SOCIAL` | Razao social |
| `CNPJ` | CNPJ |
| `DATA_CADASTRO` | Data cadastro |

### 10.2 Tabela: `AGENDA_BACKUP` (Firebird)

| Coluna | Descricao |
|--------|-----------|
| `ID` | ID do agendamento |
| `HORARIO` | Hora do backup (ex: "23:00") |
| `DOM` | Domingo (S/N) |
| `SEG` | Segunda (S/N) |
| `TER` | Terca (S/N) |
| `QUA` | Quarta (S/N) |
| `QUI` | Quinta (S/N) |
| `SEX` | Sexta (S/N) |
| `SAB` | Sabado (S/N) |
| `LOCAL_DESTINO1` | Caminho principal |
| `LOCAL_DESTINO2` | Caminho secundario |
| `BACKUP_REMOTO` | Enviar FTP (S/N) |
| `PREFIXO_BACKUP` | Tipo (V/S/U) |
| `BANCO_ORIGEM` | Identificador do banco |

---

## 11. Fluxo de Sincronizacao

```
1. TopBackup inicia no cliente
        |
        v
2. Conecta no Firebird local
   - Le EMPRESA (dados da empresa)
   - Le AGENDA_BACKUP (agendamentos)
        |
        v
3. Sincroniza com MySQL Cloud
   - Cria/atualiza registro em EMPRESA
   - Atualiza DATA_ULTIMA_INTERACAO
   - Atualiza VERSAO_LOCAL
        |
        v
4. Agenda backup conforme AGENDA_BACKUP
        |
        v
5. No horario agendado:
   - Executa gbak (backup Firebird)
   - Compacta em ZIP
   - Copia para destinos
   - Registra em LOG_BACKUPS
        |
        v
6. Opcional: Envia para FTP
   - Atualiza ENVIADO_FTP = 'S'
   - Atualiza DATA_ENVIO_FTP
```

---

## 12. Consideracoes para a Pagina Web

### 12.1 Endpoints Sugeridos (API REST)

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/empresas` | Lista todas as empresas |
| GET | `/api/empresas/:id` | Detalhes de uma empresa |
| GET | `/api/empresas/:id/backups` | Historico de backups da empresa |
| GET | `/api/backups/recentes` | Ultimos backups (todas empresas) |
| GET | `/api/backups/falhas` | Backups com falha |
| GET | `/api/dashboard/stats` | Estatisticas gerais |
| GET | `/api/dashboard/alertas` | Empresas que precisam atencao |
| GET | `/api/relatorios/mensal` | Relatorio mensal |

### 12.2 Dashboard Principal

Elementos sugeridos:
1. **Cards de resumo**: Total empresas, backups hoje (sucesso/falha), alertas
2. **Grafico de pizza**: Distribuicao de status dos backups
3. **Lista de alertas**: Empresas sem backup ha X horas
4. **Tabela de ultimos backups**: Com status colorido
5. **Grafico de linha**: Backups por dia (ultimos 30 dias)

### 12.3 Pagina de Empresa

Elementos sugeridos:
1. Informacoes da empresa (nome, CNPJ, versao)
2. Status atual (ultima interacao, ultimo backup)
3. Historico de backups com paginacao
4. Grafico de taxa de sucesso
5. Espaco utilizado

### 12.4 Cores Sugeridas por Status

```css
/* Status de Backup */
.status-pendente   { background: #9E9E9E; } /* Cinza */
.status-executando { background: #FFC107; } /* Amarelo */
.status-sucesso    { background: #4CAF50; } /* Verde */
.status-falha      { background: #F44336; } /* Vermelho */

/* Alertas de Empresa */
.alerta-ok        { background: #4CAF50; } /* Verde - OK */
.alerta-atencao   { background: #FF9800; } /* Laranja - Atencao */
.alerta-critico   { background: #F44336; } /* Vermelho - Verificar */
```

---

## 13. Script de Criacao do Banco

O arquivo completo de criacao do schema MySQL esta em:
```
/TopBackup/scripts/setup_database.sql
```

Principais comandos:

```sql
CREATE DATABASE IF NOT EXISTS PROJETO_BACKUPS
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE PROJETO_BACKUPS;

-- Tabela EMPRESA
CREATE TABLE EMPRESA (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    ID_AUX INT NULL,
    FANTASIA VARCHAR(60) NOT NULL,
    RAZAO VARCHAR(60) NOT NULL,
    CNPJ VARCHAR(18) NOT NULL UNIQUE,
    DATA_ULTIMA_INTERACAO DATETIME NULL,
    VERSAO_LOCAL VARCHAR(20) NULL,
    DATA_CADASTRO DATETIME DEFAULT CURRENT_TIMESTAMP,
    ATIVO CHAR(1) DEFAULT 'S',
    INDEX idx_cnpj (CNPJ),
    INDEX idx_ativo (ATIVO)
);

-- Tabela LOG_BACKUPS
CREATE TABLE LOG_BACKUPS (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    ID_EMPRESA INT NOT NULL,
    DATA_INICIO DATETIME NOT NULL,
    DATA_FIM DATETIME NULL,
    NOME_ARQUIVO VARCHAR(200) NULL,
    CAMINHO_DESTINO VARCHAR(500) NULL,
    CAMINHO_DESTINO2 VARCHAR(500) NULL,
    TAMANHO_BYTES BIGINT NULL,
    TAMANHO_FORMATADO VARCHAR(20) NULL,
    STATUS CHAR(1) DEFAULT 'P',
    MENSAGEM_ERRO TEXT NULL,
    TIPO_BACKUP CHAR(1) NULL,
    ENVIADO_FTP CHAR(1) DEFAULT 'N',
    DATA_ENVIO_FTP DATETIME NULL,
    MANUAL CHAR(1) DEFAULT 'N',
    FOREIGN KEY (ID_EMPRESA) REFERENCES EMPRESA(ID) ON DELETE CASCADE,
    INDEX idx_empresa (ID_EMPRESA),
    INDEX idx_data (DATA_INICIO),
    INDEX idx_status (STATUS),
    INDEX idx_log_empresa_status (ID_EMPRESA, STATUS)
);

-- Tabela VERSAO_APP
CREATE TABLE VERSAO_APP (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    VERSAO VARCHAR(20) NOT NULL UNIQUE,
    DATA_LANCAMENTO DATETIME DEFAULT CURRENT_TIMESTAMP,
    URL_DOWNLOAD VARCHAR(500) NOT NULL,
    HASH_SHA256 VARCHAR(64) NULL,
    CHANGELOG TEXT NULL,
    OBRIGATORIA CHAR(1) DEFAULT 'N',
    INDEX idx_versao (VERSAO)
);
```

---

## 14. Migracoes Automaticas

O sistema aplica migracoes automaticamente ao conectar:

1. Adiciona coluna `MANUAL` se nao existir
2. Adiciona coluna `CAMINHO_DESTINO2` se nao existir
3. Renomeia `DATA_ULTIMA_ABERTURA` para `DATA_ULTIMA_INTERACAO`
4. Remove coluna obsoleta `ULTIMO_CONTATO`

---

## 15. Resumo Rapido

| Item | Valor |
|------|-------|
| **Banco Cloud** | MySQL 8.x |
| **Host** | dashboard.topsoft.cloud:3306 |
| **Database** | PROJETO_BACKUPS |
| **Tabela Principal** | EMPRESA |
| **Tabela de Logs** | LOG_BACKUPS |
| **Tabela de Versoes** | VERSAO_APP |
| **Charset** | utf8mb4_unicode_ci |
| **FK Principal** | LOG_BACKUPS.ID_EMPRESA -> EMPRESA.ID |
| **On Delete** | CASCADE |

---

*Documento gerado para uso no projeto de monitoramento web.*
*Ultima atualizacao: Fevereiro 2026*
