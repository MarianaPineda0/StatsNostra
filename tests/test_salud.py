# Las sondas de liveness y readiness viven en rutas distintas y responden 200.
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.parametrize("ruta", ["/health", "/health/live", "/health/ready"])
def test_las_rutas_de_salud_responden_200(ruta):
    respuesta = client.get(ruta)
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_liveness_y_readiness_son_rutas_diferentes():
    rutas = app.openapi()["paths"]
    assert "/health/live" in rutas and "/health/ready" in rutas


def test_las_sondas_tambien_traen_la_identificacion_de_la_api():
    respuesta = client.get("/health/ready")
    assert respuesta.headers["X-App-Name"] == "mari"
