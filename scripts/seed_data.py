"""Inserta datos de ejemplo en un ambiente de StatsNostra via su API real.

Uso:
    python scripts/seed_data.py http://localhost:8000
    python scripts/seed_data.py https://statsnostra-pruebas.onrender.com
"""

import sys

import httpx

APOSTADORES = [
    {"nombre": "Juan Perez", "username": "juanp", "email": "juan@example.com"},
    {"nombre": "Maria Gomez", "username": "mariag", "email": "maria@example.com"},
    {"nombre": "Carlos Ruiz", "username": "carlosr", "email": "carlos@example.com"},
    {"nombre": "Ana Silva", "username": "anas", "email": "ana@example.com"},
    {"nombre": "Luis Martinez", "username": "luism", "email": "luis@example.com"},
    {"nombre": "Pedro Torres", "username": "pedrot", "email": "pedro@example.com"},
]
INACTIVOS = {"pedrot"}

PARTIDOS = [
    {
        "deporte": "Futbol",
        "liga": "Liga BetPlay",
        "equipo_local": "Millonarios",
        "equipo_visitante": "Nacional",
        "fecha_hora": "2026-07-01T20:00:00Z",
        "finalizar": (2, 1),
    },
    {
        "deporte": "Futbol",
        "liga": "Liga BetPlay",
        "equipo_local": "America",
        "equipo_visitante": "Junior",
        "fecha_hora": "2026-07-05T20:00:00Z",
        "finalizar": (1, 1),
    },
    {
        "deporte": "Futbol",
        "liga": "Premier League",
        "equipo_local": "Arsenal",
        "equipo_visitante": "Chelsea",
        "fecha_hora": "2026-07-10T18:00:00Z",
        "finalizar": (3, 0),
    },
    {
        "deporte": "Baloncesto",
        "liga": "NBA",
        "equipo_local": "Lakers",
        "equipo_visitante": "Celtics",
        "fecha_hora": "2026-09-01T02:00:00Z",
        "finalizar": None,
    },
    {
        "deporte": "Futbol",
        "liga": "Liga BetPlay",
        "equipo_local": "Santa Fe",
        "equipo_visitante": "Once Caldas",
        "fecha_hora": "2026-09-05T20:00:00Z",
        "finalizar": None,
    },
    {
        "deporte": "Futbol",
        "liga": "Champions League",
        "equipo_local": "Real Madrid",
        "equipo_visitante": "Bayern",
        "fecha_hora": "2026-09-15T19:00:00Z",
        "finalizar": None,
    },
]

# (indice_partido, username, goles_local_pred, goles_visitante_pred)
PREDICCIONES = [
    (0, "juanp", 2, 1),
    (0, "mariag", 1, 0),
    (0, "carlosr", 0, 1),
    (1, "juanp", 1, 1),
    (1, "anas", 2, 2),
    (1, "luism", 2, 0),
    (2, "mariag", 3, 0),
    (2, "carlosr", 2, 0),
    (2, "anas", 0, 1),
    (4, "luism", 1, 0),
    (5, "anas", 2, 2),
]


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    client = httpx.Client(base_url=base_url, timeout=60)

    apostador_ids: dict[str, int] = {}
    for datos in APOSTADORES:
        respuesta = client.post("/apostadores", json=datos)
        if respuesta.status_code == 201:
            cuerpo = respuesta.json()
        elif respuesta.status_code == 409:
            cuerpo = next(
                a
                for a in client.get("/apostadores").json()
                if a["username"] == datos["username"]
            )
        else:
            respuesta.raise_for_status()
            continue
        apostador_ids[datos["username"]] = cuerpo["id"]
        if datos["username"] in INACTIVOS:
            client.put(f"/apostadores/{cuerpo['id']}", json={"activo": False})
    print(f"Apostadores listos: {len(apostador_ids)}")

    partido_ids: list[int] = []
    for datos in PARTIDOS:
        payload = {k: v for k, v in datos.items() if k != "finalizar"}
        respuesta = client.post("/partidos", json=payload)
        if respuesta.status_code == 201:
            partido_id = respuesta.json()["id"]
        else:
            partidos_existentes = client.get("/partidos").json()
            partido_id = next(
                p["id"]
                for p in partidos_existentes
                if p["equipo_local"] == datos["equipo_local"]
                and p["equipo_visitante"] == datos["equipo_visitante"]
            )
        partido_ids.append(partido_id)
    print(f"Partidos listos: {len(partido_ids)}")

    creadas = 0
    for indice, username, gl, gv in PREDICCIONES:
        partido_id = partido_ids[indice]
        apostador_id = apostador_ids[username]
        respuesta = client.post(
            "/predicciones",
            json={
                "apostador_id": apostador_id,
                "partido_id": partido_id,
                "goles_local_pred": gl,
                "goles_visitante_pred": gv,
            },
        )
        if respuesta.status_code == 201:
            creadas += 1
    print(f"Predicciones creadas: {creadas}")

    finalizados = 0
    for indice, datos in enumerate(PARTIDOS):
        if datos["finalizar"] is None:
            continue
        resultado_local, resultado_visitante = datos["finalizar"]
        respuesta = client.post(
            f"/partidos/{partido_ids[indice]}/finalizar",
            json={
                "resultado_local": resultado_local,
                "resultado_visitante": resultado_visitante,
            },
        )
        if respuesta.status_code == 200:
            finalizados += 1
    print(f"Partidos finalizados: {finalizados}")


if __name__ == "__main__":
    main()
