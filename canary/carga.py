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
import math
import random
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict

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


def _una_peticion(url: str, cabeceras: dict) -> tuple[str, str, int, float]:
    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=cabeceras), timeout=30
        ) as respuesta:
            codigo, headers = respuesta.status, respuesta.headers
    except urllib.error.HTTPError as error:
        codigo, headers = error.code, error.headers
    except (urllib.error.URLError, TimeoutError):
        return "sin-respuesta", "-", 0, (time.perf_counter() - inicio) * 1000
    return (
        headers.get("X-Track", "sin-track"),
        headers.get("X-App-Version", "-"),
        codigo,
        (time.perf_counter() - inicio) * 1000,
    )


def cabeceras_de(fault: str = "", extra: list[str] | None = None) -> dict:
    cabeceras = {"Accept": "application/json"}
    if fault:
        cabeceras["X-Fault"] = fault
    for texto in extra or []:
        nombre, _, valor = texto.partition(":")
        cabeceras[nombre.strip()] = valor.strip()
    return cabeceras


def generar(url: str, duracion: int, hilos: int, cabeceras: dict) -> dict[str, list]:
    """Manda carga durante `duracion` segundos. Devuelve, por cada track que
    respondio, la lista de (codigo, milisegundos)."""
    resultados: dict[str, list] = defaultdict(list)
    cerrojo = threading.Lock()
    fin = time.monotonic() + duracion

    def trabajar() -> None:
        while time.monotonic() < fin:
            track, version, codigo, ms = _una_peticion(
                url.rstrip("/") + random.choice(RUTAS), cabeceras
            )
            with cerrojo:
                resultados[f"{track} {version}"].append((codigo, ms))

    ejecutores = [threading.Thread(target=trabajar) for _ in range(hilos)]
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
    args = parser.parse_args()

    resultados = generar(
        args.url, args.duracion, args.hilos, cabeceras_de(args.fault, args.cabecera)
    )
    imprimir(resultados, args.duracion, args.hilos)


if __name__ == "__main__":
    main()
