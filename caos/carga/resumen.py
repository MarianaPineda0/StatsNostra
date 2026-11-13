"""Resume las corridas del perfil de k6 y declara el estado estable.

Lee CARPETA/corrida-N.json (el resumen que deja caos/carga/correr.sh), toma la
mediana de cada métrica entre corridas y declara el estado estable como
«éxito >= 99 % y p95 <= X ms», con X igual al p95 mediano más un margen (25 % por
defecto). La mediana, y no el promedio, evita que una corrida rara (un arranque en
frío, un vecino ruidoso) mueva el umbral.

Uso:
    python caos/carga/resumen.py CARPETA [--margen 0.25]
Escribe CARPETA/estado-estable.json y muestra la tabla por pantalla.
"""

import argparse
import json
import statistics
from pathlib import Path

CORRIDAS_MINIMAS = 3


def leer_corrida(ruta: Path) -> dict:
    metricas = json.loads(ruta.read_text(encoding="utf-8"))["metrics"]
    duracion = metricas["http_req_duration"]
    return {
        "corrida": ruta.stem.removeprefix("corrida-"),
        "peticiones": metricas["http_reqs"]["count"],
        "throughput_rps": round(metricas["http_reqs"]["rate"], 2),
        # http_req_failed es la tasa de fallos: el éxito es lo que queda
        "exito": round(1 - metricas["http_req_failed"]["value"], 4),
        "p50_ms": round(duracion["med"], 1),
        "p95_ms": round(duracion["p(95)"], 1),
        "p99_ms": round(duracion["p(99)"], 1),
    }


def declarar(corridas: list[dict], margen: float = 0.25) -> dict:
    """Mediana de cada métrica y umbral X = p95 mediano más el margen."""
    medianas = {
        campo: round(
            statistics.median(c[campo] for c in corridas), 4 if campo == "exito" else 1
        )
        for campo in ("exito", "p50_ms", "p95_ms", "p99_ms", "throughput_rps")
    }
    return {
        "corridas": len(corridas),
        "mediana": medianas,
        "margen": margen,
        "x_ms": round(medianas["p95_ms"] * (1 + margen)),
        "declaracion": (
            f"éxito >= 99 % y p95 <= {round(medianas['p95_ms'] * (1 + margen))} ms "
            f"(mediana de {len(corridas)} corridas: éxito {medianas['exito']:.2%}, "
            f"p95 {medianas['p95_ms']:.0f} ms, más un {margen:.0%} de margen)"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("carpeta", type=Path)
    parser.add_argument("--margen", type=float, default=0.25)
    args = parser.parse_args()

    rutas = sorted(args.carpeta.glob("corrida-*.json"))
    rutas = [r for r in rutas if not r.name.endswith(".meta.json")]
    if not rutas:
        raise SystemExit(f"No hay corridas en {args.carpeta}")
    corridas = [leer_corrida(r) for r in rutas]

    columnas = ("corrida", "peticiones", "éxito", "p50 ms", "p95 ms", "p99 ms", "rps")
    print(" ".join(f"{columna:>10}" for columna in columnas))
    for c in corridas:
        print(
            f"{c['corrida']:>10} {c['peticiones']:>10} {c['exito']:>10.2%} "
            f"{c['p50_ms']:>10.0f} {c['p95_ms']:>10.0f} {c['p99_ms']:>10.0f} "
            f"{c['throughput_rps']:>10.1f}"
        )

    resultado = declarar(corridas, args.margen)
    resultado["detalle"] = corridas
    print("\nEstado estable:", resultado["declaracion"])
    if len(corridas) < CORRIDAS_MINIMAS:
        print(f"Aviso: hay {len(corridas)} corridas y se piden {CORRIDAS_MINIMAS}.")
    (args.carpeta / "estado-estable.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
