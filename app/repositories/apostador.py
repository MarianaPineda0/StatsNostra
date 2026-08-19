from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.apostador import Apostador


class ApostadorRepository:
    """Acceso a datos de Apostador. Sin reglas de negocio (eso va en el servicio)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def crear(self, apostador: Apostador) -> Apostador:
        self.db.add(apostador)
        self.db.commit()
        self.db.refresh(apostador)
        return apostador

    def listar(self) -> list[Apostador]:
        return list(self.db.scalars(select(Apostador)).all())

    def obtener_por_id(self, apostador_id: int) -> Apostador | None:
        return self.db.get(Apostador, apostador_id)

    def obtener_por_username(self, username: str) -> Apostador | None:
        return self.db.scalars(select(Apostador).where(Apostador.username == username)).first()

    def obtener_por_email(self, email: str) -> Apostador | None:
        return self.db.scalars(select(Apostador).where(Apostador.email == email)).first()

    def actualizar(self, apostador: Apostador) -> Apostador:
        self.db.commit()
        self.db.refresh(apostador)
        return apostador

    def eliminar(self, apostador: Apostador) -> None:
        self.db.delete(apostador)
        self.db.commit()
