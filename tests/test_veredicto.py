# El veredicto de una ronda: cumple solo si el éxito y el p95 respetan el estado
# estable declarado, y dice por qué cuando no.
import importlib.util
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ / "caos" / "carga"))
_spec = importlib.util.spec_from_file_location(
    "veredicto", RAIZ / "caos" / "carga" / "veredicto.py"
)
veredicto = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(veredicto)


def _corrida(exito=1.0, p95=1000.0, peticiones=3000) -> dict:
    return {"exito": exito, "p95_ms": p95, "peticiones": peticiones}


def test_cumple_cuando_exito_y_p95_estan_dentro_del_estado_estable():
    resultado = veredicto.evaluar(_corrida(exito=1.0, p95=1400), x_ms=1511)
    assert resultado["cumple"] is True
    assert resultado["motivos"] == []


def test_un_p95_por_encima_de_x_refuta_la_hipotesis_y_dice_cuanto():
    resultado = veredicto.evaluar(_corrida(p95=3022), x_ms=1511)
    assert resultado["cumple"] is False
    assert resultado["sobre_x_pct"] == 100.0
    assert "p95 3022 ms > X 1511 ms" in resultado["motivos"]


def test_un_exito_por_debajo_del_99_por_ciento_tambien_la_refuta():
    resultado = veredicto.evaluar(_corrida(exito=0.93), x_ms=1511)
    assert resultado["cumple"] is False
    assert any("éxito 93.00 %" in m or "éxito 93.00%" in m for m in resultado["motivos"])


def test_si_fallan_las_dos_cosas_se_listan_las_dos():
    resultado = veredicto.evaluar(_corrida(exito=0.5, p95=9000), x_ms=1511)
    assert len(resultado["motivos"]) == 2


def test_con_la_base_del_estado_estable_calcula_la_variacion_del_p95():
    resultado = veredicto.evaluar(_corrida(p95=2416), x_ms=1511, base_p95_ms=1208)
    assert resultado["p95_estado_estable_ms"] == 1208
    assert resultado["variacion_p95_pct"] == 100.0


def test_el_veredicto_se_puede_serializar_como_una_linea_json():
    resultado = veredicto.evaluar(_corrida(), x_ms=1511, base_p95_ms=1208)
    assert json.loads(json.dumps(resultado, ensure_ascii=False))["cumple"] is True
