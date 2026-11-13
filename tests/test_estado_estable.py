# El resumen del estado estable: mediana entre corridas (no promedio), umbral X con
# su margen, y lectura del formato real de k6.
import importlib.util
import json
from pathlib import Path

RAIZ = Path(__file__).parent.parent
_spec = importlib.util.spec_from_file_location(
    "resumen", RAIZ / "caos" / "carga" / "resumen.py"
)
resumen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(resumen)


def _corrida(p50=300.0, p95=500.0, p99=700.0, fallos=0.0, peticiones=1000, rps=15.0) -> dict:
    return {
        "corrida": "1",
        "peticiones": peticiones,
        "throughput_rps": rps,
        "exito": 1 - fallos,
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
    }


def test_el_umbral_es_el_p95_mediano_mas_el_margen():
    corridas = [_corrida(p95=400), _corrida(p95=500), _corrida(p95=600)]
    estado = resumen.declarar(corridas, margen=0.25)
    assert estado["mediana"]["p95_ms"] == 500
    assert estado["x_ms"] == 625


def test_una_corrida_rara_no_mueve_el_umbral():
    # El promedio de estos p95 sería 2.333; la mediana ignora el arranque en frío
    corridas = [_corrida(p95=500), _corrida(p95=520), _corrida(p95=6000)]
    assert resumen.declarar(corridas)["mediana"]["p95_ms"] == 520


def test_la_declaracion_nombra_exito_p95_y_cantidad_de_corridas():
    corridas = [_corrida(p95=400), _corrida(p95=500), _corrida(p95=600)]
    texto = resumen.declarar(corridas)["declaracion"]
    assert "p95 <= 625 ms" in texto and "3 corridas" in texto and "éxito >= 99 %" in texto


def test_el_exito_es_el_complemento_de_la_tasa_de_fallos(tmp_path):
    k6 = {
        "metrics": {
            "http_req_duration": {"med": 355.6, "p(95)": 384.7, "p(99)": 485.6},
            "http_req_failed": {"passes": 2, "fails": 98, "value": 0.02},
            "http_reqs": {"count": 100, "rate": 12.5},
        }
    }
    ruta = tmp_path / "corrida-2.json"
    ruta.write_text(json.dumps(k6), encoding="utf-8")
    corrida = resumen.leer_corrida(ruta)
    assert corrida["corrida"] == "2"
    assert corrida["exito"] == 0.98
    assert corrida["p95_ms"] == 384.7 and corrida["peticiones"] == 100
