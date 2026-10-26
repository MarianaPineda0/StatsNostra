# Pruebas de la inyeccion de fallos: la cabecera se interpreta bien, el
# middleware falla o demora solo cuando se le pide, y esta apagado por defecto.
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.fallos import FAULT_HEADER, InyeccionFallosMiddleware, interpretar


def _app_con_fallos():
    app = FastAPI()
    app.add_middleware(InyeccionFallosMiddleware)

    @app.get("/api/prueba")
    def prueba():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return TestClient(app)


def test_interpretar_error_y_latencia():
    assert interpretar("error=0.3;latency=250") == (0.3, 250)
    assert interpretar("latency=100") == (0.0, 100)
    assert interpretar("error=1") == (1.0, 0)


def test_interpretar_ignora_lo_que_no_entiende():
    assert interpretar("basura") == (0.0, 0)
    assert interpretar("error=abc;latency=x") == (0.0, 0)
    assert interpretar("") == (0.0, 0)


def test_interpretar_limita_los_valores():
    assert interpretar("error=7") == (1.0, 0)
    assert interpretar("error=-3") == (0.0, 0)
    assert interpretar("latency=999999") == (0.0, 5000)


def test_sin_cabecera_no_pasa_nada():
    assert _app_con_fallos().get("/api/prueba").status_code == 200


def test_error_total_devuelve_500():
    respuesta = _app_con_fallos().get("/api/prueba", headers={FAULT_HEADER: "error=1"})
    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Fallo inyectado"}


def test_error_cero_nunca_falla():
    cliente = _app_con_fallos()
    for _ in range(20):
        assert cliente.get("/api/prueba", headers={FAULT_HEADER: "error=0"}).status_code == 200


def test_la_latencia_demora_la_respuesta():
    cliente = _app_con_fallos()
    inicio = time.perf_counter()
    respuesta = cliente.get("/api/prueba", headers={FAULT_HEADER: "latency=200"})
    assert respuesta.status_code == 200
    # Margen para el temporizador de Windows, que a veces despierta unos ms antes
    assert time.perf_counter() - inicio >= 0.15


def test_health_queda_fuera_de_la_inyeccion():
    respuesta = _app_con_fallos().get("/health", headers={FAULT_HEADER: "error=1"})
    assert respuesta.status_code == 200


def test_en_la_app_real_esta_apagada_por_defecto(client):
    # FAULT_INJECTION no esta activa en pruebas: la cabecera no tiene efecto
    respuesta = client.get("/api/v1/apostadores", headers={FAULT_HEADER: "error=1"})
    assert respuesta.status_code == 200
