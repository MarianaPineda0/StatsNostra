from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ApostadorBase(BaseModel):
    nombre: str
    username: str
    email: EmailStr


class ApostadorCrear(ApostadorBase):
    pass


class ApostadorActualizar(BaseModel):
    nombre: str | None = None
    username: str | None = None
    email: EmailStr | None = None
    activo: bool | None = None


class ApostadorRespuesta(ApostadorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_registro: datetime
    activo: bool
