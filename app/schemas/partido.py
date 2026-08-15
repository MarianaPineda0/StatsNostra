from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.partido import EstadoPartido


class PartidoBase(BaseModel):
    deporte: str
    liga: str
    equipo_local: str
    equipo_visitante: str
    fecha_hora: datetime

    @model_validator(mode="after")
    def validar_equipos_distintos(self) -> Self:
        if self.equipo_local == self.equipo_visitante:
            raise ValueError("equipo_local y equipo_visitante deben ser distintos")
        return self


class PartidoCrear(PartidoBase):
    pass


class PartidoActualizar(BaseModel):
    deporte: str | None = None
    liga: str | None = None
    equipo_local: str | None = None
    equipo_visitante: str | None = None
    fecha_hora: datetime | None = None


class PartidoFinalizar(BaseModel):
    resultado_local: int = Field(ge=0)
    resultado_visitante: int = Field(ge=0)


class PartidoRespuesta(PartidoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado: EstadoPartido
    resultado_local: int | None
    resultado_visitante: int | None
