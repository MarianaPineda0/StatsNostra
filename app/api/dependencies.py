from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.apostador import ApostadorRepository
from app.repositories.consulta import ConsultaRepository
from app.repositories.partido import PartidoRepository
from app.repositories.prediccion import PrediccionRepository
from app.services.apostador import ApostadorService
from app.services.consulta import ConsultaService
from app.services.partido import PartidoService
from app.services.prediccion import PrediccionService


# Fabricas de servicios para inyeccion de dependencias de FastAPI: cada
# ruta pide `service: XService = Depends(get_x_service)` y recibe una
# instancia ya armada con su repositorio (y la sesion de BD de esa
# solicitud) sin tener que construirla a mano en cada endpoint.
def get_apostador_service(db: Session = Depends(get_db)) -> ApostadorService:
    return ApostadorService(ApostadorRepository(db))


def get_partido_service(db: Session = Depends(get_db)) -> PartidoService:
    return PartidoService(PartidoRepository(db), PrediccionRepository(db))


def get_prediccion_service(db: Session = Depends(get_db)) -> PrediccionService:
    return PrediccionService(
        PrediccionRepository(db), ApostadorRepository(db), PartidoRepository(db)
    )


def get_consulta_service(db: Session = Depends(get_db)) -> ConsultaService:
    return ConsultaService(
        ConsultaRepository(db),
        ApostadorRepository(db),
        PartidoRepository(db),
        PrediccionRepository(db),
    )
