# El consumidor de CPU del experimento: consume de verdad, tiene plazo y se puede
# parar. Si alguna de las tres falla, el experimento no sería seguro de correr.
import time

import pytest

from app.core.consumo_cpu import ConsumidorCPU, ConsumoEnCurso


@pytest.fixture()
def consumidor():
    c = ConsumidorCPU()
    yield c
    c.detener()  # que ninguna prueba deje hilos quemando CPU


def test_arranca_activo_y_se_detiene_al_pedirlo(consumidor):
    consumidor.iniciar(segundos=30)
    assert consumidor.estado()["activo"] is True

    assert consumidor.detener() is True
    assert consumidor.estado() == {"activo": False, "segundos_restantes": 0.0}


def test_se_detiene_solo_al_cumplirse_el_plazo(consumidor):
    consumidor.iniciar(segundos=1)
    time.sleep(1.5)
    assert consumidor.estado()["activo"] is False


def test_no_deja_iniciar_dos_consumos_a_la_vez(consumidor):
    consumidor.iniciar(segundos=30)
    with pytest.raises(ConsumoEnCurso):
        consumidor.iniciar(segundos=30)


def test_detener_sin_consumo_en_curso_avisa_que_no_habia(consumidor):
    assert consumidor.detener() is False


def test_realmente_consume_cpu_del_proceso(consumidor):
    antes = time.process_time()
    consumidor.iniciar(segundos=5)
    time.sleep(0.6)
    consumido = time.process_time() - antes
    consumidor.detener()
    # Con un hilo ocupado, casi todo el tiempo transcurrido es CPU
    assert consumido > 0.2


def test_despues_de_parar_el_proceso_deja_de_consumir(consumidor):
    consumidor.iniciar(segundos=5)
    time.sleep(0.2)
    consumidor.detener()

    antes = time.process_time()
    time.sleep(0.5)
    assert time.process_time() - antes < 0.15
