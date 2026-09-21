from app.core.config import get_settings
from app.schemas.partido_v2 import PartidoV2Respuesta
from app.services.integraciones_externas import obtener_datos_externos
from app.services.partido import PartidoService


class PartidoV2Service:
    """Junta el partido propio con datos en tiempo real de las APIs
    externas del equipo (Entrega 2). No duplica logica de negocio: el
    partido mismo se resuelve reutilizando PartidoService (v1)."""

    def __init__(self, partido_service: PartidoService) -> None:
        self._partido_service = partido_service
        self._settings = get_settings()

    def obtener_agregado(self, partido_id: int) -> PartidoV2Respuesta:
        partido = self._partido_service.obtener(partido_id)
        return PartidoV2Respuesta(partido=partido, **obtener_datos_externos(self._settings))
