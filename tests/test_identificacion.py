# Contrato del grupo: cada respuesta dice que API la atendio y con que version.
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)
settings = get_settings()


def test_la_respuesta_trae_nombre_y_version_de_la_api():
    respuesta = client.get("/health")
    assert respuesta.headers["X-App-Name"] == settings.app_id
    assert respuesta.headers["X-App-Version"] == settings.app_version


def test_los_errores_tambien_se_identifican():
    respuesta = client.get("/ruta-que-no-existe")
    assert respuesta.status_code == 404
    assert respuesta.headers["X-App-Name"] == settings.app_id


def test_el_trace_id_sigue_volviendo_en_la_respuesta():
    respuesta = client.get("/health", headers={"X-Trace-Id": "k6-1-7"})
    assert respuesta.headers["X-Trace-Id"] == "k6-1-7"
