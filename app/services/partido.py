from app.core.exceptions import RecursoNoEncontrado, ReglaDeNegocioViolada
from app.models.partido import EstadoPartido, Partido
from app.repositories.partido import PartidoRepository
from app.repositories.prediccion import PrediccionRepository
from app.schemas.partido import PartidoActualizar, PartidoCrear, PartidoFinalizar
from app.services.puntos import calcular_puntos


class PartidoService:
    """Reglas de negocio de Partido, incluyendo el cierre de un partido."""

    def __init__(
        self, repositorio: PartidoRepository, predicciones: PrediccionRepository
    ) -> None:
        self.repositorio = repositorio
        self.predicciones = predicciones

    def crear(self, datos: PartidoCrear) -> Partido:
        partido = Partido(
            deporte=datos.deporte,
            liga=datos.liga,
            equipo_local=datos.equipo_local,
            equipo_visitante=datos.equipo_visitante,
            fecha_hora=datos.fecha_hora,
        )
        return self.repositorio.crear(partido)

    def listar(self) -> list[Partido]:
        return self.repositorio.listar()

    def obtener(self, partido_id: int) -> Partido:
        partido = self.repositorio.obtener_por_id(partido_id)
        if partido is None:
            raise RecursoNoEncontrado(f"Partido {partido_id} no encontrado")
        return partido

    def actualizar(self, partido_id: int, datos: PartidoActualizar) -> Partido:
        partido = self.obtener(partido_id)
        if partido.estado == EstadoPartido.FINALIZADO:
            raise ReglaDeNegocioViolada("No se puede modificar un partido finalizado")

        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(partido, campo, valor)

        return self.repositorio.actualizar(partido)

    def eliminar(self, partido_id: int) -> None:
        partido = self.obtener(partido_id)
        self.repositorio.eliminar(partido)

    def finalizar(self, partido_id: int, datos: PartidoFinalizar) -> Partido:
        # Regla 6: un partido finalizado no puede volver a finalizarse
        # (evita recalcular puntos dos veces sobre las mismas predicciones)
        partido = self.obtener(partido_id)
        if partido.estado == EstadoPartido.FINALIZADO:
            raise ReglaDeNegocioViolada("El partido ya fue finalizado")

        partido.resultado_local = datos.resultado_local
        partido.resultado_visitante = datos.resultado_visitante
        partido.estado = EstadoPartido.FINALIZADO

        # Regla 7: al finalizar se evaluan TODAS las predicciones de este
        # partido de una vez, dejando acertada/puntos fijos permanentemente
        for prediccion in self.predicciones.listar_por_partido(partido_id):
            acertada, puntos = calcular_puntos(
                prediccion.goles_local_pred,
                prediccion.goles_visitante_pred,
                datos.resultado_local,
                datos.resultado_visitante,
            )
            prediccion.acertada = acertada
            prediccion.puntos = puntos

        return self.repositorio.actualizar(partido)
