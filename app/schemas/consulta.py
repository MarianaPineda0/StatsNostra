from pydantic import BaseModel


class EstadisticasApostador(BaseModel):
    total_predicciones: int
    predicciones_acertadas: int
    predicciones_fallidas: int
    porcentaje_acierto: float
    puntos_totales: int


class PosicionRanking(BaseModel):
    posicion: int
    apostador_id: int
    username: str
    total_predicciones: int
    aciertos: int
    porcentaje_acierto: float
    puntos_totales: int
