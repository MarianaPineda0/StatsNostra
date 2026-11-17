"""Generador de carga concurrente para comparar stable y canary.

Manda peticiones en paralelo a la URL del servicio y agrupa lo que ve por el
track que respondio (cabecera X-Track). Sirve para tres cosas: comprobar el
reparto real de trafico entre revisiones, comparar latencias de las dos bajo
la misma carga y juntar suficientes peticiones para que la puerta de calidad
decida con datos.

Uso:
    python canary/carga.py --url https://... --duracion 120 --hilos 10
    python canary/carga.py --url https://... --fault "error=0.5"   # regresion simulada
"""

import argparse
import json
import math
import random
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

# Rutas de lectura comunes a las dos versiones: asi el reparto del trafico no
# depende de que una de las dos tenga rutas que la otra no conoce
RUTAS = [
    "/api/v1/apostadores",
    "/api/v1/partidos",
    "/api/v1/predicciones",
    "/api/v2/apostadores",
]


def _percentil(valores: list[float], q: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, math.ceil(q * len(ordenados)) - 1)]


def _cota_superior(errores: int, total: int) -> float:
    """Limite superior del 95 % (Wilson) de la tasa de error real.

    Con pocas peticiones la cota es amplia: 0 errores en 20 peticiones no
    prueba que el canary este sano, solo que el error real no pasa del 16 %.
    """
    if total == 0:
        return 1.0
    z, p = 1.96, errores / total
    centro = p + z * z / (2 * total)
    margen = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return (centro + margen) / (1 + z * z / total)


def _pedir(
    url: str, cabeceras: dict, metodo: str = "GET", cuerpo: dict | None = None
) -> tuple[str, str, int, float, dict]:
    inicio = time.perf_counter()
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    cabeceras = {**cabeceras, "Content-Type": "application/json"} if datos else cabeceras
    peticion = urllib.request.Request(url, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            codigo, headers, contenido = respuesta.status, respuesta.headers, respuesta.read()
    except urllib.error.HTTPError as error:
        codigo, headers, contenido = error.code, error.headers, b""
    except (urllib.error.URLError, TimeoutError):
        return "sin-respuesta", "-", 0, (time.perf_counter() - inicio) * 1000, {}
    try:
        respuesta_json = json.loads(contenido) if contenido else {}
    except ValueError:
        respuesta_json = {}
    return (
        headers.get("X-Track", "sin-track"),
        headers.get("X-App-Version", "-"),
        codigo,
        (time.perf_counter() - inicio) * 1000,
        respuesta_json,
    )


def _una_peticion(url: str, cabeceras: dict) -> tuple[str, str, int, float]:
    return _pedir(url, cabeceras)[:4]


def _ciclo_negocio(base: str, cabeceras: dict, registrar) -> None:
    """Crea un partido con dos predicciones, lo finaliza y borra lo creado.

    Una prediccion acierta el marcador y la otra no, y las dos se evaluan en la
    misma peticion de finalizar: la revision que la atiende siempre registra
    50 % de aciertos. Asi la metrica de negocio no depende del azar y una
    regresion en el calculo de puntos del canary si se nota.

    Al final se borra todo: las listas del API devuelven todas las filas, y si
    la carga las dejara crecer la latencia de cada corrida seria peor que la de
    la anterior y la comparacion entre revisiones dejaria de ser justa.
    """
    sufijo = uuid.uuid4().hex[:12]
    creados: list[str] = []  # rutas de lo creado, en orden de creacion

    def llamar(ruta: str, cuerpo: dict | None = None, metodo: str = "POST") -> dict | None:
        track, version, codigo, ms, datos = _pedir(base + ruta, cabeceras, metodo, cuerpo)
        registrar(track, version, codigo, ms)
        return datos if codigo < 300 else None

    def crear(ruta: str, cuerpo: dict) -> dict | None:
        datos = llamar(ruta, cuerpo)
        if datos is not None:
            creados.append(f"{ruta}/{datos['id']}")
        return datos

    try:
        apostadores = [
            crear(
                "/api/v1/apostadores",
                {
                    "nombre": f"Carga {indice}",
                    "username": f"carga_{sufijo}_{indice}",
                    "email": f"carga.{sufijo}.{indice}@example.com",
                },
            )
            for indice in (1, 2)
        ]
        partido = crear(
            "/api/v1/partidos",
            {
                "deporte": "Futbol",
                "liga": "Liga BetPlay",
                "equipo_local": f"Local {sufijo}",
                "equipo_visitante": f"Visitante {sufijo}",
                "fecha_hora": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            },
        )
        if partido is None or not all(apostadores):
            return
        # El resultado sera 2-1: el primer apostador acierta y el segundo no
        for apostador, (local, visitante) in zip(apostadores, [(2, 1), (0, 3)], strict=True):
            crear(
                "/api/v1/predicciones",
                {
                    "apostador_id": apostador["id"],
                    "partido_id": partido["id"],
                    "goles_local_pred": local,
                    "goles_visitante_pred": visitante,
                },
            )
        llamar(
            f"/api/v1/partidos/{partido['id']}/finalizar",
            {"resultado_local": 2, "resultado_visitante": 1},
        )
    finally:
        # Primero las predicciones, que dependen del partido y de los apostadores
        for ruta in sorted(creados, key=lambda r: "/predicciones/" not in r):
            llamar(ruta, metodo="DELETE")


def cabeceras_de(fault: str = "", extra: list[str] | None = None) -> dict:
    cabeceras = {"Accept": "application/json"}
    if fault:
        cabeceras["X-Fault"] = fault
    for texto in extra or []:
        nombre, _, valor = texto.partition(":")
        cabeceras[nombre.strip()] = valor.strip()
    return cabeceras


def generar(
    url: str,
    duracion: int,
    hilos: int,
    cabeceras: dict,
    hilos_negocio: int = 0,
    tasa: float = 0,
    ciclo_cada: float = 0,
) -> dict[str, list]:
    """Manda carga durante `duracion` segundos. Devuelve, por cada track que
    respondio, la lista de (codigo, milisegundos).

    Con `tasa` (peticiones por segundo, en total) la carga es de ritmo fijo: no
    depende de lo rapido que responda el servicio. Sin ella cada hilo manda lo
    mas rapido que puede y, si el servicio tarda, satura la linea base y falsea
    la comparacion. Los `hilos_negocio` finalizan partidos con predicciones
    (un ciclo cada `ciclo_cada` segundos) para que la metrica de negocio tenga
    datos en las dos revisiones.
    """
    resultados: dict[str, list] = defaultdict(list)
    cerrojo = threading.Lock()
    fin = time.monotonic() + duracion
    base = url.rstrip("/")
    intervalo = hilos / tasa if tasa else 0

    def registrar(track: str, version: str, codigo: int, ms: float) -> None:
        with cerrojo:
            resultados[f"{track} {version}"].append((codigo, ms))

    def esperar(inicio: float, cada: float) -> None:
        resto = cada - (time.monotonic() - inicio)
        if resto > 0:
            time.sleep(resto)

    def trabajar() -> None:
        while time.monotonic() < fin:
            inicio = time.monotonic()
            registrar(*_una_peticion(base + random.choice(RUTAS), cabeceras))
            esperar(inicio, intervalo)

    def trabajar_negocio() -> None:
        while time.monotonic() < fin:
            inicio = time.monotonic()
            _ciclo_negocio(base, cabeceras, registrar)
            esperar(inicio, ciclo_cada)

    ejecutores = [threading.Thread(target=trabajar) for _ in range(hilos)]
    ejecutores += [threading.Thread(target=trabajar_negocio) for _ in range(hilos_negocio)]
    for ejecutor in ejecutores:
        ejecutor.start()
    for ejecutor in ejecutores:
        ejecutor.join()
    return resultados


def imprimir(resultados: dict[str, list], duracion: int, hilos: int) -> None:
    total = sum(len(v) for v in resultados.values())
    print(f"\n{total} peticiones en {duracion} s con {hilos} hilos\n")
    print(
        f"{'respondio':<18} {'peticiones':>10} {'reparto':>8} {'5xx':>5} {'err cota95':>10} "
        f"{'p50ms':>7} {'p95ms':>7} {'p99ms':>7}"
    )
    for clave, filas in sorted(resultados.items()):
        errores = sum(1 for codigo, _ in filas if codigo >= 500 or codigo == 0)
        tiempos = [ms for _, ms in filas]
        print(
            f"{clave:<18} {len(filas):>10} {len(filas) / total:>8.1%} {errores:>5} "
            f"{_cota_superior(errores, len(filas)):>10.1%} {_percentil(tiempos, 0.50):>7.0f} "
            f"{_percentil(tiempos, 0.95):>7.0f} {_percentil(tiempos, 0.99):>7.0f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", required=True, help="URL base del servicio")
    parser.add_argument("--duracion", type=int, default=60, help="segundos de carga")
    parser.add_argument("--hilos", type=int, default=10, help="peticiones en paralelo")
    parser.add_argument("--fault", default="", help='valor de X-Fault, ej. "error=0.5"')
    parser.add_argument("--cabecera", action="append", default=[], help='ej. "x-canary: true"')
    parser.add_argument(
        "--tasa", type=float, default=0, help="peticiones por segundo en total"
    )
    parser.add_argument(
        "--hilos-negocio",
        type=int,
        default=0,
        help="hilos que finalizan partidos con predicciones",
    )
    args = parser.parse_args()

    resultados = generar(
        args.url, args.duracion, args.hilos, cabeceras_de(args.fault, args.cabecera),
        args.hilos_negocio, args.tasa,
    )  # fmt: skip
    imprimir(resultados, args.duracion, args.hilos)


if __name__ == "__main__":
    main()
