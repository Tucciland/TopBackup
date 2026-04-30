-- TopBackup - Script de Criação do Banco MySQL
-- Execute este script no servidor MySQL para criar a estrutura necessária

-- Cria o banco de dados
CREATE DATABASE IF NOT EXISTS PROJETO_BACKUPS
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE PROJETO_BACKUPS;

-- ============================================
-- Tabela EMPRESA
-- Armazena informações das empresas clientes
-- ============================================
CREATE TABLE IF NOT EXISTS EMPRESA (
    ID                      INT AUTO_INCREMENT PRIMARY KEY,
    ID_AUX                  INT,                                  -- ID do sistema local
    FANTASIA                VARCHAR(60) NOT NULL,
    RAZAO                   VARCHAR(60) NOT NULL,
    CNPJ                    VARCHAR(18) NOT NULL UNIQUE,          -- UNIQUE evita duplicatas
    DATA_ULTIMA_INTERACAO   DATETIME,                             -- Atualizado na abertura do app e após backup
    VERSAO_LOCAL            VARCHAR(20),                          -- "1.0.5" formato string
    DATA_CADASTRO           DATETIME DEFAULT CURRENT_TIMESTAMP,
    ATIVO                   CHAR(1) DEFAULT 'S',
    INDEX idx_cnpj (CNPJ),
    INDEX idx_ativo (ATIVO)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Tabela LOG_BACKUPS
-- Registra histórico de backups realizados
-- ============================================
CREATE TABLE IF NOT EXISTS LOG_BACKUPS (
    ID                INT AUTO_INCREMENT PRIMARY KEY,
    ID_EMPRESA        INT NOT NULL,
    DATA_INICIO       DATETIME NOT NULL,
    DATA_FIM          DATETIME,
    NOME_ARQUIVO      VARCHAR(200),
    CAMINHO_DESTINO   VARCHAR(500),
    CAMINHO_DESTINO2  VARCHAR(500),
    TAMANHO_BYTES     BIGINT,                                   -- Suporta arquivos grandes
    TAMANHO_FORMATADO VARCHAR(20),
    STATUS            CHAR(1) NOT NULL DEFAULT 'P',             -- P=Pendente, E=Executando, S=Sucesso, F=Falha
    MENSAGEM_ERRO     TEXT,
    TIPO_BACKUP       CHAR(1),                                  -- V=Versionado, S=Semanal, U=Único
    ENVIADO_FTP       CHAR(1) DEFAULT 'N',
    DATA_ENVIO_FTP    DATETIME,
    FOREIGN KEY (ID_EMPRESA) REFERENCES EMPRESA(ID) ON DELETE CASCADE,
    INDEX idx_empresa (ID_EMPRESA),
    INDEX idx_data (DATA_INICIO),
    INDEX idx_status (STATUS)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Tabela VERSAO_APP
-- Gerencia versões do aplicativo para auto-update
-- ============================================
CREATE TABLE IF NOT EXISTS VERSAO_APP (
    ID              INT AUTO_INCREMENT PRIMARY KEY,
    VERSAO          VARCHAR(20) NOT NULL UNIQUE,
    DATA_LANCAMENTO DATETIME DEFAULT CURRENT_TIMESTAMP,
    URL_DOWNLOAD    VARCHAR(500) NOT NULL,
    HASH_SHA256     VARCHAR(64),
    CHANGELOG       TEXT,
    OBRIGATORIA     CHAR(1) DEFAULT 'N',
    INDEX idx_versao (VERSAO)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Inserir versões do aplicativo
-- ============================================
-- NOTA: A URL de download deve ser configurada diretamente no banco com o token de acesso GitHub
-- Formato: https://TOKEN@raw.githubusercontent.com/Tucciland/TopBackup/main/dist/TopBackup.exe
-- As versões são gerenciadas diretamente no banco MySQL (não neste script)

-- ============================================
-- Views úteis para monitoramento
-- ============================================

-- View: Últimos backups por empresa
CREATE OR REPLACE VIEW vw_ultimos_backups AS
SELECT
    e.ID AS EMPRESA_ID,
    e.FANTASIA,
    e.CNPJ,
    lb.DATA_INICIO,
    lb.STATUS,
    lb.NOME_ARQUIVO,
    lb.TAMANHO_FORMATADO,
    lb.MENSAGEM_ERRO
FROM EMPRESA e
LEFT JOIN LOG_BACKUPS lb ON e.ID = lb.ID_EMPRESA
WHERE lb.ID = (
    SELECT MAX(ID) FROM LOG_BACKUPS WHERE ID_EMPRESA = e.ID
)
ORDER BY lb.DATA_INICIO DESC;

-- View: Status das empresas
CREATE OR REPLACE VIEW vw_status_empresas AS
SELECT
    e.ID,
    e.FANTASIA,
    e.CNPJ,
    e.ATIVO,
    e.DATA_ULTIMA_INTERACAO,
    e.VERSAO_LOCAL,
    TIMESTAMPDIFF(HOUR, e.DATA_ULTIMA_INTERACAO, NOW()) AS HORAS_SEM_INTERACAO,
    CASE
        WHEN TIMESTAMPDIFF(HOUR, e.DATA_ULTIMA_INTERACAO, NOW()) <= 24 THEN 'OK'
        WHEN TIMESTAMPDIFF(HOUR, e.DATA_ULTIMA_INTERACAO, NOW()) <= 48 THEN 'ATENCAO'
        ELSE 'VERIFICAR'
    END AS STATUS_CONEXAO
FROM EMPRESA e
WHERE e.ATIVO = 'S'
ORDER BY e.DATA_ULTIMA_INTERACAO DESC;

-- ============================================
-- Stored Procedures
-- ============================================

-- Procedure: Relatório de backups do mês
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS sp_relatorio_backups_mes(IN p_mes INT, IN p_ano INT)
BEGIN
    SELECT
        e.FANTASIA,
        e.CNPJ,
        COUNT(CASE WHEN lb.STATUS = 'S' THEN 1 END) AS BACKUPS_SUCESSO,
        COUNT(CASE WHEN lb.STATUS = 'F' THEN 1 END) AS BACKUPS_FALHA,
        COUNT(*) AS TOTAL_BACKUPS,
        SUM(lb.TAMANHO_BYTES) AS TAMANHO_TOTAL_BYTES,
        MAX(lb.DATA_INICIO) AS ULTIMO_BACKUP
    FROM EMPRESA e
    LEFT JOIN LOG_BACKUPS lb ON e.ID = lb.ID_EMPRESA
        AND MONTH(lb.DATA_INICIO) = p_mes
        AND YEAR(lb.DATA_INICIO) = p_ano
    WHERE e.ATIVO = 'S'
    GROUP BY e.ID, e.FANTASIA, e.CNPJ
    ORDER BY e.FANTASIA;
END //
DELIMITER ;

-- ============================================
-- Índices adicionais para performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_log_empresa_status ON LOG_BACKUPS(ID_EMPRESA, STATUS);

-- ============================================
-- Fim do script
-- ============================================
SELECT 'Banco de dados PROJETO_BACKUPS criado com sucesso!' AS MENSAGEM;
