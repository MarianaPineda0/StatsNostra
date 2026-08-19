from fastapi import APIRouter, Depends

from app.api.dependencies import get_consulta_service
from app.schemas.consulta import EstadisticasApostador, PosicionRanking
from app.schemas.partido import PartidoRespuesta
from app.schemas.prediccion import PrediccionRespuesta
from app.services.consulta import ConsultaService

# Estas rutas usan el verbo HTTP "QUERY" (no GET) via api_route(methods=["QUERY"]),
# el metodo generico de FastAPI/Starlette para registrar cualquier verbo,
# no solo los atajos usuales (@router.get, @router.post, etc.).
#
# Como Cloudflare (el borde de Render) bloquea metodos no estandar antes de
# que lleguen a la app, MetodoOverrideMiddleware (app/core/middleware.py)
# permite tambien invocarlas con POST + header X-HTTP-Method-Override: QUERY
# sin cambiar nada aqui — el metodo real sigue siendo QUERY.
router = APIRouter(prefix="/query", tags=["query"])


@router.api_route(
    "/apostadores/{apostador_id}/predicciones",
    methods=["QUERY"],
    response_model=list[PrediccionRespuesta],
)
def consultar_predicciones_por_apostador(
    apostador_id: int, service: ConsultaService = Depends(get_consulta_service)
) -> list[PrediccionRespuesta]:
    return service.predicciones_por_apostador(apostador_id)


@router.api_route(
    "/partidos/{partido_id}/predicciones",
    methods=["QUERY"],
    response_model=list[PrediccionRespuesta],
)
def consultar_predicciones_por_partido(
    partido_id: int, service: ConsultaService = Depends(get_consulta_service)
) -> list[PrediccionRespuesta]:
    return service.predicciones_por_partido(partido_id)


@router.api_route(
    "/apostadores/{apostador_id}/estadisticas",
    methods=["QUERY"],
    response_model=EstadisticasApostador,
)
def consultar_estadisticas_apostador(
    apostador_id: int, service: ConsultaService = Depends(get_consulta_service)
) -> EstadisticasApostador:
    return service.estadisticas_apostador(apostador_id)


@router.api_route(
    "/apostadores/ranking", methods=["QUERY"], response_model=list[PosicionRanking]
)
def consultar_ranking(
    service: ConsultaService = Depends(get_consulta_service),
) -> list[PosicionRanking]:
    return service.ranking_apostadores()


@router.api_route(
    "/partidos/finalizados", methods=["QUERY"], response_model=list[PartidoRespuesta]
)
def consultar_partidos_finalizados(
    service: ConsultaService = Depends(get_consulta_service),
) -> list[PartidoRespuesta]:
    return service.partidos_finalizados()


@router.api_route("/partidos", methods=["QUERY"], response_model=list[PartidoRespuesta])
def consultar_partidos(
    deporte: str | None = None,
    liga: str | None = None,
    service: ConsultaService = Depends(get_consulta_service),
) -> list[PartidoRespuesta]:
    return service.listar_partidos(deporte, liga)
