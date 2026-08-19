from app.core.exceptions import ConflictoDeDatos, RecursoNoEncontrado, ReglaDeNegocioViolada
from app.models.partido import EstadoPartido
from app.models.prediccion import Prediccion
from app.repositories.apostador import ApostadorRepository
from app.repositories.partido import PartidoRepository
from app.repositories.prediccion import PrediccionRepository
from app.schemas.prediccion import PrediccionActualizar, PrediccionCrear


class PrediccionService:
    """Reglas de negocio de Predicción (reglas 1-5 de la especificación)."""

    def __init__(
        self,
        repositorio: PrediccionRepository,
        apostadores: ApostadorRepository,
        partidos: PartidoRepository,
    ) -> None:
        self.repositorio = repositorio
        self.apostadores = apostadores
        self.partidos = partidos

    def crear(self, datos: PrediccionCrear) -> Prediccion:
        # Regla 2: el apostador debe existir
        apostador = self.apostadores.obtener_por_id(datos.apostador_id)
        if apostador is None:
            raise RecursoNoEncontrado(f"Apostador {datos.apostador_id} no encontrado")
        # Regla 3: el apostador debe estar activo
        if not apostador.activo:
            raise ReglaDeNegocioViolada("El apostador no está activo")

        # Regla 4: el partido debe existir
        partido = self.partidos.obtener_por_id(datos.partido_id)
        if partido is None:
            raise RecursoNoEncontrado(f"Partido {datos.partido_id} no encontrado")
        # Regla 1: no se puede predecir un partido ya finalizado
        if partido.estado == EstadoPartido.FINALIZADO:
            raise ReglaDeNegocioViolada("No se puede predecir un partido finalizado")

        # Regla 5: un apostador no puede tener dos predicciones para el
        # mismo partido (tambien reforzado por el UNIQUE de la BD, pero se
        # valida antes para devolver un 409 con mensaje claro)
        if self.repositorio.obtener_por_apostador_y_partido(
            datos.apostador_id, datos.partido_id
        ):
            raise ConflictoDeDatos("El apostador ya tiene una predicción para este partido")

        prediccion = Prediccion(
            apostador_id=datos.apostador_id,
            partido_id=datos.partido_id,
            goles_local_pred=datos.goles_local_pred,
            goles_visitante_pred=datos.goles_visitante_pred,
        )
        return self.repositorio.crear(prediccion)

    def listar(self) -> list[Prediccion]:
        return self.repositorio.listar()

    def obtener(self, prediccion_id: int) -> Prediccion:
        prediccion = self.repositorio.obtener_por_id(prediccion_id)
        if prediccion is None:
            raise RecursoNoEncontrado(f"Predicción {prediccion_id} no encontrada")
        return prediccion

    def actualizar(self, prediccion_id: int, datos: PrediccionActualizar) -> Prediccion:
        prediccion = self.obtener(prediccion_id)
        partido = self.partidos.obtener_por_id(prediccion.partido_id)
        if partido is not None and partido.estado == EstadoPartido.FINALIZADO:
            raise ReglaDeNegocioViolada(
                "No se puede modificar una predicción de un partido finalizado"
            )

        if datos.goles_local_pred is not None:
            prediccion.goles_local_pred = datos.goles_local_pred
        if datos.goles_visitante_pred is not None:
            prediccion.goles_visitante_pred = datos.goles_visitante_pred

        return self.repositorio.actualizar(prediccion)

    def eliminar(self, prediccion_id: int) -> None:
        prediccion = self.obtener(prediccion_id)
        self.repositorio.eliminar(prediccion)
