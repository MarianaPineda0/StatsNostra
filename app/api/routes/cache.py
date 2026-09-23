from typing import Literal

from fastapi import APIRouter, status

from app.core.config import get_settings
from app.services.integraciones_externas import invalidar_cache_externa

# Contraparte del TTL de 30s (app/integrations/cache.py): permite forzar
# desde afuera que el proximo request vuelva a traer el dato mas reciente
# de la API del compañero, sin esperar a que expire la cache.
router = APIRouter(prefix="/api/v2/cache", tags=["cache"])


@router.delete("/{entidad}", status_code=status.HTTP_204_NO_CONTENT)
def invalidar_entidad(entidad: Literal["trading_journal", "ecommerce"]) -> None:
    invalidar_cache_externa(get_settings(), entidad)
