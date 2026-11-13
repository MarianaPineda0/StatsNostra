import threading
import time


class ConsumoEnCurso(Exception):
    """Ya hay un consumo de CPU activo en este proceso."""


class ConsumidorCPU:
    """Quema CPU del proceso durante un tiempo acotado, para el experimento de
    agotamiento de recursos.

    Los hilos ocupados compiten con el servidor por el GIL y por la cuota de CPU
    del contenedor, así que el pod deja de atender con soltura: es el mismo
    síntoma de un pod saturado de verdad, pero con inicio, fin y parada que
    controlamos nosotros.

    Tres garantías para que no se quede pegado: siempre hay un plazo (los hilos
    se detienen solos al cumplirse), se puede parar a mano, y son hilos demonio,
    de modo que reiniciar el pod también lo limpia.
    """

    def __init__(self) -> None:
        self._parar = threading.Event()
        self._cerrojo = threading.Lock()
        self._hilos: list[threading.Thread] = []
        self._hasta = 0.0

    def iniciar(self, segundos: int, hilos: int = 1) -> None:
        with self._cerrojo:
            if self._activo():
                raise ConsumoEnCurso("Ya hay un consumo de CPU en curso")
            self._parar.clear()
            self._hasta = time.monotonic() + segundos
            self._hilos = [
                threading.Thread(target=self._quemar, args=(self._hasta,), daemon=True)
                for _ in range(hilos)
            ]
            for hilo in self._hilos:
                hilo.start()

    def detener(self) -> bool:
        """Detiene el consumo. Devuelve si había uno en curso."""
        with self._cerrojo:
            estaba_activo = self._activo()
            self._parar.set()
            hilos = list(self._hilos)
        for hilo in hilos:
            hilo.join(timeout=2)
        return estaba_activo

    def estado(self) -> dict:
        with self._cerrojo:
            activo = self._activo()
            restantes = max(self._hasta - time.monotonic(), 0.0) if activo else 0.0
        return {"activo": activo, "segundos_restantes": round(restantes, 1)}

    def _activo(self) -> bool:
        return any(hilo.is_alive() for hilo in self._hilos)

    def _quemar(self, hasta: float) -> None:
        # Trabajo corto entre revisiones de la parada: la detención responde en
        # milisegundos y no depende de que termine una operación larga
        while not self._parar.is_set() and time.monotonic() < hasta:
            sum(i * i for i in range(2000))


consumidor = ConsumidorCPU()
