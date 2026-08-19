def _crear_apostador(client, username="query01", email="query01@example.com"):
    return client.post(
        "/apostadores",
        json={"nombre": "Apostador Query", "username": username, "email": email},
    ).json()


def _crear_partido(client, deporte="Futbol", liga="Liga X"):
    return client.post(
        "/partidos",
        json={
            "deporte": deporte,
            "liga": liga,
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
    ).json()


def test_query_predicciones_por_apostador(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    _crear_prediccion(client, apostador["id"], partido["id"])

    respuesta = client.request("QUERY", f"/query/apostadores/{apostador['id']}/predicciones")
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1


def test_query_predicciones_por_apostador_inexistente(client):
    respuesta = client.request("QUERY", "/query/apostadores/999/predicciones")
    assert respuesta.status_code == 404


def test_query_predicciones_por_partido(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    _crear_prediccion(client, apostador["id"], partido["id"])

    respuesta = client.request("QUERY", f"/query/partidos/{partido['id']}/predicciones")
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1


def test_query_estadisticas_apostador(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    _crear_prediccion(client, apostador["id"], partido["id"], gl=2, gv=1)
    client.post(
        f"/partidos/{partido['id']}/finalizar",
        json={"resultado_local": 2, "resultado_visitante": 1},
    )

    respuesta = client.request("QUERY", f"/query/apostadores/{apostador['id']}/estadisticas")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total_predicciones"] == 1
    assert cuerpo["predicciones_acertadas"] == 1
    assert cuerpo["puntos_totales"] == 3


def test_query_ranking(client):
    apostador = _crear_apostador(client)
    partido = _crear_partido(client)
    _crear_prediccion(client, apostador["id"], partido["id"], gl=2, gv=1)
    client.post(
        f"/partidos/{partido['id']}/finalizar",
        json={"resultado_local": 2, "resultado_visitante": 1},
    )

    respuesta = client.request("QUERY", "/query/apostadores/ranking")
    assert respuesta.status_code == 200
    ranking = respuesta.json()
    entrada = next(r for r in ranking if r["apostador_id"] == apostador["id"])
    assert entrada["puntos_totales"] == 3
    assert entrada["porcentaje_acierto"] == 100.0


def test_query_partidos_finalizados(client):
    partido = _crear_partido(client)
    client.post(
        f"/partidos/{partido['id']}/finalizar",
        json={"resultado_local": 1, "resultado_visitante": 0},
    )

    respuesta = client.request("QUERY", "/query/partidos/finalizados")
    assert respuesta.status_code == 200
    ids = [p["id"] for p in respuesta.json()]
    assert partido["id"] in ids


def test_query_partidos_con_filtro(client):
    _crear_partido(client, deporte="Futbol", liga="Liga X")
    creado = _crear_partido(client, deporte="Baloncesto Test QUERY", liga="Liga Y")

    respuesta = client.request(
        "QUERY", "/query/partidos", params={"deporte": "Baloncesto Test QUERY"}
    )
    assert respuesta.status_code == 200
    resultados = respuesta.json()
    assert all(r["deporte"] == "Baloncesto Test QUERY" for r in resultados)
    assert creado["id"] in [r["id"] for r in resultados]


def test_override_post_equivale_a_query(client):
    partido = _crear_partido(client)
    client.post(
        f"/partidos/{partido['id']}/finalizar",
        json={"resultado_local": 1, "resultado_visitante": 0},
    )

    respuesta = client.post(
        "/query/partidos/finalizados",
        headers={"X-HTTP-Method-Override": "QUERY"},
    )
    assert respuesta.status_code == 200
    ids = [p["id"] for p in respuesta.json()]
    assert partido["id"] in ids


def test_post_sin_override_no_es_valido(client):
    respuesta = client.post("/query/partidos/finalizados")
    assert respuesta.status_code == 405
