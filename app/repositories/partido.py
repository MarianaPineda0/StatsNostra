from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.partido import Partido


class PartidoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def crear(self, partido: Partido) -> Partido:
        self.db.add(partido)
        self.db.commit()
        self.db.refresh(partido)
        return partido

    def listar(self) -> list[Partido]:
        return list(self.db.scalars(select(Partido)).all())

    def obtener_por_id(self, partido_id: int) -> Partido | None:
        return self.db.get(Partido, partido_id)

    def actualizar(self, partido: Partido) -> Partido:
        self.db.commit()
        self.db.refresh(partido)
        return partido

    def eliminar(self, partido: Partido) -> None:
        self.db.delete(partido)
        self.db.commit()
