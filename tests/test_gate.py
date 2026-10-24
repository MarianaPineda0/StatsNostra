# Pruebas de la puerta de calidad del canary: la decision sale de los umbrales
# de canary/slo.yaml, no de un criterio escrito aparte en el codigo.
from pathlib import Path

import pytest
import yaml

from canary.gate import ABORTAR, PAUSAR, PROMOVER, Medicion, decidir

SLO = yaml.safe_load(
    (Path(__file__).parent.parent / "canary" / "slo.yaml").read_text(encoding="utf-8")
)


def _sana(**cambios) -> Medicion:
    base = {
        "peticiones": 500,
        "errores_5xx": 1,
        "p50_ms": 60,
        "p95_ms": 200,
        "p99_ms": 400,
        "cpu": 0.30,
        "memoria": 0.40,
    }
    return Medicion(**{**base, **cambios})


def test_canary_sano_se_promueve():
    decision, razones = decidir(SLO, _sana(), _sana())
    assert decision == PROMOVER
    assert razones


def test_poca_muestra_pausa_aunque_todo_se_vea_bien():
    decision, razones = decidir(SLO, _sana(peticiones=30, errores_5xx=0), _sana())
    assert decision == PAUSAR
    assert "muestra insuficiente" in razones[0]


def test_muchos_errores_abortan():
    decision, razones = decidir(SLO, _sana(errores_5xx=100), _sana())  # 20 %
    assert decision == ABORTAR
    assert any("5xx" in r for r in razones)


def test_latencia_muy_alta_aborta():
    decision, _ = decidir(SLO, _sana(p95_ms=2500), _sana(p95_ms=2400))
    assert decision == ABORTAR


def test_latencia_triple_que_la_estable_aborta():
    decision, razones = decidir(SLO, _sana(p95_ms=900), _sana(p95_ms=200))
    assert decision == ABORTAR
    assert any("estable" in r for r in razones)


def test_error_moderado_pausa_en_vez_de_abortar():
    # 3 % de errores: supera lo que permite promover (1 %) pero no el 5 % de abortar
    decision, razones = decidir(SLO, _sana(errores_5xx=15), _sana())
    assert decision == PAUSAR
    assert any("5xx" in r for r in razones)


def test_cpu_saturada_impide_promover():
    decision, razones = decidir(SLO, _sana(cpu=0.95), _sana())
    assert decision == PAUSAR
    assert any("CPU" in r for r in razones)


def test_mas_errores_que_la_estable_pausa():
    # 1 % en el canary contra 0 % en la estable: dentro del 1 % absoluto pero
    # por encima del margen relativo permitido
    decision, razones = decidir(SLO, _sana(errores_5xx=5), _sana(errores_5xx=0))
    assert decision == PAUSAR
    assert any("estable" in r for r in razones)


def test_sin_datos_de_la_estable_no_se_inventa_una_violacion():
    decision, _ = decidir(SLO, _sana(), Medicion())
    assert decision == PROMOVER


@pytest.mark.parametrize(
    ("errores", "esperado"), [(0, PROMOVER), (2, PROMOVER), (10, PAUSAR), (40, ABORTAR)]
)
def test_escalera_de_errores(errores, esperado):
    # 500 peticiones: 0.4 %, 2 %, 8 % de errores
    assert decidir(SLO, _sana(errores_5xx=errores), _sana(errores_5xx=0))[0] == esperado
