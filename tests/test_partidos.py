# Pruebas del CRUD de Partido, la validacion de equipos/resultados, y la
# finalizacion (incluyendo el bloqueo de finalizar dos veces, regla 6).


def _crear_partido(client, local="Millonarios", visitante="Nacional"):
    return client.post(
        "/partidos",
        json={
            "deporte": "Futbol",
            "liga": "Liga X",
            "equipo_local": local,
            "equipo_visitante": visitante,
            "fecha_hora": "2026-09-01T20:00:00Z",
        },
    )


def test_crear_partido(client):
    respuesta = _crear_partido(client)
    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "PROGRAMADO"


def test_crear_partido_equipos_iguales(client):
    respuesta = _crear_partido(client, local="Millonarios", visitante="Millonarios")
    assert respuesta.status_code == 422


def test_listar_partidos(client):
    creado = _crear_partido(client).json()
    ids = [p["id"] for p in client.get("/partidos").json()]
    assert creado["id"] in ids


def test_obtener_partido(client):
    creado = _crear_partido(client).json()
    respuesta = client.get(f"/partidos/{creado['id']}")
    assert respuesta.status_code == 200


def test_obtener_partido_inexistente(client):
    assert client.get("/partidos/999").status_code == 404


def test_actualizar_partido(client):
    creado = _crear_partido(client).json()
    respuesta = client.put(f"/partidos/{creado['id']}", json={"liga": "Liga Y"})
    assert respuesta.status_code == 200
    assert respuesta.json()["liga"] == "Liga Y"


def test_eliminar_partido(client):
    creado = _crear_partido(client).json()
    assert client.delete(f"/partidos/{creado['id']}").status_code == 204
    assert client.get(f"/partidos/{creado['id']}").status_code == 404


def test_finalizar_partido(client):
    creado = _crear_partido(client).json()
    respuesta = client.post(
        f"/partidos/{creado['id']}/finalizar",
        json={"resultado_local": 2, "resultado_visitante": 1},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "FINALIZADO"


def test_finalizar_partido_dos_veces(client):
    creado = _crear_partido(client).json()
    client.post(
        f"/partidos/{creado['id']}/finalizar",
        json={"resultado_local": 2, "resultado_visitante": 1},
    )
    respuesta = client.post(
        f"/partidos/{creado['id']}/finalizar",
        json={"resultado_local": 3, "resultado_visitante": 0},
    )
    assert respuesta.status_code == 400


def test_finalizar_partido_resultado_negativo(client):
    creado = _crear_partido(client).json()
    respuesta = client.post(
        f"/partidos/{creado['id']}/finalizar",
        json={"resultado_local": -1, "resultado_visitante": 0},
    )
    assert respuesta.status_code == 422
