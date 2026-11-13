# El medidor de saturación: poco retraso con el bucle libre, mucho cuando algo lo
# bloquea, y un valor que se recupera cuando el bloqueo pasa.
import asyncio
import time

from app.core.saturacion import MonitorSaturacion


def _correr(escenario):
    return asyncio.run(escenario())


def test_con_el_bucle_libre_el_retraso_es_pequeno():
    async def escenario():
        monitor = MonitorSaturacion(intervalo=0.02)
        monitor.iniciar()
        await asyncio.sleep(0.4)
        retraso = monitor.lag_ms
        await monitor.detener()
        return retraso

    assert _correr(escenario) < 60


def test_un_bloqueo_del_bucle_se_nota_en_el_retraso():
    async def escenario():
        monitor = MonitorSaturacion(intervalo=0.02)
        monitor.iniciar()
        await asyncio.sleep(0.1)
        time.sleep(0.3)  # bloquea el bucle, como lo haría un hilo que acapara la CPU
        await asyncio.sleep(0.05)
        retraso = monitor.lag_ms
        await monitor.detener()
        return retraso

    assert _correr(escenario) > 200


def test_el_valor_se_recupera_cuando_el_bloqueo_pasa():
    async def escenario():
        monitor = MonitorSaturacion(intervalo=0.02, muestras=5)
        monitor.iniciar()
        await asyncio.sleep(0.05)
        time.sleep(0.25)
        await asyncio.sleep(0.05)
        durante = monitor.lag_ms
        await asyncio.sleep(0.5)  # más que las 5 muestras de 20 ms de la ventana
        despues = monitor.lag_ms
        await monitor.detener()
        return durante, despues

    durante, despues = _correr(escenario)
    assert durante > 200
    assert despues < 60


def test_iniciar_dos_veces_no_crea_dos_medidores():
    async def escenario():
        monitor = MonitorSaturacion(intervalo=0.02)
        monitor.iniciar()
        primera = monitor._tarea
        monitor.iniciar()
        misma = monitor._tarea is primera
        await monitor.detener()
        return misma

    assert _correr(escenario) is True


def test_sin_iniciar_el_retraso_es_cero():
    assert MonitorSaturacion().lag_ms == 0.0
