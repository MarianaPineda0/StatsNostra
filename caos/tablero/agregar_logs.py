"""Resume las peticiones de una ronda en una serie por ventanas de 10 s y por pod.

Entrada: el CSV de exportar_logs.sh (hora, pod, ruta, status, ms, traceId).
Salida: datos/servidor-rondaN.csv con peticiones, p50 y p95 del API de negocio por
ventana y pod, más datos/inyeccion-rondaN.json con la hora en que arrancó el fallo.
Solo cuenta /api/ (no las sondas ni las rutas de control del experimento).
"""

import csv
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime

VENTANA_S = 10


def percentil(valores, p):
    ordenados = sorted(valores)
    return ordenados[min(int(p * len(ordenados)), len(ordenados) - 1)]


def main(entrada: str, ronda: str, carpeta_salida: str) -> None:
    filas = list(csv.reader(open(entrada, encoding="utf-8")))
    por_ventana = defaultdict(list)
    inicio_fallo = None
    for hora, pod, ruta, _status, ms, _trace in filas:
        instante = datetime.fromisoformat(hora)
        if ruta == "/fault/cpu":
            if inicio_fallo is None or instante < inicio_fallo[0]:
                inicio_fallo = (instante, pod)
            continue
        if not ruta.startswith("/api/"):
            continue
        ventana = int(instante.timestamp()) // VENTANA_S * VENTANA_S
        por_ventana[(ventana, pod)].append(float(ms))

    with open(
        f"{carpeta_salida}/servidor-ronda{ronda}.csv", "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f)
        w.writerow(["ventana_utc", "pod", "peticiones", "p50_ms", "p95_ms"])
        for (ventana, pod), v in sorted(por_ventana.items()):
            hora = datetime.fromtimestamp(ventana, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            w.writerow(
                [hora, pod, len(v), round(percentil(v, 0.5), 1), round(percentil(v, 0.95), 1)]
            )

    instante, pod = inicio_fallo
    json.dump(
        {
            "inicio_utc": instante.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pod_saturado": pod,
            "duracion_s": 180,
        },
        open(f"{carpeta_salida}/inyeccion-ronda{ronda}.json", "w", encoding="utf-8"),
        indent=2,
    )


if __name__ == "__main__":
    main(*sys.argv[1:4])
