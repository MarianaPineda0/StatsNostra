import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EstadoPartido(str, enum.Enum):
    PROGRAMADO = "PROGRAMADO"
    EN_JUEGO = "EN_JUEGO"
    FINALIZADO = "FINALIZADO"


class Partido(Base):
    __tablename__ = "partidos"
    __table_args__ = (
        CheckConstraint(
            "equipo_local <> equipo_visitante", name="ck_partido_equipos_distintos"
        ),
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
