"""Veredicto de una ronda: compara el resumen de k6 con el estado estable declarado.

La hipótesis dice «éxito >= 99 % y p95 <= X ms». Que una ronda la refute no es un
error del experimento sino su resultado, así que este script siempre termina bien
y deja el veredicto en una línea JSON que el experimento guarda en su diario.

Uso:
    python caos/carga/veredicto.py RESUMEN.json [--x-ms 1511] [--esperar 90]
Sin --x-ms toma X de caos/evidencia/estado-estable/estado-estable.json.
--esperar espera hasta N segundos a que k6 termine (que exista su .meta.json).
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from resumen import leer_corrida  # noqa: E402

RAIZ = Path(__file__).parent.parent.parent
ESTADO_ESTABLE = RAIZ / "caos" / "evidencia" / "estado-estable" / "estado-estable.json"
EXITO_MINIMO = 0.99


def evaluar(corrida: dict, x_ms: float, base_p95_ms: float | None = None) -> dict:
    motivos = []
    if corrida["exito"] < EXITO_MINIMO:
        motivos.append(f"éxito {corrida['exito']:.2%} < {EXITO_MINIMO:.0%}")
    if corrida["p95_ms"] > x_ms:
        motivos.append(f"p95 {corrida['p95_ms']:.0f} ms > X {x_ms:.0f} ms")
    veredicto = {
        "cumple": not motivos,
        "motivos": motivos,
        "exito": corrida["exito"],
        "exito_minimo": EXITO_MINIMO,
        "p95_ms": corrida["p95_ms"],
        "x_ms": x_ms,
        "sobre_x_pct": round((corrida["p95_ms"] / x_ms - 1) * 100, 1),
        "peticiones": corrida["peticiones"],
    }
    if base_p95_ms:
        veredicto["p95_estado_estable_ms"] = base_p95_ms
        veredicto["variacion_p95_pct"] = round((corrida["p95_ms"] / base_p95_ms - 1) * 100, 1)
    return veredicto


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("resumen", type=Path)
    parser.add_argument("--x-ms", type=float)
    parser.add_argument("--esperar", type=int, default=0)
    args = parser.parse_args()

    meta = args.resumen.with_name(args.resumen.stem + ".meta.json")
    limite = time.monotonic() + args.esperar
    while not meta.exists() and time.monotonic() < limite:
        time.sleep(2)
    if not args.resumen.exists():
        raise SystemExit(f"No hay resumen de k6 en {args.resumen}")

    base = None
    x_ms = args.x_ms
    if ESTADO_ESTABLE.exists():
        estado = json.loads(ESTADO_ESTABLE.read_text(encoding="utf-8"))
        base = estado["mediana"]["p95_ms"]
        x_ms = x_ms or estado["x_ms"]
    if x_ms is None:
        raise SystemExit("Falta X: pasa --x-ms o mide primero el estado estable")

    print(json.dumps(evaluar(leer_corrida(args.resumen), x_ms, base), ensure_ascii=False))


if __name__ == "__main__":
    main()
