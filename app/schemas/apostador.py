from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ApostadorBase(BaseModel):
    nombre: str
    username: str
    email: EmailStr  # Pydantic valida el formato de correo automaticamente


class ApostadorCrear(ApostadorBase):
    pass


# Todos los campos opcionales: permite actualizaciones parciales (PUT con
# solo el campo que se quiere cambiar, sin reenviar todo el objeto)
class ApostadorActualizar(BaseModel):
    nombre: str | None = None
    username: str | None = None
    email: EmailStr | None = None
    activo: bool | None = None


class ApostadorRespuesta(ApostadorBase):
    # from_attributes permite construir este schema directo desde el modelo
    # de SQLAlchemy (apostador.nombre, apostador.id, etc.), no solo desde un dict
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_registro: datetime
    activo: bool
