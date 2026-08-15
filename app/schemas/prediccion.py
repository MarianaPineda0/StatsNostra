from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PrediccionBase(BaseModel):
    apostador_id: int
    partido_id: int
    goles_local_pred: int = Field(ge=0)
    goles_visitante_pred: int = Field(ge=0)


class PrediccionCrear(PrediccionBase):
    pass


class PrediccionActualizar(BaseModel):
    goles_local_pred: int | None = Field(default=None, ge=0)
    goles_visitante_pred: int | None = Field(default=None, ge=0)


class PrediccionRespuesta(PrediccionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_prediccion: datetime
    acertada: bool | None
    puntos: int | None
