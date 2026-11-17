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


def test_estable_sin_trafico_no_sirve_de_linea_base():
    # Caso real de la etapa del 100 %: la estable ya no atiende nada y su p95
    # sale de una muestra vacia; no debe provocar un aborto del canary sano
    estable_sin_trafico = _sana(peticiones=0, p95_ms=23)
    decision, _ = decidir(SLO, _sana(p95_ms=111), estable_sin_trafico)
    assert decision == PROMOVER


def test_con_poca_muestra_en_la_estable_se_juzga_solo_por_los_limites_absolutos():
    decision, _ = decidir(SLO, _sana(p95_ms=300), _sana(peticiones=40, p95_ms=50))
    assert decision == PROMOVER


def test_los_limites_absolutos_siguen_valiendo_sin_linea_base():
    decision, _ = decidir(SLO, _sana(p95_ms=2500), _sana(peticiones=0))
    assert decision == ABORTAR


def test_diferencia_relativa_sin_diferencia_absoluta_no_cuenta():
    # Caso real de la etapa del 50 %: 110 ms contra 29 ms es casi 4 veces,
    # pero ambos estan lejos del limite y nadie notaria 80 ms de diferencia
    decision, _ = decidir(SLO, _sana(p95_ms=110), _sana(p95_ms=29))
    assert decision == PROMOVER


def test_regresion_de_verdad_sigue_abortando():
    # 900 ms contra 200 ms: 4,5 veces y 700 ms de diferencia
    decision, razones = decidir(SLO, _sana(p95_ms=900), _sana(p95_ms=200))
    assert decision == ABORTAR
    assert any("estable" in r for r in razones)


def test_relacion_alta_con_diferencia_moderada_pausa_pero_no_aborta():
    # 250 ms contra 90 ms: 2,8 veces, 160 ms de diferencia. Supera lo que
    # permite promover (1,5 veces y 150 ms) pero no el limite de abortar
    decision, _ = decidir(SLO, _sana(p95_ms=250), _sana(p95_ms=90))
    assert decision == PAUSAR


def test_caida_moderada_de_aciertos_pausa():
    # 75 % contra 100 % de la estable: cae 25 puntos, mas que lo que deja
    # promover (15) pero menos que lo que obliga a abortar (30)
    decision, razones = decidir(
        SLO, _sana(evaluadas=40, aciertos=30), _sana(evaluadas=40, aciertos=40)
    )
    assert decision == PAUSAR
    assert any("aciertos" in r for r in razones)


def test_caida_fuerte_de_aciertos_aborta():
    # 10 % contra 50 % de la estable: cae 40 puntos
    decision, razones = decidir(
        SLO, _sana(evaluadas=40, aciertos=4), _sana(evaluadas=40, aciertos=20)
    )
    assert decision == ABORTAR
    assert any("aciertos" in r for r in razones)


def test_aciertos_iguales_a_la_estable_no_bloquean():
    decision, _ = decidir(
        SLO, _sana(evaluadas=40, aciertos=20), _sana(evaluadas=40, aciertos=20)
    )
    assert decision == PROMOVER


def test_con_pocas_evaluaciones_la_metrica_de_negocio_no_decide():
    decision, _ = decidir(
        SLO, _sana(evaluadas=5, aciertos=0), _sana(evaluadas=40, aciertos=20)
    )
    assert decision == PROMOVER


def test_canary_hasta_una_vez_y_media_la_estable_se_promueve():
    decision, _ = decidir(SLO, _sana(p95_ms=600, p99_ms=900), _sana(p95_ms=420, p99_ms=600))
    assert decision == PROMOVER


def test_canary_mas_de_una_vez_y_media_la_estable_pausa():
    decision, razones = decidir(SLO, _sana(p95_ms=700, p99_ms=1100), _sana(p95_ms=250))
    assert decision == PAUSAR
    assert any("relativo" in r for r in razones)
