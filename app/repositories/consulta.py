from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.apostador import Apostador
from app.models.partido import EstadoPartido, Partido
from app.models.prediccion import Prediccion


class ConsultaRepository:
    """Consultas de solo lectura que combinan las tablas existentes.

    No define ninguna entidad nueva: solo compone JOIN/GROUP BY sobre
    Apostador, Partido y Prediccion para las lecturas del verbo QUERY.
    """

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
        # Suma condicional: cuenta 1 por cada prediccion realmente acertada
        # (acertada=True), ignorando las fallidas (False) y las pendientes (NULL)
        aciertos = func.coalesce(
            func.sum(case((Prediccion.acertada.is_(True), 1), else_=0)), 0
        )
        puntos = func.coalesce(func.sum(Prediccion.puntos), 0)
        # outerjoin (no join normal) para que un apostador sin predicciones
        # todavia aparezca en el ranking con 0 puntos, en vez de desaparecer
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
