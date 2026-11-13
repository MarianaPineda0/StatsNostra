# Endpoint de consumo de CPU: protegido por cabecera, con tope de duración, un
# solo consumo a la vez y parada siempre disponible.
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import fallos
from app.core.consumo_cpu import ConsumidorCPU
from app.main import app as app_real

CABECERA = {"X-Inject-Fault": "cpu"}


@pytest.fixture()
def cliente(monkeypatch):
    consumidor = ConsumidorCPU()
    monkeypatch.setattr(fallos, "consumidor", consumidor)
    app = FastAPI()
    app.include_router(fallos.router)
    yield TestClient(app)
    consumidor.detener()  # que ninguna prueba deje hilos quemando CPU


def test_sin_la_cabecera_no_arranca_y_responde_403(cliente):
    respuesta = cliente.post("/fault/cpu?segundos=30")
    assert respuesta.status_code == 403
    assert cliente.get("/fault/cpu").json()["activo"] is False


def test_otra_cabecera_de_fallo_tampoco_vale(cliente):
    respuesta = cliente.post("/fault/cpu", headers={"X-Inject-Fault": "error"})
    assert respuesta.status_code == 403


def test_con_la_cabecera_arranca_y_el_estado_lo_refleja(cliente):
    respuesta = cliente.post("/fault/cpu?segundos=30&hilos=2", headers=CABECERA)
    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is True
    assert cliente.get("/fault/cpu").json()["activo"] is True


def test_un_segundo_arranque_responde_409(cliente):
    cliente.post("/fault/cpu?segundos=30", headers=CABECERA)
    respuesta = cliente.post("/fault/cpu?segundos=30", headers=CABECERA)
    assert respuesta.status_code == 409


def test_detener_funciona_sin_cabecera(cliente):
    cliente.post("/fault/cpu?segundos=30", headers=CABECERA)
    respuesta = cliente.delete("/fault/cpu")
    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False


def test_detener_sin_consumo_no_falla(cliente):
    assert cliente.delete("/fault/cpu").status_code == 200


@pytest.mark.parametrize("consulta", ["segundos=0", "segundos=601", "hilos=0", "hilos=5"])
def test_los_limites_de_duracion_e_hilos_se_respetan(cliente, consulta):
    respuesta = cliente.post(f"/fault/cpu?{consulta}", headers=CABECERA)
    assert respuesta.status_code == 422
    assert cliente.get("/fault/cpu").json()["activo"] is False


def test_en_la_api_real_apagada_la_ruta_no_existe():
    assert "/fault/cpu" not in app_real.openapi()["paths"]
    respuesta = TestClient(app_real).post("/fault/cpu", headers=CABECERA)
    assert respuesta.status_code == 404
