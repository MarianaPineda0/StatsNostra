# La regla de la credencial señuelo: salta solo cuando alguien abre ese secreto.
import json
from pathlib import Path

import pytest

from seguridad.deteccion import reglas

CASOS = Path(__file__).parent.parent / "seguridad" / "deteccion" / "casos"


def _caso(nombre: str) -> dict:
    return json.loads((CASOS / nombre).read_text(encoding="utf-8"))


def test_abrir_el_senuelo_dispara_la_regla():
    assert reglas.CREDENCIAL_SENUELO.coincide(_caso("senuelo-positivo-lectura.json"))


@pytest.mark.parametrize(
    "archivo", sorted(p.name for p in CASOS.glob("senuelo-negativo-*.json"))
)
def test_lo_demas_no_dispara_la_regla(archivo):
    assert not reglas.CREDENCIAL_SENUELO.coincide(_caso(archivo))


def test_el_filtro_apunta_al_secreto_senuelo():
    filtro = reglas.CREDENCIAL_SENUELO.filtro()
    assert reglas.SECRETO_SENUELO in filtro
    assert "AccessSecretVersion" in filtro
    assert 'log_id("cloudaudit.googleapis.com/data_access")' in filtro


def test_las_dos_reglas_no_se_confunden():
    assert not reglas.SERVICE_EXPUESTO.coincide(_caso("senuelo-positivo-lectura.json"))
    assert not reglas.CREDENCIAL_SENUELO.coincide(_caso("positivo-nodeport-9090.json"))
