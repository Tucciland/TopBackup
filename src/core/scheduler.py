"""
TopBackup - Agendador de Backups
Usa APScheduler para agendar e executar backups
"""

from datetime import datetime, time
from typing import Optional, Callable, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobExecutionEvent

from ..database.models import AgendaBackup
from ..config.settings import Settings
from ..config.constants import CONFIG_SYNC_INTERVAL, UPDATE_CHECK_INTERVAL
from ..utils.logger import get_logger


class BackupScheduler:
    """Agendador de backups usando APScheduler"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger()

        # Cria scheduler com timezone local
        self.scheduler = BackgroundScheduler(
            timezone='America/Sao_Paulo',
            job_defaults={
                'coalesce': True,  # Agrupa execuções perdidas
                'max_instances': 1,  # Máximo 1 instância por job
                'misfire_grace_time': 3600  # 1 hora de tolerância
            }
        )

        # Callbacks
        self._backup_callback: Optional[Callable] = None
        self._sync_callback: Optional[Callable] = None
        self._update_callback: Optional[Callable] = None

        # Estado
        self._is_running = False
        self._next_backup: Optional[datetime] = None

    def set_backup_callback(self, callback: Callable):
        """Define callback para execução de backup"""
        self._backup_callback = callback

    def set_sync_callback(self, callback: Callable):
        """Define callback para sincronização"""
        self._sync_callback = callback

    def set_update_callback(self, callback: Callable):
        """Define callback para verificação de updates"""
        self._update_callback = callback

    def configure_from_agenda(self, agenda: AgendaBackup):
        """
        Configura agendamento baseado em uma única agenda (compatibilidade)
        """
        self.configure_from_agendas([agenda])

    def configure_from_agendas(self, agendas: List[AgendaBackup]):
        """
        Configura agendamento baseado em TODAS as agendas do Firebird

        Args:
            agendas: Lista de configurações de agendamento
        """
        # Remove jobs anteriores
        for i in range(10):  # Remove até 10 jobs de backup
            self._remove_job(f'backup_job_{i}')
        self._remove_job('backup_job')

        if not agendas:
            self.logger.warning("Nenhuma agenda de backup configurada")
            return

        # Cria um job para cada agenda/horário
        for i, agenda in enumerate(agendas):
            hora, minuto = agenda.get_hora_minuto()
            dias_cron = self._build_cron_days(agenda)

            if not dias_cron:
                self.logger.warning(f"Agenda {i+1}: Nenhum dia configurado")
                continue

            # Cria trigger cron
            trigger = CronTrigger(
                day_of_week=dias_cron,
                hour=hora,
                minute=minuto
            )

            job_id = f'backup_job_{i}'

            # Adiciona job
            self.scheduler.add_job(
                func=self._execute_backup_job,
                trigger=trigger,
                id=job_id,
                name=f'Backup {hora:02d}:{minuto:02d}',
                replace_existing=True
            )

            self.logger.info(f"Backup agendado: {hora:02d}:{minuto:02d} ({dias_cron})")

        # Atualiza próximo backup
        self._update_next_backup()

    def _build_cron_days(self, agenda: AgendaBackup) -> str:
        """Constrói string de dias para cron"""
        dias = []
        if agenda.seg == 'S':
            dias.append('mon')
        if agenda.ter == 'S':
            dias.append('tue')
        if agenda.qua == 'S':
            dias.append('wed')
        if agenda.qui == 'S':
            dias.append('thu')
        if agenda.sex == 'S':
            dias.append('fri')
        if agenda.sab == 'S':
            dias.append('sat')
        if agenda.dom == 'S':
            dias.append('sun')

        return ','.join(dias)

    def configure_system_jobs(self):
        """Configura jobs do sistema (sync, update)"""
        # Job de sincronização com Firebird (a cada 30min)
        if self._sync_callback:
            self.scheduler.add_job(
                func=self._sync_callback,
                trigger=IntervalTrigger(seconds=CONFIG_SYNC_INTERVAL),
                id='sync_job',
                name='Sincronização Config',
                replace_existing=True
            )

        # Job de verificação de updates (a cada 6h)
        if self._update_callback:
            self.scheduler.add_job(
                func=self._update_callback,
                trigger=IntervalTrigger(seconds=UPDATE_CHECK_INTERVAL),
                id='update_job',
                name='Verificação Updates',
                replace_existing=True
            )

    def start(self):
        """Inicia o scheduler"""
        if not self._is_running:
            self.scheduler.add_listener(
                self._on_job_event,
                EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
            )
            self.scheduler.start()
            self._is_running = True
            self.logger.info("Scheduler iniciado")

            # Atualiza próximo backup após iniciar (jobs só têm next_run_time após start)
            self._update_next_backup()

    def stop(self):
        """Para o scheduler"""
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            self.logger.info("Scheduler parado")

    def pause(self):
        """Pausa todos os jobs"""
        self.scheduler.pause()
        self.logger.info("Scheduler pausado")

    def resume(self):
        """Resume todos os jobs"""
        self.scheduler.resume()
        self.logger.info("Scheduler resumido")

    def trigger_backup_now(self):
        """Dispara backup manual imediatamente"""
        if self._backup_callback:
            self.scheduler.add_job(
                func=self._execute_backup_job,
                trigger='date',
                id='backup_manual',
                name='Backup Manual',
                replace_existing=True
            )
            self.logger.info("Backup manual agendado")

    def _execute_backup_job(self):
        """Executa job de backup"""
        if self._backup_callback:
            try:
                self._backup_callback()
            except Exception as e:
                self.logger.error(f"Erro no backup: {e}")
        self._update_next_backup()

    def _remove_job(self, job_id: str):
        """Remove job pelo ID"""
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass

    def _update_next_backup(self):
        """Atualiza próximo horário de backup considerando TODOS os jobs"""
        try:
            next_times = []
            for job in self.scheduler.get_jobs():
                if job.id.startswith('backup_job') and job.next_run_time:
                    next_times.append(job.next_run_time)

            if next_times:
                # Pega o mais próximo
                self._next_backup = min(next_times)
                self.logger.debug(f"Próximo backup: {self._next_backup}")
        except Exception:
            pass

    def _on_job_event(self, event: JobExecutionEvent):
        """Callback de eventos do scheduler"""
        if event.exception:
            self.logger.error(f"Job {event.job_id} falhou: {event.exception}")
        else:
            self.logger.debug(f"Job {event.job_id} executado")

    def get_next_backup_time(self) -> Optional[datetime]:
        """Retorna próximo horário de backup"""
        # Se não tem cache ou scheduler está rodando, calcula dinamicamente
        if self._next_backup is None and self._is_running:
            self._update_next_backup()
        return self._next_backup

    def get_scheduled_jobs(self) -> List[dict]:
        """Retorna lista de jobs agendados"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time,
                'trigger': str(job.trigger)
            })
        return jobs

    @property
    def is_running(self) -> bool:
        """Verifica se scheduler está rodando"""
        return self._is_running
