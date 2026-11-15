"""Resume por pod lo que atendió el API en cada ronda y arma la comparación de una traza.

Entrada: los CSV de exportar_logs.sh de la ronda 0 y de la ronda 1, y la carpeta de datos
con inyeccion-rondaN.json (que dice cuándo arrancó el fallo y qué pod se saturó).
Salida: datos/resumen-pods.json con, por ronda, las llamadas, el p50, el p95 y el p99 de
cada pod, la parte del tráfico que atendió el pod saturado minuto a minuto, y la misma
traza (el trace id de la llamada más lenta de la ronda 0) vista en las dos rondas.
Solo cuenta /api/: no las sondas ni las rutas de control del experimento.

Uso: python caos/tablero/resumen_pods.py ronda0.csv ronda1.csv caos/tablero/datos
"""

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def percentil(valores, p):
    ordenados = sorted(valores)
    return ordenados[min(int(p * len(ordenados)), len(ordenados) - 1)]


def leer(ruta_csv: str, inicio: datetime):
    llamadas = []
    for hora, pod, ruta, status, ms, traza in csv.reader(open(ruta_csv, encoding="utf-8")):
        if not ruta.startswith("/api/"):
            continue
        segundos = (datetime.fromisoformat(hora) - inicio).total_seconds()
        llamadas.append(
            {
                "s": segundos,
                "pod": pod,
                "ruta": ruta,
                "status": int(status),
                "ms": float(ms),
                "traza": traza,
            }
        )
    return llamadas


def resumir(llamadas, saturado: str) -> dict:
    por_pod = defaultdict(list)
    for c in llamadas:
        por_pod[c["pod"]].append(c["ms"])
    total = len(llamadas)
    pods = []
    for pod, v in sorted(por_pod.items(), key=lambda kv: (kv[0] != saturado, kv[0])):
        pods.append(
            {
                "pod": pod,
                "rol": "saturado" if pod == saturado else "sano",
                "llamadas": len(v),
                "parte": len(v) / total,
                "p50_ms": percentil(v, 0.5),
                "p95_ms": percentil(v, 0.95),
                "p99_ms": percentil(v, 0.99),
            }
        )
    por_minuto = defaultdict(lambda: [0, 0])
    for c in llamadas:
        m = int(c["s"] // 60)
        if 0 <= m <= 3:
            por_minuto[m][0] += 1
            por_minuto[m][1] += c["pod"] == saturado
    reparto = [
        {"minuto": m, "llamadas": t, "parte_saturado": s / t if t else 0.0}
        for m, (t, s) in sorted(por_minuto.items())
    ]
    errores = sum(c["status"] >= 500 for c in llamadas)
    return {
        "pod_saturado": saturado,
        "llamadas": total,
        "errores_5xx": errores,
        "pods": pods,
        "reparto_por_minuto": reparto,
    }


def main(csv0: str, csv1: str, datos: str) -> None:
    datos_dir = Path(datos)
    iny = {
        r: json.loads((datos_dir / f"inyeccion-ronda{r}.json").read_text(encoding="utf-8"))
        for r in "01"
    }
    inicio = {
        r: datetime.fromisoformat(iny[r]["inicio_utc"].replace("Z", "+00:00")) for r in "01"
    }
    llamadas = {"0": leer(csv0, inicio["0"]), "1": leer(csv1, inicio["1"])}
    resumen = {f"ronda{r}": resumir(llamadas[r], iny[r]["pod_saturado"]) for r in "01"}

    # La traza más lenta de la ronda 0 en el pod saturado, y esa misma traza en la ronda 1.
    # El perfil de k6 es determinista (usuario e iteración forman el trace id), así que el
    # mismo trace id es la misma petición lógica en las dos rondas.
    lenta = max(
        (c for c in llamadas["0"] if c["pod"] == iny["0"]["pod_saturado"]),
        key=lambda c: c["ms"],
    )

    def de_traza(r):
        return [
            {
                "ruta": c["ruta"],
                "rol": "saturado" if c["pod"] == iny[r]["pod_saturado"] else "sano",
                "ms": c["ms"],
            }
            for c in sorted(llamadas[r], key=lambda c: c["s"])
            if c["traza"] == lenta["traza"]
        ]

    resumen["traza"] = {"id": lenta["traza"], "ronda0": de_traza("0"), "ronda1": de_traza("1")}

    (datos_dir / "resumen-pods.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("escrito", datos_dir / "resumen-pods.json")


if __name__ == "__main__":
    main(*sys.argv[1:4])
