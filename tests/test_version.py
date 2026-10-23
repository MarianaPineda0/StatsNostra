# Pruebas de las cabeceras de version/track y del evento de negocio que
# se registra al finalizar un partido.
import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logging_config import FormateadorJSON
from app.core.middleware import TRACK_HEADER, VERSION_HEADER, VersionMiddleware


def test_health_incluye_version_y_track(client):
    cuerpo = client.get("/health").json()
    assert cuerpo["status"] == "ok"
    assert cuerpo["track"] == "stable"
    assert cuerpo["version"]


def test_toda_respuesta_lleva_version_y_track(client):
    # Tambien las que fallan: una ruta inexistente y un recurso que no existe
    for ruta in ("/health", "/ruta-que-no-existe", "/api/v1/apostadores/999999"):
        respuesta = client.get(ruta)
        assert VERSION_HEADER in respuesta.headers, ruta
        assert respuesta.headers[TRACK_HEADER] == "stable", ruta


def test_middleware_reporta_el_track_que_recibe():
    app = FastAPI()
    app.add_middleware(VersionMiddleware, version="4.0.0", track="canary")

    @app.get("/ping")
    def ping():
        return {}

    respuesta = TestClient(app).get("/ping")
    assert respuesta.headers[VERSION_HEADER] == "4.0.0"
    assert respuesta.headers[TRACK_HEADER] == "canary"


def test_formateador_pone_los_datos_del_evento_en_la_raiz():
    registro = logging.LogRecord("x", logging.INFO, __file__, 1, "evento", None, None)
    registro.datos = {"evento": "prediccion_evaluada", "puntos": 3}
    linea = json.loads(FormateadorJSON().format(registro))
    assert linea["evento"] == "prediccion_evaluada"
    assert linea["puntos"] == 3
    assert linea["message"] == "evento"


def test_finalizar_registra_un_evento_por_prediccion(client, caplog):
    apostador = client.post(
        "/apostadores",
        json={"nombre": "Ana", "username": "ana_ver", "email": "ana_ver@example.com"},
    ).json()
    partido = client.post(
        "/partidos",
        json={
            "deporte": "Futbol",
            "liga": "Liga X",
            "equipo_local": "Millonarios",
            "equipo_visitante": "Nacional",
            "fecha_hora": "2026-09-01T20:00:00Z",
        },
    ).json()
    client.post(
        "/predicciones",
        json={
            "apostador_id": apostador["id"],
            "partido_id": partido["id"],
            "goles_local_pred": 2,
            "goles_visitante_pred": 1,
        },
    )

    with caplog.at_level(logging.INFO):
        client.post(
            f"/partidos/{partido['id']}/finalizar",
            json={"resultado_local": 2, "resultado_visitante": 1},
        )

    eventos = [r.datos for r in caplog.records if hasattr(r, "datos")]
    assert eventos == [{"evento": "prediccion_evaluada", "acertada": True, "puntos": 3}]
