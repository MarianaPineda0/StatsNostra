from app.core.exceptions import RecursoNoEncontrado
from app.models.partido import Partido
from app.models.prediccion import Prediccion
from app.repositories.apostador import ApostadorRepository
from app.repositories.consulta import ConsultaRepository
from app.repositories.partido import PartidoRepository
from app.repositories.prediccion import PrediccionRepository
from app.schemas.consulta import EstadisticasApostador, PosicionRanking


class ConsultaService:
    """Lecturas del verbo QUERY: combinan datos de varias entidades a la vez.

    Se separa de los servicios de cada entidad porque estas consultas no
    pertenecen a una sola tabla (ej. el ranking cruza Apostador y Prediccion).
    """

    def __init__(
        self,
        consultas: ConsultaRepository,
        apostadores: ApostadorRepository,
        partidos: PartidoRepository,
        predicciones: PrediccionRepository,
    ) -> None:
        self.consultas = consultas
        self.apostadores = apostadores
        self.partidos = partidos
        self.predicciones = predicciones

    def predicciones_por_apostador(self, apostador_id: int) -> list[Prediccion]:
        if self.apostadores.obtener_por_id(apostador_id) is None:
            raise RecursoNoEncontrado(f"Apostador {apostador_id} no encontrado")
        return self.predicciones.listar_por_apostador(apostador_id)

    def predicciones_por_partido(self, partido_id: int) -> list[Prediccion]:
        if self.partidos.obtener_por_id(partido_id) is None:
            raise RecursoNoEncontrado(f"Partido {partido_id} no encontrado")
        return self.predicciones.listar_por_partido(partido_id)

    def estadisticas_apostador(self, apostador_id: int) -> EstadisticasApostador:
        if self.apostadores.obtener_por_id(apostador_id) is None:
            raise RecursoNoEncontrado(f"Apostador {apostador_id} no encontrado")

        predicciones = self.predicciones.listar_por_apostador(apostador_id)
        total = len(predicciones)
        acertadas = sum(1 for p in predicciones if p.acertada is True)
        fallidas = sum(1 for p in predicciones if p.acertada is False)
        puntos_totales = sum(p.puntos or 0 for p in predicciones)
        porcentaje = (acertadas / total * 100) if total > 0 else 0.0

        return EstadisticasApostador(
            total_predicciones=total,
            predicciones_acertadas=acertadas,
            predicciones_fallidas=fallidas,
            porcentaje_acierto=round(porcentaje, 2),
            puntos_totales=puntos_totales,
        )

    def ranking_apostadores(self) -> list[PosicionRanking]:
        # El repositorio ya devuelve las filas ordenadas por puntos (SQL
        # ORDER BY); aqui solo se les asigna la posicion 1, 2, 3... segun
        # el orden en que llegan
        filas = self.consultas.ranking_apostadores()
        resultado = []
        for posicion, fila in enumerate(filas, start=1):
            porcentaje = (
                (fila.aciertos / fila.total_predicciones * 100)
                if fila.total_predicciones > 0
                else 0.0
            )
            resultado.append(
                PosicionRanking(
                    posicion=posicion,
                    apostador_id=fila.id,
                    username=fila.username,
                    total_predicciones=fila.total_predicciones,
                    aciertos=fila.aciertos,
                    porcentaje_acierto=round(porcentaje, 2),
                    puntos_totales=fila.puntos_totales,
                )
            )
        return resultado

    def partidos_finalizados(self) -> list[Partido]:
        return self.consultas.partidos_finalizados()

    def listar_partidos(self, deporte: str | None, liga: str | None) -> list[Partido]:
        return self.consultas.partidos_filtrados(deporte, liga)
