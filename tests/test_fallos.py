# Interruptor de fallos del grupo: X-Inject-Fault con error o latency, apagado
# por defecto y sin tocar nunca las rutas de salud.
import time

from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.core.fallos import FAULT_HEADER, InyeccionFallosMiddleware, fallos_pedidos
from app.main import app as app_real


def _app(tasa_error: float, latencia_ms: int = 0) -> TestClient:
    def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/api/datos", ok), Route("/health/ready", ok)])
    app.add_middleware(
        InyeccionFallosMiddleware, tasa_error=tasa_error, latencia_ms=latencia_ms
    )
    return TestClient(app)


def test_se_entiende_error_latency_y_su_combinacion():
    assert fallos_pedidos("error") == {"error"}
    assert fallos_pedidos("latency") == {"latency"}
    assert fallos_pedidos("ERROR; latency") == {"error", "latency"}
    assert fallos_pedidos("") == set()


def test_con_error_y_tasa_total_toda_peticion_falla_con_500():
    respuesta = _app(tasa_error=1.0).get("/api/datos", headers={FAULT_HEADER: "error"})
    assert respuesta.status_code == 500


def test_con_tasa_cero_nunca_falla():
    cliente = _app(tasa_error=0.0)
    codigos = {
        cliente.get("/api/datos", headers={FAULT_HEADER: "error"}).status_code
        for _ in range(20)
    }
    assert codigos == {200}


def test_sin_la_cabecera_todo_responde_normal():
    assert _app(tasa_error=1.0, latencia_ms=500).get("/api/datos").status_code == 200


def test_con_latency_la_respuesta_se_demora_lo_configurado():
    cliente = _app(tasa_error=0.0, latencia_ms=300)
    inicio = time.perf_counter()
    respuesta = cliente.get("/api/datos", headers={FAULT_HEADER: "latency"})
    assert respuesta.status_code == 200
    assert time.perf_counter() - inicio >= 0.25


def test_las_rutas_de_salud_nunca_reciben_fallos():
    cliente = _app(tasa_error=1.0, latencia_ms=500)
    inicio = time.perf_counter()
    respuesta = cliente.get("/health/ready", headers={FAULT_HEADER: "error,latency"})
    assert respuesta.status_code == 200
    assert time.perf_counter() - inicio < 0.4


def test_en_la_api_real_el_interruptor_viene_apagado():
    # Sin FAULT_HEADER_ENABLED=true la cabecera no hace nada
    respuesta = TestClient(app_real).get("/health", headers={FAULT_HEADER: "error"})
    assert respuesta.status_code == 200
