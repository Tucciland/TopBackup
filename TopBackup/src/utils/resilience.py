"""
TopBackup - Utilitários de Resiliência
Retry, circuit breaker e tratamento de falhas
"""

import time
import functools
from dataclasses import dataclass
from typing import Callable, TypeVar, Any, Optional, Tuple, Type
from enum import Enum


class CircuitState(Enum):
    """Estados do circuit breaker"""
    CLOSED = "closed"      # Funcionando normalmente
    OPEN = "open"          # Circuito aberto, rejeitando chamadas
    HALF_OPEN = "half_open"  # Testando se o serviço voltou


@dataclass
class RetryConfig:
    """Configuração de retry"""
    max_attempts: int = 3
    delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 30.0
    exceptions: Tuple[Type[Exception], ...] = (Exception,)


T = TypeVar('T')


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
) -> Callable:
    """
    Decorator para retry com backoff exponencial

    Args:
        max_attempts: Número máximo de tentativas
        delay: Delay inicial entre tentativas (segundos)
        backoff_multiplier: Multiplicador do delay a cada tentativa
        max_delay: Delay máximo entre tentativas
        exceptions: Tupla de exceções para retry
        on_retry: Callback chamado em cada retry

    Usage:
        @retry(max_attempts=3, delay=1.0)
        def funcao_instavel():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        raise

                    if on_retry:
                        on_retry(attempt, e)

                    time.sleep(current_delay)
                    current_delay = min(current_delay * backoff_multiplier, max_delay)

            raise last_exception

        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit Breaker para proteger contra falhas em cascata

    Usage:
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

        @cb
        def chamada_externa():
            ...
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self.execute(func, *args, **kwargs)
        return wrapper

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Executa função com proteção do circuit breaker"""
        self._check_state()

        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker está aberto. Tente novamente em {self._time_until_recovery():.1f}s"
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _check_state(self):
        """Verifica e atualiza estado do circuit breaker"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0

    def _should_attempt_recovery(self) -> bool:
        """Verifica se deve tentar recuperação"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _time_until_recovery(self) -> float:
        """Tempo até próxima tentativa de recuperação"""
        if self.last_failure_time is None:
            return 0
        elapsed = time.time() - self.last_failure_time
        return max(0, self.recovery_timeout - elapsed)

    def _on_success(self):
        """Callback de sucesso"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0

        self.success_count += 1

    def _on_failure(self):
        """Callback de falha"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def reset(self):
        """Reseta o circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0

    @property
    def is_open(self) -> bool:
        """Verifica se o circuito está aberto"""
        self._check_state()
        return self.state == CircuitState.OPEN


class CircuitBreakerOpenError(Exception):
    """Exceção lançada quando o circuit breaker está aberto"""
    pass


def with_timeout(timeout_seconds: float):
    """
    Decorator para adicionar timeout a funções
    NOTA: Funciona apenas em Windows com threading
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import threading
            import queue

            result_queue: queue.Queue = queue.Queue()
            exception_queue: queue.Queue = queue.Queue()

            def target():
                try:
                    result = func(*args, **kwargs)
                    result_queue.put(result)
                except Exception as e:
                    exception_queue.put(e)

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout_seconds)

            if thread.is_alive():
                raise TimeoutError(f"Operação excedeu timeout de {timeout_seconds}s")

            if not exception_queue.empty():
                raise exception_queue.get()

            if not result_queue.empty():
                return result_queue.get()

            raise RuntimeError("Execução falhou sem resultado ou exceção")

        return wrapper
    return decorator
