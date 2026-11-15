# La regla de detección de Services expuestos: debe saltar con los casos positivos y no con
# los negativos, que incluyen el flujo normal del despliegue.
import json
from pathlib import Path

import pytest

from seguridad.deteccion import reglas

CASOS = Path(__file__).parent.parent / "seguridad" / "deteccion" / "casos"


def _caso(nombre: str) -> dict:
    return json.loads((CASOS / nombre).read_text(encoding="utf-8"))


@pytest.mark.parametrize("archivo", sorted(p.name for p in CASOS.glob("positivo-*.json")))
def test_los_casos_positivos_disparan_la_regla(archivo):
    assert reglas.coincide(_caso(archivo))


@pytest.mark.parametrize("archivo", sorted(p.name for p in CASOS.glob("negativo-*.json")))
def test_los_casos_negativos_no_disparan_la_regla(archivo):
    assert not reglas.coincide(_caso(archivo))


def test_hay_casos_de_los_dos_tipos():
    assert list(CASOS.glob("positivo-*.json")) and list(CASOS.glob("negativo-*.json"))


def test_el_filtro_incluye_lo_que_evalua_la_regla():
    filtro = reglas.filtro()
    assert "io.k8s.core.v1.services.create" in filtro
    assert '("NodePort" OR "LoadBalancer")' in filtro
    assert reglas.SERVICE_LEGITIMO in filtro
