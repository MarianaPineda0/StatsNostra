# La readiness consciente de la saturación: apagada por defecto, 503 solo con
# umbral y retraso por encima, y liveness nunca se ve afectada.
from collections import deque

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


def _retraso(monkeypatch, valor_ms: float) -> None:
    monkeypatch.setattr(main.monitor, "_muestras", deque([valor_ms], maxlen=10))


def test_sin_umbral_la_readiness_responde_200_aunque_haya_retraso(monkeypatch):
    monkeypatch.setattr(main.settings, "readiness_lag_ms", 0)
    _retraso(monkeypatch, 5000)
    respuesta = client.get("/health/ready")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_con_umbral_y_retraso_por_encima_responde_503_y_dice_cuanto(monkeypatch):
    monkeypatch.setattr(main.settings, "readiness_lag_ms", 100)
    _retraso(monkeypatch, 250.4)
    respuesta = client.get("/health/ready")
    assert respuesta.status_code == 503
    assert respuesta.json() == {"status": "saturado", "lag_ms": 250.4}


def test_con_umbral_y_retraso_por_debajo_sigue_en_200(monkeypatch):
    monkeypatch.setattr(main.settings, "readiness_lag_ms", 100)
    _retraso(monkeypatch, 40)
    assert client.get("/health/ready").status_code == 200


def test_un_retraso_justo_en_el_umbral_no_saca_al_pod(monkeypatch):
    monkeypatch.setattr(main.settings, "readiness_lag_ms", 100)
    _retraso(monkeypatch, 100)
    assert client.get("/health/ready").status_code == 200


@pytest.mark.parametrize("ruta", ["/health", "/health/live"])
def test_liveness_y_health_no_dependen_de_la_saturacion(monkeypatch, ruta):
    monkeypatch.setattr(main.settings, "readiness_lag_ms", 100)
    _retraso(monkeypatch, 9000)
    assert client.get(ruta).status_code == 200


def test_la_api_arranca_y_detiene_el_medidor_con_su_ciclo_de_vida():
    with TestClient(app) as cliente:
        cliente.get("/health/live")
        assert main.monitor._tarea is not None
    assert main.monitor._tarea is None


def test_el_retraso_se_expone_como_metrica():
    cuerpo = client.get("/metrics").text
    assert "statsnostra_event_loop_lag_ms" in cuerpo
