"""
TopBackup - Cliente MySQL
Conexão e operações com banco MySQL na nuvem
"""

import mysql.connector
from mysql.connector import Error as MySQLError
from typing import Optional, List, Tuple
from contextlib import contextmanager
from datetime import datetime

from .models import Empresa, LogBackup, VersaoApp
from ..config.settings import MySQLConfig
from ..utils.logger import get_logger
from ..utils.resilience import retry


class MySQLClient:
    """Cliente para conexão com banco MySQL na nuvem"""

    def __init__(self, config: MySQLConfig):
        self.config = config
        self.logger = get_logger()
        self._pool = None

    def _get_connection_params(self) -> dict:
        """Retorna parâmetros de conexão"""
        return {
            'host': self.config.host,
            'port': self.config.port,
            'database': self.config.database,
            'user': self.config.user,
            'password': self.config.password,
            'charset': 'utf8mb4',
            'connect_timeout': 30,
            'autocommit': False,
        }

    @contextmanager
    def get_connection(self):
        """Context manager para conexão com MySQL"""
        connection = None
        try:
            connection = mysql.connector.connect(**self._get_connection_params())
            yield connection
        finally:
            if connection and connection.is_connected():
                connection.close()

    @retry(max_attempts=3, delay=2.0, exceptions=(MySQLError,))
    def test_connection(self) -> Tuple[bool, str]:
        """
        Testa a conexão com o banco MySQL

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                return True, "Conexão bem-sucedida"
        except MySQLError as e:
            self.logger.error(f"Erro de conexão MySQL: {e}")
            return False, str(e)
        except Exception as e:
            self.logger.error(f"Erro inesperado MySQL: {e}")
            return False, str(e)

    # ============ EMPRESA ============

    def get_empresa_by_cnpj(self, cnpj: str) -> Optional[Empresa]:
        """Busca empresa pelo CNPJ"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                sql = """
                    SELECT ID, ID_AUX, FANTASIA, RAZAO, CNPJ,
                           DATA_ULTIMA_INTERACAO, VERSAO_LOCAL,
                           DATA_CADASTRO, ATIVO
                    FROM EMPRESA
                    WHERE CNPJ = %s
                """
                cursor.execute(sql, (cnpj,))
                row = cursor.fetchone()

                if row:
                    return Empresa(
                        id=row['ID'],
                        id_aux=row['ID_AUX'],
                        fantasia=row['FANTASIA'],
                        razao=row['RAZAO'],
                        cnpj=row['CNPJ'],
                        data_ultima_interacao=row['DATA_ULTIMA_INTERACAO'],
                        versao_local=row['VERSAO_LOCAL'],
                        data_cadastro=row['DATA_CADASTRO'],
                        ativo=row['ATIVO']
                    )
                return None

        except Exception as e:
            self.logger.error(f"Erro ao buscar empresa: {e}")
            return None

    def insert_empresa(self, empresa: Empresa) -> Optional[int]:
        """Insere nova empresa"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = """
                    INSERT INTO EMPRESA
                    (ID_AUX, FANTASIA, RAZAO, CNPJ, DATA_ULTIMA_INTERACAO,
                     VERSAO_LOCAL, ATIVO)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    empresa.id_aux,
                    empresa.fantasia,
                    empresa.razao,
                    empresa.cnpj,
                    datetime.now(),
                    empresa.versao_local,
                    empresa.ativo
                ))
                conn.commit()
                return cursor.lastrowid

        except Exception as e:
            self.logger.error(f"Erro ao inserir empresa: {e}")
            return None

    def update_empresa(self, empresa: Empresa) -> bool:
        """Atualiza dados da empresa"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = """
                    UPDATE EMPRESA SET
                        ID_AUX = %s,
                        FANTASIA = %s,
                        RAZAO = %s,
                        DATA_ULTIMA_INTERACAO = %s,
                        VERSAO_LOCAL = %s,
                        ATIVO = %s
                    WHERE ID = %s
                """
                cursor.execute(sql, (
                    empresa.id_aux,
                    empresa.fantasia,
                    empresa.razao,
                    datetime.now(),
                    empresa.versao_local,
                    empresa.ativo,
                    empresa.id
                ))
                conn.commit()
                return cursor.rowcount > 0

        except Exception as e:
            self.logger.error(f"Erro ao atualizar empresa: {e}")
            return False

    def sync_empresa(self, empresa: Empresa) -> Optional[int]:
        """Sincroniza empresa (insert ou update)"""
        existing = self.get_empresa_by_cnpj(empresa.cnpj)

        if existing:
            empresa.id = existing.id
            self.update_empresa(empresa)
            return existing.id
        else:
            return self.insert_empresa(empresa)

    # ============ LOG_BACKUPS ============

    def insert_log_backup(self, log: LogBackup) -> Optional[int]:
        """Insere novo log de backup"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = """
                    INSERT INTO LOG_BACKUPS
                    (ID_EMPRESA, DATA_INICIO, DATA_FIM, NOME_ARQUIVO,
                     CAMINHO_DESTINO, CAMINHO_DESTINO2, TAMANHO_BYTES, TAMANHO_FORMATADO,
                     STATUS, MENSAGEM_ERRO, TIPO_BACKUP, ENVIADO_FTP, DATA_ENVIO_FTP, MANUAL)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    log.id_empresa,
                    log.data_inicio,
                    log.data_fim,
                    log.nome_arquivo,
                    log.caminho_destino,
                    log.caminho_destino2,
                    log.tamanho_bytes,
                    log.tamanho_formatado,
                    log.status,
                    log.mensagem_erro,
                    log.tipo_backup,
                    log.enviado_ftp,
                    log.data_envio_ftp,
                    'S' if log.manual else 'N'
                ))
                conn.commit()
                return cursor.lastrowid

        except Exception as e:
            self.logger.error(f"Erro ao inserir log de backup: {e}")
            return None

    def update_log_backup(self, log: LogBackup) -> bool:
        """Atualiza log de backup"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = """
                    UPDATE LOG_BACKUPS SET
                        DATA_FIM = %s,
                        NOME_ARQUIVO = %s,
                        CAMINHO_DESTINO = %s,
                        CAMINHO_DESTINO2 = %s,
                        TAMANHO_BYTES = %s,
                        TAMANHO_FORMATADO = %s,
                        STATUS = %s,
                        MENSAGEM_ERRO = %s,
                        ENVIADO_FTP = %s,
                        DATA_ENVIO_FTP = %s
                    WHERE ID = %s
                """
                cursor.execute(sql, (
                    log.data_fim,
                    log.nome_arquivo,
                    log.caminho_destino,
                    log.caminho_destino2,
                    log.tamanho_bytes,
                    log.tamanho_formatado,
                    log.status,
                    log.mensagem_erro,
                    log.enviado_ftp,
                    log.data_envio_ftp,
                    log.id
                ))
                conn.commit()
                return cursor.rowcount > 0

        except Exception as e:
            self.logger.error(f"Erro ao atualizar log de backup: {e}")
            return False

    def get_logs_by_empresa(self, id_empresa: int, limit: int = 50) -> List[LogBackup]:
        """Busca logs de backup por empresa"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                sql = """
                    SELECT * FROM LOG_BACKUPS
                    WHERE ID_EMPRESA = %s
                    ORDER BY DATA_INICIO DESC
                    LIMIT %s
                """
                cursor.execute(sql, (id_empresa, limit))
                rows = cursor.fetchall()

                logs = []
                for row in rows:
                    # Campos podem não existir em bancos antigos
                    manual_value = row.get('MANUAL', 'N')
                    caminho_destino2 = row.get('CAMINHO_DESTINO2')
                    logs.append(LogBackup(
                        id=row['ID'],
                        id_empresa=row['ID_EMPRESA'],
                        data_inicio=row['DATA_INICIO'],
                        data_fim=row['DATA_FIM'],
                        nome_arquivo=row['NOME_ARQUIVO'],
                        caminho_destino=row['CAMINHO_DESTINO'],
                        caminho_destino2=caminho_destino2,
                        tamanho_bytes=row['TAMANHO_BYTES'],
                        tamanho_formatado=row['TAMANHO_FORMATADO'],
                        status=row['STATUS'],
                        mensagem_erro=row['MENSAGEM_ERRO'],
                        tipo_backup=row['TIPO_BACKUP'],
                        enviado_ftp=row['ENVIADO_FTP'],
                        data_envio_ftp=row['DATA_ENVIO_FTP'],
                        manual=(manual_value == 'S')
                    ))
                return logs

        except Exception as e:
            self.logger.error(f"Erro ao buscar logs de backup: {e}")
            return []

    # ============ VERSAO_APP ============

    def get_latest_version(self) -> Optional[VersaoApp]:
        """Busca a versão mais recente do aplicativo"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                sql = """
                    SELECT * FROM VERSAO_APP
                    ORDER BY DATA_LANCAMENTO DESC
                    LIMIT 1
                """
                cursor.execute(sql)
                row = cursor.fetchone()

                if row:
                    return VersaoApp(
                        id=row['ID'],
                        versao=row['VERSAO'],
                        data_lancamento=row['DATA_LANCAMENTO'],
                        url_download=row['URL_DOWNLOAD'],
                        hash_sha256=row['HASH_SHA256'],
                        changelog=row['CHANGELOG'],
                        obrigatoria=row['OBRIGATORIA']
                    )
                return None

        except Exception as e:
            self.logger.error(f"Erro ao buscar versão: {e}")
            return None

    # ============ INTERAÇÃO ============

    def update_empresa_interacao(self, id_empresa: int) -> bool:
        """Atualiza última interação da empresa (abertura do app ou backup)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = """
                    UPDATE EMPRESA SET DATA_ULTIMA_INTERACAO = %s WHERE ID = %s
                """
                cursor.execute(sql, (datetime.now(), id_empresa))
                conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"Erro ao atualizar interação: {e}")
            return False

    # ============ SCHEMA ============

    def ensure_schema(self):
        """Garante que o schema do banco está atualizado"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Verifica se coluna MANUAL existe em LOG_BACKUPS
                cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = 'LOG_BACKUPS'
                    AND COLUMN_NAME = 'MANUAL'
                """, (self.config.database,))

                if cursor.fetchone()[0] == 0:
                    # Adiciona coluna MANUAL
                    cursor.execute("""
                        ALTER TABLE LOG_BACKUPS
                        ADD COLUMN MANUAL CHAR(1) DEFAULT 'N'
                    """)
                    conn.commit()
                    self.logger.info("Coluna MANUAL adicionada à tabela LOG_BACKUPS")

                # Verifica se coluna CAMINHO_DESTINO2 existe em LOG_BACKUPS
                cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = 'LOG_BACKUPS'
                    AND COLUMN_NAME = 'CAMINHO_DESTINO2'
                """, (self.config.database,))

                if cursor.fetchone()[0] == 0:
                    # Adiciona coluna CAMINHO_DESTINO2
                    cursor.execute("""
                        ALTER TABLE LOG_BACKUPS
                        ADD COLUMN CAMINHO_DESTINO2 VARCHAR(500) AFTER CAMINHO_DESTINO
                    """)
                    conn.commit()
                    self.logger.info("Coluna CAMINHO_DESTINO2 adicionada à tabela LOG_BACKUPS")

                # Migração: Renomeia DATA_ULTIMA_ABERTURA para DATA_ULTIMA_INTERACAO
                cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = 'EMPRESA'
                    AND COLUMN_NAME = 'DATA_ULTIMA_ABERTURA'
                """, (self.config.database,))

                if cursor.fetchone()[0] > 0:
                    cursor.execute("""
                        ALTER TABLE EMPRESA
                        CHANGE DATA_ULTIMA_ABERTURA DATA_ULTIMA_INTERACAO DATETIME
                    """)
                    conn.commit()
                    self.logger.info("Coluna DATA_ULTIMA_ABERTURA renomeada para DATA_ULTIMA_INTERACAO")

                # Migração: Remove coluna ULTIMO_CONTATO (obsoleta)
                cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = 'EMPRESA'
                    AND COLUMN_NAME = 'ULTIMO_CONTATO'
                """, (self.config.database,))

                if cursor.fetchone()[0] > 0:
                    cursor.execute("""
                        ALTER TABLE EMPRESA
                        DROP COLUMN ULTIMO_CONTATO
                    """)
                    conn.commit()
                    self.logger.info("Coluna ULTIMO_CONTATO removida da tabela EMPRESA")

        except Exception as e:
            self.logger.warning(f"Erro ao verificar schema: {e}")
