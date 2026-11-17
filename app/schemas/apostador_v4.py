from pydantic import BaseModel


class ResumenApostadorV4(BaseModel):
    """Respuesta de GET /api/v4/apostadores/{id}/resumen."""

    apostador_id: int
    username: str
    total_predicciones: int
    # Las que ya tienen resultado: solo sobre estas se mide el acierto
    evaluadas: int
    aciertos: int
    precision: float
    puntos_totales: int
    # Aciertos seguidos, contando desde la ultima prediccion evaluada
    racha_actual: int
    # Promedio de las que trajeron confianza; None si ninguna la trajo
    confianza_promedio: float | None
