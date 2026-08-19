# Pruebas del CRUD de Apostador: creacion, lectura, actualizacion,
# eliminacion, y los dos casos de conflicto (username/email duplicado).


def _crear_apostador(client, username="ana01", email="ana01@example.com"):
    return client.post(
        "/apostadores",
        json={"nombre": "Ana Gomez", "username": username, "email": email},
    )


def test_crear_apostador(client):
    respuesta = _crear_apostador(client)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["username"] == "ana01"
    assert cuerpo["activo"] is True


def test_listar_apostadores(client):
    creado = _crear_apostador(client).json()
    respuesta = client.get("/apostadores")
    assert respuesta.status_code == 200
    assert creado["id"] in [a["id"] for a in respuesta.json()]


def test_obtener_apostador(client):
    creado = _crear_apostador(client).json()
    respuesta = client.get(f"/apostadores/{creado['id']}")
    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == creado["id"]


def test_obtener_apostador_inexistente(client):
    respuesta = client.get("/apostadores/999")
    assert respuesta.status_code == 404


def test_actualizar_apostador(client):
    creado = _crear_apostador(client).json()
    respuesta = client.put(f"/apostadores/{creado['id']}", json={"nombre": "Ana Editada"})
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Ana Editada"


def test_eliminar_apostador(client):
    creado = _crear_apostador(client).json()
    respuesta = client.delete(f"/apostadores/{creado['id']}")
    assert respuesta.status_code == 204
    assert client.get(f"/apostadores/{creado['id']}").status_code == 404


def test_username_duplicado(client):
    _crear_apostador(client, username="dup", email="uno@example.com")
    respuesta = _crear_apostador(client, username="dup", email="dos@example.com")
    assert respuesta.status_code == 409


def test_email_duplicado(client):
    _crear_apostador(client, username="uno", email="dup@example.com")
    respuesta = _crear_apostador(client, username="dos", email="dup@example.com")
    assert respuesta.status_code == 409
