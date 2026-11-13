import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.core.consumo_cpu import ConsumoEnCurso, consumidor
from app.core.fallos import fallos_pedidos

logger = logging.getLogger(__name__)

# Solo se registra con FAULT_HEADER_ENABLED=true (ver app/main.py): con el
# interruptor apagado estas rutas ni existen
router = APIRouter(prefix="/fault/cpu", tags=["fallos"])

# Tope del consumo: aunque la petición pida más, ningún experimento se queda
# quemando CPU mas de diez minutos
MAXIMO_SEGUNDOS = 600


def exigir_cabecera_cpu(x_inject_fault: str | None = Header(default=None)) -> None:
    # Una segunda llave además de la variable de entorno: una petición suelta no
    # puede arrancar el consumo sin pedirlo expresamente
    if "cpu" not in fallos_pedidos(x_inject_fault or ""):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Falta la cabecera X-Inject-Fault: cpu",
        )


@router.post("", dependencies=[Depends(exigir_cabecera_cpu)])
def iniciar_consumo(
    segundos: int = Query(180, ge=1, le=MAXIMO_SEGUNDOS),
    hilos: int = Query(1, ge=1, le=4),
) -> dict:
    try:
        consumidor.iniciar(segundos, hilos)
    except ConsumoEnCurso as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    logger.warning(
        "consumo de cpu iniciado",
        extra={
            "datos": {"evento": "cpu_agotamiento_inicio", "segundos": segundos, "hilos": hilos}
        },
    )
    return consumidor.estado()


# Detener no pide cabecera: parar el experimento tiene que ser siempre fácil
@router.delete("")
def detener_consumo() -> dict:
    habia = consumidor.detener()
    logger.warning(
        "consumo de cpu detenido",
        extra={"datos": {"evento": "cpu_agotamiento_fin", "habia_consumo": habia}},
    )
    return consumidor.estado()


@router.get("")
def estado_consumo() -> dict:
    return consumidor.estado()
