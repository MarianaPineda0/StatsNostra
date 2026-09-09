from pydantic import BaseModel

from app.schemas.apostador import ApostadorRespuesta


# Los datos de las APIs externas no tienen un schema fijo aqui a proposito:
# son propiedad de esas APIs, no de esta, y su forma puede cambiar sin que
# este repositorio tenga que actualizarse. None cuando esa nube no respondio.
class ApostadorV2Respuesta(BaseModel):
    apostador: ApostadorRespuesta
    trading_journal_trade: dict | None
    trading_journal_strategy: dict | None
    ecommerce_cliente: dict | None
    ecommerce_comercio: dict | None
