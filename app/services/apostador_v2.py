from app.core.config import get_settings
from app.schemas.apostador_v2 import ApostadorV2Respuesta
from app.services.apostador import ApostadorService
from app.services.integraciones_externas import obtener_datos_externos


class ApostadorV2Service:
    """Junta el apostador propio con datos en tiempo real de las APIs
    externas del equipo (Entrega 2). No duplica logica de negocio: el
    apostador mismo se resuelve reutilizando ApostadorService (v1)."""

    def __init__(self, apostador_service: ApostadorService) -> None:
        self._apostador_service = apostador_service
        self._settings = get_settings()

    def obtener_agregado(self, apostador_id: int) -> ApostadorV2Respuesta:
        apostador = self._apostador_service.obtener(apostador_id)
        return ApostadorV2Respuesta(
            apostador=apostador, **obtener_datos_externos(self._settings)
        )
