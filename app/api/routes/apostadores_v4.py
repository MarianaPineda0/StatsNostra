from fastapi import APIRouter, Depends

from app.api.dependencies import get_apostador_v4_service
from app.schemas.apostador_v4 import ResumenApostadorV4
from app.services.apostador_v4 import ApostadorV4Service

# Entrega 4 (canary): lectura nueva sobre los datos de siempre. No hay
# CRUD de apostadores en v4: para eso siguen sirviendo v1 y v2.
router = APIRouter(prefix="/api/v4/apostadores", tags=["apostadores-v4"])


@router.get("/{apostador_id}/resumen", response_model=ResumenApostadorV4)
def resumen_apostador(
    apostador_id: int, service: ApostadorV4Service = Depends(get_apostador_v4_service)
) -> ResumenApostadorV4:
    return service.resumen(apostador_id)
