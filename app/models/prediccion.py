from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Prediccion(Base):
    __tablename__ = "predicciones"
    __table_args__ = (
        UniqueConstraint("apostador_id", "partido_id", name="uq_prediccion_apostador_partido"),
        CheckConstraint("goles_local_pred >= 0", name="ck_prediccion_goles_local_no_negativo"),
        CheckConstraint(
            "goles_visitante_pred >= 0", name="ck_prediccion_goles_visitante_no_negativo"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    apostador_id: Mapped[int] = mapped_column(ForeignKey("apostadores.id"), nullable=False)
    partido_id: Mapped[int] = mapped_column(ForeignKey("partidos.id"), nullable=False)
    goles_local_pred: Mapped[int] = mapped_column(Integer, nullable=False)
    goles_visitante_pred: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_prediccion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    acertada: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    puntos: Mapped[int | None] = mapped_column(Integer, nullable=True)

    apostador: Mapped["Apostador"] = relationship(back_populates="predicciones")
    partido: Mapped["Partido"] = relationship(back_populates="predicciones")
