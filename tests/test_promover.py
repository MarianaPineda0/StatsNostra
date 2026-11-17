# Pruebas del orquestador de etapas con un entorno falso: se comprueba que
# promueve cuando todo va bien y que aborta (dejando todo en la estable)
# cuando una etapa falla, sin tocar GCP.
from pathlib import Path

import yaml

from canary.gate import Medicion
from canary.promover import SALIDA_ABORTADO, SALIDA_OK, Entorno, promover

SLO = yaml.safe_load(
    (Path(__file__).parent.parent / "canary" / "slo.yaml").read_text(encoding="utf-8")
)
ESTABLE, CANARY = "rev-estable", "rev-canary"


def _sana(**cambios) -> Medicion:
    base = {"peticiones": 500, "errores_5xx": 0, "p50_ms": 60, "p95_ms": 200, "p99_ms": 400}
    return Medicion(**{**base, **cambios})


class EntornoFalso:
    """Registra lo que el orquestador hace y entrega mediciones preparadas."""

    def __init__(self, mediciones):
        self.mediciones = list(mediciones)  # una (canary, estable) por evaluacion
        self.trafico, self.cargas, self.esperas = [], [], []

    def entorno(self) -> Entorno:
        return Entorno(
            fijar_trafico=lambda reparto: self.trafico.append(dict(reparto)),
            generar_carga=self.cargas.append,
            medir=lambda ventana: self.mediciones.pop(0),
            dormir=self.esperas.append,
        )


def _correr(mediciones, etapas=(10, 50, 100)):
    falso = EntornoFalso(mediciones)
    salida = promover(
        SLO, list(etapas), 3, 90, CANARY, ESTABLE, falso.entorno(), log=lambda _: None
    )
    return salida, falso


def test_canary_sano_llega_al_100_por_ciento():
    salida, falso = _correr([(_sana(), _sana())] * 3)
    assert salida == SALIDA_OK
    assert falso.trafico == [
        {ESTABLE: 90, CANARY: 10},
        {ESTABLE: 50, CANARY: 50},
        {ESTABLE: 0, CANARY: 100},
    ]


def test_cada_etapa_hornea_el_tiempo_pedido():
    _, falso = _correr([(_sana(), _sana())] * 3)
    assert falso.cargas == [180, 180, 180]  # 3 minutos por etapa


def test_falla_en_la_primera_etapa_aborta_y_vuelve_a_la_estable():
    falla = _sana(peticiones=200, errores_5xx=100)  # 50 % de errores
    salida, falso = _correr([(falla, _sana())])
    assert salida == SALIDA_ABORTADO
    assert falso.trafico[-1] == {ESTABLE: 100, CANARY: 0}
    assert len(falso.trafico) == 2  # subio al 10 % y volvio atras, sin pasar a la siguiente


def test_falla_en_una_etapa_posterior_tambien_aborta():
    falla = _sana(p95_ms=2500)
    salida, falso = _correr([(_sana(), _sana()), (falla, _sana(p95_ms=2400))])
    assert salida == SALIDA_ABORTADO
    assert falso.trafico[-1] == {ESTABLE: 100, CANARY: 0}
    assert falso.trafico[0] == {ESTABLE: 90, CANARY: 10}


def test_pausa_por_poca_muestra_y_luego_promueve():
    poca = _sana(peticiones=20)
    salida, falso = _correr([(poca, _sana()), (_sana(), _sana())], etapas=(10,))
    assert salida == SALIDA_OK
    # horneado de 180 s y luego una carga extra de la pausa antes de reevaluar
    assert falso.cargas == [180, SLO["pausa"]["espera_segundos"]]


def test_pausa_que_no_se_resuelve_termina_en_aborto():
    poca = _sana(peticiones=20)
    reintentos = SLO["pausa"]["reintentos_max"]
    salida, falso = _correr([(poca, _sana())] * (reintentos + 1), etapas=(10,))
    assert salida == SALIDA_ABORTADO
    assert falso.trafico[-1] == {ESTABLE: 100, CANARY: 0}


def test_espera_a_que_las_metricas_lleguen_antes_de_medir():
    _, falso = _correr([(_sana(), _sana())], etapas=(10,))
    assert falso.esperas == [90]


def test_en_el_100_por_ciento_no_se_compara_con_la_estable():
    # En la etapa final la estable trae datos viejos de las etapas anteriores,
    # con un p95 mucho menor; comparar contra eso abortaria un canary sano
    vieja = _sana(p95_ms=30)
    canary_sano = _sana(p95_ms=120)
    salida, falso = _correr([(canary_sano, vieja)], etapas=(100,))
    assert salida == SALIDA_OK
    assert falso.trafico == [{ESTABLE: 0, CANARY: 100}]


def test_la_ventana_de_medicion_deja_fuera_el_calentamiento():
    ventanas = []
    falso = EntornoFalso([(_sana(), _sana())])
    entorno = falso.entorno()
    entorno.medir = lambda ventana: (ventanas.append(ventana), falso.mediciones.pop(0))[1]
    promover(SLO, [10], 3, 90, CANARY, ESTABLE, entorno, log=lambda _: None)
    # 3 min de carga + 90 s de espera - 90 s de calentamiento = 3 min medidos
    assert ventanas == [3]
