# Una linea de log por peticion, con el formato acordado con el grupo.
import logging

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _registros(caplog) -> list[dict]:
    return [
        r.datos
        for r in caplog.records
        if r.name == "app.core.middleware" and hasattr(r, "datos")
    ]


def test_cada_peticion_deja_una_linea_con_los_campos_del_grupo(caplog):
    with caplog.at_level(logging.INFO):
        client.get("/ruta-que-no-existe", headers={"X-Trace-Id": "k6-2-5"})

    (datos,) = _registros(caplog)
    assert datos["api"] == "mari"
    assert datos["traceId"] == "k6-2-5"
    assert datos["metodo"] == "GET"
    assert datos["ruta"] == "/ruta-que-no-existe"
    assert datos["status"] == 404
    assert datos["ms"] >= 0


def test_sin_trace_id_de_entrada_se_registra_el_generado(caplog):
    with caplog.at_level(logging.INFO):
        respuesta = client.get("/ruta-que-no-existe")

    (datos,) = _registros(caplog)
    assert datos["traceId"] == respuesta.headers["X-Trace-Id"]


def test_las_sondas_y_las_metricas_no_llenan_el_log(caplog):
    with caplog.at_level(logging.INFO):
        for ruta in ("/health", "/metrics"):
            client.get(ruta)

    assert _registros(caplog) == []
