"""
TopBackup - Cliente Firebird
Conexão e operações com banco Firebird 2.5 usando fdb
"""

import fdb
from typing import Optional, List, Tuple
from contextlib import contextmanager

from .models import Empresa, AgendaBackup
from ..config.settings import FirebirdConfig
from ..utils.logger import get_logger
from ..utils.resilience import retry


class FirebirdClient:
    """Cliente para conexão com banco Firebird 2.5"""

    def __init__(self, config: FirebirdConfig):
        self.config = config
        self.logger = get_logger()
        self._connection: Optional[fdb.Connection] = None

    def _get_connection_params(self) -> dict:
        """Retorna parâmetros de conexão"""
        return {
            'dsn': self.config.database_path,
            'user': self.config.user,
            'password': self.config.password,
            'charset': self.config.charset,
        }

    @contextmanager
    def get_connection(self):
        """Context manager para conexão com Firebird"""
        connection = None
        try:
            connection = fdb.connect(**self._get_connection_params())
            yield connection
        finally:
            if connection:
                connection.close()

    @retry(max_attempts=3, delay=1.0, exceptions=(fdb.DatabaseError,))
    def test_connection(self) -> Tuple[bool, str]:
        """
        Testa a conexão com o banco Firebird

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM RDB$DATABASE")
                cursor.fetchone()
                return True, "Conexão bem-sucedida"
        except fdb.DatabaseError as e:
            self.logger.error(f"Erro de conexão Firebird: {e}")
            return False, str(e)
        except Exception as e:
            self.logger.error(f"Erro inesperado Firebird: {e}")
            return False, str(e)

    def get_empresa(self) -> Optional[Empresa]:
        """
        Obtém dados da empresa do banco Firebird

        A tabela EMPRESA no Firebird geralmente tem apenas um registro
        com os dados da empresa local.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Busca dados da empresa do banco Firebird local
                sql = """
                    SELECT FIRST 1
                        CODIGO,
                        FANTASIA,
                        RAZAO,
                        CNPJ,
                        DATA_CADASTRO
                    FROM EMPRESA
                """

                try:
                    cursor.execute(sql)
                    row = cursor.fetchone()
                except fdb.DatabaseError:
                    # Tenta SQL alternativo
                    sql = """
                        SELECT FIRST 1
                            ID,
                            NOME_FANTASIA,
                            RAZAO_SOCIAL,
                            CNPJ,
                            NULL
                        FROM EMPRESA
                    """
                    cursor.execute(sql)
                    row = cursor.fetchone()

                if row:
                    return Empresa(
                        id_aux=row[0],
                        fantasia=row[1] or "",
                        razao=row[2] or "",
                        cnpj=row[3] or "",
                        data_cadastro=row[4]
                    )

                return None

        except Exception as e:
            self.logger.error(f"Erro ao buscar empresa: {e}")
            return None

    def get_agenda_backup(self) -> Optional[AgendaBackup]:
        """
        Obtém configurações de agenda de backup do Firebird

        Busca na tabela AGENDA_BACKUP ou CONFIG_BACKUP
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Busca na tabela AGENDA_BACKUP
                # PREFIXO_BACKUP: 'V' = Versionado (CNPJ_ANO_MES_DIA_HORA)
                #                 'S' = Semanal (CNPJ_DIA_DA_SEMANA)
                #                 'U' = Unico (CNPJ)
                sql = """
                    SELECT
                        ID,
                        HORARIO,
                        DOM, SEG, TER, QUA, QUI, SEX, SAB,
                        LOCAL_DESTINO1,
                        LOCAL_DESTINO2,
                        BACKUP_REMOTO,
                        PREFIXO_BACKUP,
                        BANCO_ORIGEM
                    FROM AGENDA_BACKUP
                    ORDER BY ID
                """

                try:
                    cursor.execute(sql)
                    row = cursor.fetchone()
                except fdb.DatabaseError:
                    # Tenta tabela alternativa
                    sql = """
                        SELECT FIRST 1
                            ID,
                            HORA_BACKUP,
                            'N', 'S', 'S', 'S', 'S', 'S', 'N',
                            CAMINHO_BACKUP,
                            NULL,
                            'N',
                            'V',
                            'S'
                        FROM CONFIG_SISTEMA
                    """
                    cursor.execute(sql)
                    row = cursor.fetchone()

                if row:
                    # Debug: mostra o que veio do Firebird
                    self.logger.info(f"AGENDA_BACKUP do Firebird: ID={row[0]}, HORARIO={row[1]}")
                    self.logger.info(f"  LOCAL_DESTINO1={row[9]}")
                    self.logger.info(f"  LOCAL_DESTINO2={row[10]}")
                    self.logger.info(f"  PREFIXO_BACKUP={row[12]}, BANCO_ORIGEM={row[13]}")

                    return AgendaBackup(
                        id=row[0],
                        horario=row[1] or "23:00",
                        dom=row[2] or 'N',
                        seg=row[3] or 'S',
                        ter=row[4] or 'S',
                        qua=row[5] or 'S',
                        qui=row[6] or 'S',
                        sex=row[7] or 'S',
                        sab=row[8] or 'N',
                        local_destino1=row[9] or "",
                        local_destino2=row[10],
                        backup_remoto=row[11] or 'N',
                        prefixo_backup=row[12] or 'V',
                        banco_origem=row[13] or ""
                    )

                return None

        except Exception as e:
            self.logger.error(f"Erro ao buscar agenda de backup: {e}")
            return None

    def get_all_agendas(self) -> List[AgendaBackup]:
        """
        Obtém TODAS as agendas de backup do Firebird

        Returns:
            Lista de AgendaBackup
        """
        agendas = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                sql = """
                    SELECT
                        ID,
                        HORARIO,
                        DOM, SEG, TER, QUA, QUI, SEX, SAB,
                        LOCAL_DESTINO1,
                        LOCAL_DESTINO2,
                        BACKUP_REMOTO,
                        PREFIXO_BACKUP,
                        BANCO_ORIGEM
                    FROM AGENDA_BACKUP
                    ORDER BY HORARIO
                """

                cursor.execute(sql)
                rows = cursor.fetchall()

                for row in rows:
                    agenda = AgendaBackup(
                        id=row[0],
                        horario=row[1] or "23:00",
                        dom=row[2] or 'N',
                        seg=row[3] or 'S',
                        ter=row[4] or 'S',
                        qua=row[5] or 'S',
                        qui=row[6] or 'S',
                        sex=row[7] or 'S',
                        sab=row[8] or 'N',
                        local_destino1=row[9] or "",
                        local_destino2=row[10],
                        backup_remoto=row[11] or 'N',
                        prefixo_backup=row[12] or 'V',
                        banco_origem=row[13] or ""
                    )
                    agendas.append(agenda)

        except Exception as e:
            self.logger.error(f"Erro ao buscar agendas: {e}")

        return agendas

    def get_versao_sistema(self) -> Optional[str]:
        """Obtém a versão do sistema local do Firebird"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Tenta diferentes formas de obter a versão
                sqls = [
                    "SELECT FIRST 1 VERSAO FROM CONFIG_SISTEMA",
                    "SELECT FIRST 1 VERSAO FROM SISTEMA",
                    "SELECT FIRST 1 VALOR FROM PARAMETROS WHERE CHAVE = 'VERSAO'",
                ]

                for sql in sqls:
                    try:
                        cursor.execute(sql)
                        row = cursor.fetchone()
                        if row and row[0]:
                            return str(row[0])
                    except fdb.DatabaseError:
                        continue

                return None

        except Exception as e:
            self.logger.error(f"Erro ao buscar versão do sistema: {e}")
            return None

    def atualizar_data_abertura(self) -> bool:
        """Atualiza a data de última abertura do sistema"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                sql = """
                    UPDATE EMPRESA
                    SET DATA_CADASTRO = CURRENT_TIMESTAMP
                    WHERE CODIGO = (SELECT FIRST 1 CODIGO FROM EMPRESA)
                """

                try:
                    cursor.execute(sql)
                    conn.commit()
                    return True
                except fdb.DatabaseError:
                    return False

        except Exception as e:
            self.logger.error(f"Erro ao atualizar data de abertura: {e}")
            return False

    def get_database_path(self) -> str:
        """Retorna o caminho do banco de dados"""
        return self.config.database_path

    @staticmethod
    def validate_database_path(path: str) -> Tuple[bool, str]:
        """Valida se o caminho do banco é válido"""
        import os

        if not path:
            return False, "Caminho não informado"

        if not os.path.exists(path):
            return False, f"Arquivo não encontrado: {path}"

        if not path.lower().endswith(('.fdb', '.gdb')):
            return False, "Extensão inválida. Use .fdb ou .gdb"

        return True, "Caminho válido"
