from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Import solo para chequeo de tipos: evita el import circular en tiempo de
# ejecucion (Prediccion tambien referencia a Apostador), pero le permite al
# editor/type checker resolver "Prediccion" en el relationship de abajo.
if TYPE_CHECKING:
    from app.models.prediccion import Prediccion


class Apostador(Base):
    """Usuario que registra predicciones sobre partidos."""

    __tablename__ = "apostadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    # username y email unicos a nivel de BD (no solo validados en la app):
    # asi ni una insercion directa por SQL podria dejar duplicados
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Un apostador inactivo no puede crear nuevas predicciones (ver
    # PrediccionService.crear) aunque su historial se conserve intacto
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    predicciones: Mapped[list["Prediccion"]] = relationship(back_populates="apostador")
