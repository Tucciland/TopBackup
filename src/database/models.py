"""
TopBackup - Modelos de Dados
Dataclasses para representar entidades do sistema
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional, Union
from enum import Enum


class StatusBackup(Enum):
    """Status do backup"""
    PENDENTE = 'P'
    EXECUTANDO = 'E'
    SUCESSO = 'S'
    FALHA = 'F'


class TipoBackup(Enum):
    """Tipo de backup"""
    VERSIONADO = 'V'  # CNPJ_YYYYMMDD_HHMMSS.zip
    SEMANAL = 'S'     # CNPJ_SEG.zip
    UNICO = 'U'       # CNPJ.zip


class DiaSemana(Enum):
    """Dias da semana para agendamento"""
    DOM = 'DOM'
    SEG = 'SEG'
    TER = 'TER'
    QUA = 'QUA'
    QUI = 'QUI'
    SEX = 'SEX'
    SAB = 'SAB'


@dataclass
class Empresa:
    """Representa uma empresa do sistema"""
    id: Optional[int] = None
    id_aux: Optional[int] = None  # ID do sistema local
    fantasia: str = ""
    razao: str = ""
    cnpj: str = ""
    data_ultima_interacao: Optional[datetime] = None
    versao_local: Optional[str] = None
    data_cadastro: Optional[datetime] = None
    ativo: str = 'S'

    def cnpj_limpo(self) -> str:
        """Retorna CNPJ apenas com números"""
        return ''.join(filter(str.isdigit, self.cnpj))

    def is_ativo(self) -> bool:
        """Verifica se empresa está ativa"""
        return self.ativo == 'S'


@dataclass
class AgendaBackup:
    """Representa uma agenda de backup do Firebird

    prefixo_backup indica o padrão de nomenclatura do arquivo:
        'V' = Versionado: CNPJ_YYYYMMDD_HHMMSS.zip (várias versões por data/hora)
        'S' = Semanal: CNPJ_SEG.zip (controle semanal, dia da semana)
        'U' = Unico: CNPJ.zip (arquivo único, sempre sobrescrito)
    """
    id: Optional[int] = None
    id_empresa: Optional[int] = None
    horario: Union[str, time] = "23:00"
    dom: str = 'N'
    seg: str = 'S'
    ter: str = 'S'
    qua: str = 'S'
    qui: str = 'S'
    sex: str = 'S'
    sab: str = 'N'
    local_destino1: str = ""
    local_destino2: Optional[str] = None
    backup_remoto: str = 'N'
    prefixo_backup: str = 'V'
    banco_origem: str = ""

    def get_dias_ativos(self) -> list:
        """Retorna lista de dias da semana ativos"""
        dias = []
        if self.dom == 'S':
            dias.append(6)  # Domingo = 6 no Python
        if self.seg == 'S':
            dias.append(0)
        if self.ter == 'S':
            dias.append(1)
        if self.qua == 'S':
            dias.append(2)
        if self.qui == 'S':
            dias.append(3)
        if self.sex == 'S':
            dias.append(4)
        if self.sab == 'S':
            dias.append(5)
        return dias

    def deve_executar_hoje(self) -> bool:
        """Verifica se deve executar backup hoje"""
        hoje = datetime.now().weekday()
        return hoje in self.get_dias_ativos()

    def get_hora_minuto(self) -> tuple:
        """Retorna hora e minuto do agendamento"""
        try:
            # Se for objeto time do datetime, usa diretamente
            if isinstance(self.horario, time):
                return self.horario.hour, self.horario.minute
            # Se for string, faz o parse
            partes = str(self.horario).split(':')
            return int(partes[0]), int(partes[1])
        except (ValueError, IndexError, AttributeError):
            return 23, 0


@dataclass
class LogBackup:
    """Representa um log de backup"""
    id: Optional[int] = None
    id_empresa: int = 0
    data_inicio: datetime = field(default_factory=datetime.now)
    data_fim: Optional[datetime] = None
    nome_arquivo: Optional[str] = None
    caminho_destino: Optional[str] = None
    caminho_destino2: Optional[str] = None
    tamanho_bytes: Optional[int] = None
    tamanho_formatado: Optional[str] = None
    status: str = StatusBackup.PENDENTE.value
    mensagem_erro: Optional[str] = None
    tipo_backup: Optional[str] = None
    enviado_ftp: str = 'N'
    data_envio_ftp: Optional[datetime] = None
    manual: bool = False  # True se foi backup manual, False se automático

    def set_sucesso(self, arquivo: str, caminho: str, tamanho: int, tamanho_fmt: str, caminho2: Optional[str] = None):
        """Define backup como sucesso"""
        self.status = StatusBackup.SUCESSO.value
        self.data_fim = datetime.now()
        self.nome_arquivo = arquivo
        self.caminho_destino = caminho
        self.caminho_destino2 = caminho2
        self.tamanho_bytes = tamanho
        self.tamanho_formatado = tamanho_fmt

    def set_falha(self, erro: str):
        """Define backup como falha"""
        self.status = StatusBackup.FALHA.value
        self.data_fim = datetime.now()
        self.mensagem_erro = erro

    def set_executando(self):
        """Define backup como em execução"""
        self.status = StatusBackup.EXECUTANDO.value

    def set_ftp_enviado(self):
        """Define que arquivo foi enviado via FTP"""
        self.enviado_ftp = 'S'
        self.data_envio_ftp = datetime.now()

    def duracao_segundos(self) -> Optional[float]:
        """Calcula duração do backup em segundos"""
        if self.data_fim and self.data_inicio:
            delta = self.data_fim - self.data_inicio
            return delta.total_seconds()
        return None


@dataclass
class VersaoApp:
    """Representa uma versão do aplicativo para auto-update"""
    id: Optional[int] = None
    versao: str = ""
    data_lancamento: Optional[datetime] = None
    url_download: str = ""
    hash_sha256: Optional[str] = None
    changelog: Optional[str] = None
    obrigatoria: str = 'N'

    def is_obrigatoria(self) -> bool:
        """Verifica se a atualização é obrigatória"""
        return self.obrigatoria == 'S'


