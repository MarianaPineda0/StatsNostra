import asyncio
import contextlib
from collections import deque

from prometheus_client import Gauge

INTERVALO_S = 0.1
# Diez muestras de 100 ms: el valor es el peor retraso del último segundo
MUESTRAS = 10

RETRASO_GAUGE = Gauge(
    "statsnostra_event_loop_lag_ms",
    "Peor retraso del bucle de eventos en el último segundo, en milisegundos",
)


class MonitorSaturacion:
    """Mide cuánto se atrasa el bucle de eventos respecto a lo que debería.

    Pide dormir 100 ms y mira cuánto tardó de verdad. En un pod sano el exceso
    es de pocos milisegundos; cuando algo le quita la CPU al proceso (un hilo
    ocupado, la cuota del contenedor) el bucle se atrasa y el exceso crece. Es
    la señal más directa de que el pod ya no atiende con soltura, y sirve para
    decidir si debe seguir recibiendo tráfico (/health/ready).
    """

    def __init__(self, intervalo: float = INTERVALO_S, muestras: int = MUESTRAS) -> None:
        self._intervalo = intervalo
        self._muestras: deque[float] = deque([0.0], maxlen=muestras)
        self._tarea: asyncio.Task | None = None

    @property
    def lag_ms(self) -> float:
        return max(self._muestras)

    def iniciar(self) -> None:
        if self._tarea is None:
            self._tarea = asyncio.create_task(self._medir())

    async def detener(self) -> None:
        if self._tarea is not None:
            self._tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tarea
            self._tarea = None

    async def _medir(self) -> None:
        bucle = asyncio.get_running_loop()
        while True:
            esperado = bucle.time() + self._intervalo
            await asyncio.sleep(self._intervalo)
            self._muestras.append(max(bucle.time() - esperado, 0.0) * 1000)
            RETRASO_GAUGE.set(self.lag_ms)


monitor = MonitorSaturacion()
