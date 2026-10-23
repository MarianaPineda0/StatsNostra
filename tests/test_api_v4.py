# Pruebas de las rutas /api/v4: nivel de confianza en las predicciones y
# compatibilidad con las versiones anteriores del API.


def _crear_apostador(client, username="v4user", email="v4user@example.com"):
    return client.post(
        "/apostadores", json={"nombre": "Usuario V4", "username": username, "email": email}
    ).json()


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


def _preparar(client, **extra):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    cuerpo = {
        "apostador_id": apostador["id"],
        "partido_id": partido["id"],
        "goles_local_pred": 2,
        "goles_visitante_pred": 1,
        **extra,
    }
    return apostador, partido, cuerpo


def test_crear_prediccion_con_confianza(client):
    _, _, cuerpo = _preparar(client, confianza=4)
    respuesta = client.post("/api/v4/predicciones", json=cuerpo)
    assert respuesta.status_code == 201
    assert respuesta.json()["confianza"] == 4


def test_crear_prediccion_sin_confianza_queda_en_null(client):
    _, _, cuerpo = _preparar(client)
    respuesta = client.post("/api/v4/predicciones", json=cuerpo)
    assert respuesta.status_code == 201
    assert respuesta.json()["confianza"] is None


def test_confianza_fuera_de_rango_se_rechaza(client):
    _, _, cuerpo = _preparar(client)
    for valor in (0, 6, -1):
        respuesta = client.post("/api/v4/predicciones", json={**cuerpo, "confianza": valor})
        assert respuesta.status_code == 422, valor


def test_v4_mantiene_las_reglas_de_negocio(client):
    # La regla 5 (una prediccion por apostador y partido) sigue valiendo
    _, _, cuerpo = _preparar(client, confianza=3)
    assert client.post("/api/v4/predicciones", json=cuerpo).status_code == 201
    assert client.post("/api/v4/predicciones", json=cuerpo).status_code == 409


def test_listar_y_obtener_devuelven_la_confianza(client):
    _, _, cuerpo = _preparar(client, confianza=5)
    creada = client.post("/api/v4/predicciones", json=cuerpo).json()
    assert client.get(f"/api/v4/predicciones/{creada['id']}").json()["confianza"] == 5
    listado = {p["id"]: p["confianza"] for p in client.get("/api/v4/predicciones").json()}
    assert listado[creada["id"]] == 5


def test_actualizar_la_confianza(client):
    _, _, cuerpo = _preparar(client, confianza=2)
    creada = client.post("/api/v4/predicciones", json=cuerpo).json()
    respuesta = client.patch(f"/api/v4/predicciones/{creada['id']}", json={"confianza": 5})
    assert respuesta.status_code == 200
    assert respuesta.json()["confianza"] == 5
    assert respuesta.json()["goles_local_pred"] == 2


def test_v1_y_v2_siguen_igual_y_no_exponen_la_confianza(client):
    # Compatibilidad hacia atras: lo creado por v4 se lee por v1 sin romper
    _, _, cuerpo = _preparar(client, confianza=4)
    creada = client.post("/api/v4/predicciones", json=cuerpo).json()
    v1 = client.get(f"/api/v1/predicciones/{creada['id']}")
    assert v1.status_code == 200
    assert "confianza" not in v1.json()
