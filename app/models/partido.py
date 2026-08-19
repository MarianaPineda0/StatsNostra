import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.prediccion import Prediccion


class EstadoPartido(enum.StrEnum):
    # Ciclo de vida de un partido: solo se puede predecir en PROGRAMADO,
    # y FINALIZADO es un estado terminal (no vuelve atras, ver
    # PartidoService.finalizar)
    PROGRAMADO = "PROGRAMADO"
    EN_JUEGO = "EN_JUEGO"
    FINALIZADO = "FINALIZADO"


class Partido(Base):
    """Evento deportivo sobre el que los apostadores hacen predicciones."""

    __tablename__ = "partidos"
    __table_args__ = (
        # Regla de negocio: un equipo no puede jugar contra si mismo
        CheckConstraint(
            "equipo_local <> equipo_visitante", name="ck_partido_equipos_distintos"
        ),
        # Los resultados solo existen despues de finalizar (por eso permiten
        # NULL), pero si tienen valor no pueden ser negativos
        CheckConstraint(
            "resultado_local IS NULL OR resultado_local >= 0",
            name="ck_partido_resultado_local_no_negativo",
        ),
        CheckConstraint(
            "resultado_visitante IS NULL OR resultado_visitante >= 0",
            name="ck_partido_resultado_visitante_no_negativo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    deporte: Mapped[str] = mapped_column(String(50), nullable=False)
    liga: Mapped[str] = mapped_column(String(100), nullable=False)
    equipo_local: Mapped[str] = mapped_column(String(100), nullable=False)
    equipo_visitante: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[EstadoPartido] = mapped_column(
        Enum(EstadoPartido, name="estado_partido"),
        default=EstadoPartido.PROGRAMADO,
        nullable=False,
    )
    resultado_local: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resultado_visitante: Mapped[int | None] = mapped_column(Integer, nullable=True)

    predicciones: Mapped[list["Prediccion"]] = relationship(back_populates="partido")
