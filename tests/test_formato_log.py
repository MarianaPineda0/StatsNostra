# Formato de log acordado con el grupo: cada linea lleva traceId y api.
import json
import logging

from app.core.logging_config import FormateadorJSON
from app.core.trace import trace_id_var


def _linea(mensaje="hola", api="mari", **extra) -> dict:
    registro = logging.LogRecord("prueba", logging.INFO, __file__, 1, mensaje, None, None)
    for clave, valor in extra.items():
        setattr(registro, clave, valor)
    return json.loads(FormateadorJSON(api).format(registro))


def test_la_linea_lleva_traceid_api_y_hora_utc():
    token = trace_id_var.set("k6-3-9")
    try:
        linea = _linea()
    finally:
        trace_id_var.reset(token)
    assert linea["traceId"] == "k6-3-9"
    assert linea["trace_id"] == "k6-3-9"  # el nombre de la v2 se conserva
    assert linea["api"] == "mari"
    assert linea["timestamp"].endswith("+00:00")


def test_sin_peticion_en_curso_el_traceid_va_vacio():
    assert _linea()["traceId"] is None


def test_los_campos_del_evento_quedan_en_la_raiz():
    linea = _linea(datos={"metodo": "GET", "status": 200})
    assert linea["metodo"] == "GET"
    assert linea["status"] == 200
