# Pruebas del CRUD de Prediccion y de las 5 reglas de negocio: apostador
# existente/activo, partido existente/no finalizado, sin predicciones
# duplicadas (mismo apostador + mismo partido).


def _crear_apostador(client, username="pred01", email="pred01@example.com", activo=True):
    creado = client.post(
        "/apostadores",
        json={"nombre": "Apostador Test", "username": username, "email": email},
    ).json()
    if not activo:
        client.put(f"/apostadores/{creado['id']}", json={"activo": False})
    return creado


def _crear_partido(client):
    return client.post(
        "/partidos",
        json={
            "deporte": "Futbol",
            "liga": "Liga X",
            "equipo_local": "Millonarios",
            "equipo_visitante": "Nacional",
            "fecha_hora": "2026-09-01T20:00:00Z",
        },
    ).json()


def _crear_prediccion(client, apostador_id, partido_id, gl=2, gv=1):
    return client.post(
        "/predicciones",
        json={
            "apostador_id": apostador_id,
            "partido_id": partido_id,
            "goles_local_pred": gl,
            "goles_visitante_pred": gv,
        },
    )


def test_crear_prediccion(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    respuesta = _crear_prediccion(client, apostador["id"], partido["id"])
    assert respuesta.status_code == 201
    assert respuesta.json()["acertada"] is None


def test_listar_predicciones(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    creada = _crear_prediccion(client, apostador["id"], partido["id"]).json()
    ids = [p["id"] for p in client.get("/predicciones").json()]
    assert creada["id"] in ids


def test_obtener_prediccion(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    creada = _crear_prediccion(client, apostador["id"], partido["id"]).json()
    assert client.get(f"/predicciones/{creada['id']}").status_code == 200


def test_obtener_prediccion_inexistente(client):
    assert client.get("/predicciones/999").status_code == 404


def test_actualizar_prediccion(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    creada = _crear_prediccion(client, apostador["id"], partido["id"]).json()
    respuesta = client.put(f"/predicciones/{creada['id']}", json={"goles_local_pred": 3})
    assert respuesta.status_code == 200
    assert respuesta.json()["goles_local_pred"] == 3


def test_actualizar_prediccion_con_patch(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    creada = _crear_prediccion(client, apostador["id"], partido["id"]).json()
    respuesta = client.patch(f"/predicciones/{creada['id']}", json={"goles_local_pred": 3})
    assert respuesta.status_code == 200
    assert respuesta.json()["goles_local_pred"] == 3


def test_eliminar_prediccion(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    creada = _crear_prediccion(client, apostador["id"], partido["id"]).json()
    assert client.delete(f"/predicciones/{creada['id']}").status_code == 204
    assert client.get(f"/predicciones/{creada['id']}").status_code == 404


def test_prediccion_apostador_inexistente(client):
    partido = _crear_partido(client)
    respuesta = _crear_prediccion(client, 999, partido["id"])
    assert respuesta.status_code == 404


def test_prediccion_partido_inexistente(client):
    apostador = _crear_apostador(client)
    respuesta = _crear_prediccion(client, apostador["id"], 999)
    assert respuesta.status_code == 404


def test_prediccion_apostador_inactivo(client):
    apostador = _crear_apostador(client, activo=False)
    partido = _crear_partido(client)
    respuesta = _crear_prediccion(client, apostador["id"], partido["id"])
    assert respuesta.status_code == 400


def test_prediccion_partido_finalizado(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    client.post(
        f"/partidos/{partido['id']}/finalizar",
        json={"resultado_local": 1, "resultado_visitante": 0},
    )
    respuesta = _crear_prediccion(client, apostador["id"], partido["id"])
    assert respuesta.status_code == 400


def test_prediccion_duplicada(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    _crear_prediccion(client, apostador["id"], partido["id"])
    respuesta = _crear_prediccion(client, apostador["id"], partido["id"])
    assert respuesta.status_code == 409
