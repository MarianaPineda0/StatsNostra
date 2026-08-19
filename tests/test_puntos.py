# Pruebas unitarias puras del sistema de puntos (sin BD, sin HTTP): cubren
# los 3 casos de la regla (exacto=3, resultado correcto=1, incorrecto=0)
# y el caso especial de empate.
from app.services.puntos import calcular_puntos


def test_marcador_exacto_da_tres_puntos():
    acertada, puntos = calcular_puntos(2, 1, 2, 1)
    assert acertada is True
    assert puntos == 3


def test_resultado_correcto_marcador_incorrecto_da_un_punto():
    acertada, puntos = calcular_puntos(3, 0, 2, 1)
    assert acertada is True
    assert puntos == 1


def test_resultado_incorrecto_da_cero_puntos():
    acertada, puntos = calcular_puntos(0, 2, 2, 1)
    assert acertada is False
    assert puntos == 0


def test_empate_predicho_y_empate_real_da_un_punto():
    acertada, puntos = calcular_puntos(1, 1, 2, 2)
    assert acertada is True
    assert puntos == 1


def test_empate_exacto_da_tres_puntos():
    acertada, puntos = calcular_puntos(1, 1, 1, 1)
    assert acertada is True
    assert puntos == 3
