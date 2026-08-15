from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.apostador import Apostador
from app.models.partido import EstadoPartido, Partido
from app.models.prediccion import Prediccion


class ConsultaRepository:
    # Consultas de solo lectura que combinan las tablas existentes (no crea entidades nuevas)
    def __init__(self, db: Session) -> None:
        self.db = db

    def partidos_finalizados(self) -> list[Partido]:
        stmt = select(Partido).where(Partido.estado == EstadoPartido.FINALIZADO)
        return list(self.db.scalars(stmt).all())

    def partidos_filtrados(self, deporte: str | None, liga: str | None) -> list[Partido]:
        stmt = select(Partido)
        if deporte:
            stmt = stmt.where(Partido.deporte == deporte)
        if liga:
            stmt = stmt.where(Partido.liga == liga)
        return list(self.db.scalars(stmt).all())

    def ranking_apostadores(self):
        aciertos = func.coalesce(
            func.sum(case((Prediccion.acertada.is_(True), 1), else_=0)), 0
        )
        puntos = func.coalesce(func.sum(Prediccion.puntos), 0)
        stmt = (
            select(
                Apostador.id,
                Apostador.username,
                func.count(Prediccion.id).label("total_predicciones"),
                aciertos.label("aciertos"),
                puntos.label("puntos_totales"),
            )
            .select_from(Apostador)
            .outerjoin(Prediccion, Prediccion.apostador_id == Apostador.id)
            .group_by(Apostador.id, Apostador.username)
            .order_by(puntos.desc())
        )
        return self.db.execute(stmt).all()
