from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prediccion import Prediccion


class PrediccionRepository:
    """Acceso a datos de Predicción. Sin reglas de negocio (eso va en el servicio)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def crear(self, prediccion: Prediccion) -> Prediccion:
        self.db.add(prediccion)
        self.db.commit()
        self.db.refresh(prediccion)
        return prediccion

    def listar(self) -> list[Prediccion]:
        return list(self.db.scalars(select(Prediccion)).all())

    def obtener_por_id(self, prediccion_id: int) -> Prediccion | None:
        return self.db.get(Prediccion, prediccion_id)

    def obtener_por_apostador_y_partido(
        self, apostador_id: int, partido_id: int
    ) -> Prediccion | None:
        return self.db.scalars(
            select(Prediccion).where(
                Prediccion.apostador_id == apostador_id,
                Prediccion.partido_id == partido_id,
            )
        ).first()

    def listar_por_partido(self, partido_id: int) -> list[Prediccion]:
        return list(
            self.db.scalars(
                select(Prediccion).where(Prediccion.partido_id == partido_id)
            ).all()
        )

    def listar_por_apostador(self, apostador_id: int) -> list[Prediccion]:
        return list(
            self.db.scalars(
                select(Prediccion).where(Prediccion.apostador_id == apostador_id)
            ).all()
        )

    def actualizar(self, prediccion: Prediccion) -> Prediccion:
        self.db.commit()
        self.db.refresh(prediccion)
        return prediccion

    def eliminar(self, prediccion: Prediccion) -> None:
        self.db.delete(prediccion)
        self.db.commit()
