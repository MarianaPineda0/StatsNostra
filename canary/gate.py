"""Puerta de calidad del canary: compara la revision canary con la estable y
decide si se promueve, se pausa o se aborta, segun canary/slo.yaml.

Uso:
    python canary/gate.py --canary REVISION --estable REVISION [--ventana 5]

Codigo de salida: 0 promover, 10 pausar, 20 abortar. Lo lee el workflow para
seguir a la etapa siguiente o dejar el trafico en 0 % canary / 100 % estable.
"""

import argparse
import json
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml

PROMOVER, PAUSAR, ABORTAR = "PROMOVER", "PAUSAR", "ABORTAR"
CODIGOS_SALIDA = {PROMOVER: 0, PAUSAR: 10, ABORTAR: 20}
SLO_POR_DEFECTO = Path(__file__).with_name("slo.yaml")


@dataclass
class Medicion:
    """Senales de una revision en la ventana evaluada."""

    peticiones: float = 0.0
    errores_5xx: float = 0.0
    p50_ms: float | None = None
    p95_ms: float | None = None
    p99_ms: float | None = None
    cpu: float | None = None
    memoria: float | None = None

    @property
    def tasa_error(self) -> float:
        return self.errores_5xx / self.peticiones if self.peticiones else 0.0


def decidir(slo: dict, canary: Medicion, estable: Medicion) -> tuple[str, list[str]]:
    """Aplica los umbrales de slo.yaml. Devuelve la decision y sus razones."""
    if canary.peticiones < slo["muestra_minima"]["peticiones_canary"]:
        return PAUSAR, [
            f"muestra insuficiente: {canary.peticiones:.0f} peticiones en el canary, "
            f"minimo {slo['muestra_minima']['peticiones_canary']}"
        ]

    ab, pr, sat = slo["abortar"], slo["promover"], slo["saturacion"]
    razones_abortar = []
    if canary.tasa_error > ab["tasa_error_5xx_max"]:
        razones_abortar.append(
            f"errores 5xx {canary.tasa_error:.1%} > {ab['tasa_error_5xx_max']:.1%}"
        )
    if canary.p95_ms is not None and canary.p95_ms > ab["latencia_p95_ms_max"]:
        razones_abortar.append(f"p95 {canary.p95_ms:.0f} ms > {ab['latencia_p95_ms_max']} ms")
    if _veces(canary.p95_ms, estable.p95_ms) > ab["p95_vs_estable_max"]:
        razones_abortar.append(
            f"p95 {_veces(canary.p95_ms, estable.p95_ms):.1f} veces la de la estable "
            f"(limite {ab['p95_vs_estable_max']})"
        )
    if razones_abortar:
        return ABORTAR, razones_abortar

    incumplidas = []
    if canary.tasa_error > pr["tasa_error_5xx_max"]:
        incumplidas.append(
            f"errores 5xx {canary.tasa_error:.1%} > {pr['tasa_error_5xx_max']:.1%}"
        )
    if canary.tasa_error - estable.tasa_error > pr["error_extra_max"]:
        incumplidas.append("mas errores que la estable en la misma ventana")
    if canary.p95_ms is not None and canary.p95_ms > pr["latencia_p95_ms_max"]:
        incumplidas.append(f"p95 {canary.p95_ms:.0f} ms > {pr['latencia_p95_ms_max']} ms")
    if canary.p99_ms is not None and canary.p99_ms > pr["latencia_p99_ms_max"]:
        incumplidas.append(f"p99 {canary.p99_ms:.0f} ms > {pr['latencia_p99_ms_max']} ms")
    if _veces(canary.p95_ms, estable.p95_ms) > pr["p95_vs_estable_max"]:
        incumplidas.append("p95 por encima del limite relativo a la estable")
    if canary.cpu is not None and canary.cpu > sat["cpu_max"]:
        incumplidas.append(f"CPU {canary.cpu:.0%} > {sat['cpu_max']:.0%}")
    if canary.memoria is not None and canary.memoria > sat["memoria_max"]:
        incumplidas.append(f"memoria {canary.memoria:.0%} > {sat['memoria_max']:.0%}")

    if incumplidas:
        return PAUSAR, incumplidas
    return PROMOVER, ["todos los umbrales de promocion se cumplen"]


def _veces(canary: float | None, estable: float | None) -> float:
    # Sin datos de la estable no hay con que comparar: no cuenta como violacion
    if canary is None or not estable:
        return 0.0
    return canary / estable


# --- Lectura de metricas (Cloud Monitoring, API compatible con PromQL) ---


def _token() -> str:
    # which resuelve gcloud.cmd en Windows, donde subprocess no lo encuentra solo
    gcloud = shutil.which("gcloud") or "gcloud"
    salida = subprocess.run(
        [gcloud, "auth", "print-access-token"], capture_output=True, text=True, check=True
    )
    return salida.stdout.strip()


def _consultar(proyecto: str, promql: str, token: str) -> float | None:
    url = (
        f"https://monitoring.googleapis.com/v1/projects/{proyecto}/location/global/"
        f"prometheus/api/v1/query?" + urllib.parse.urlencode({"query": promql})
    )
    peticion = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(peticion, timeout=30) as respuesta:
        resultado = json.load(respuesta)["data"]["result"]
    if not resultado:
        return None
    valor = float(resultado[0]["value"][1])
    return None if valor != valor else valor  # NaN: no hubo datos en la ventana


def medir(
    proyecto: str, servicio: str, revision: str, ventana_min: int, token: str
) -> Medicion:
    filtro = (
        'monitored_resource="cloud_run_revision",'
        f'service_name="{servicio}",revision_name="{revision}"'
    )
    ventana = f"{ventana_min}m"

    def percentil(metrica: str, q: float) -> float | None:
        return _consultar(
            proyecto,
            f"histogram_quantile({q}, sum by (le) "
            f"(increase(run_googleapis_com:{metrica}_bucket{{{filtro}}}[{ventana}])))",
            token,
        )

    def contar(extra: str = "") -> float:
        consulta = (
            f"sum(increase(run_googleapis_com:request_count{{{filtro}{extra}}}[{ventana}]))"
        )
        return _consultar(proyecto, consulta, token) or 0.0

    return Medicion(
        peticiones=contar(),
        errores_5xx=contar(',response_code_class="5xx"'),
        p50_ms=percentil("request_latencies", 0.50),
        p95_ms=percentil("request_latencies", 0.95),
        p99_ms=percentil("request_latencies", 0.99),
        cpu=percentil("container_cpu_utilizations", 0.95),
        memoria=percentil("container_memory_utilizations", 0.95),
    )


def _fila(nombre: str, m: Medicion) -> str:
    def f(valor, formato):
        return "-" if valor is None else format(valor, formato)

    return (
        f"{nombre:<8} {m.peticiones:>8.0f} {m.tasa_error:>7.2%} {f(m.p50_ms, '.0f'):>7} "
        f"{f(m.p95_ms, '.0f'):>7} {f(m.p99_ms, '.0f'):>7} "
        f"{f(m.cpu, '.0%'):>6} {f(m.memoria, '.0%'):>6}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--proyecto", default="project-3f57bb8c-371e-4b9c-949")
    parser.add_argument("--servicio", default="statsnostra-api")
    parser.add_argument("--canary", required=True, help="nombre de la revision canary")
    parser.add_argument("--estable", required=True, help="nombre de la revision estable")
    parser.add_argument("--ventana", type=int, default=5, help="minutos a evaluar")
    parser.add_argument("--slo", type=Path, default=SLO_POR_DEFECTO)
    args = parser.parse_args()

    slo = yaml.safe_load(args.slo.read_text(encoding="utf-8"))
    token = _token()
    canary = medir(args.proyecto, args.servicio, args.canary, args.ventana, token)
    estable = medir(args.proyecto, args.servicio, args.estable, args.ventana, token)

    decision, razones = decidir(slo, canary, estable)
    print(
        f"{'':<8} {'peticion':>8} {'err5xx':>7} {'p50ms':>7} {'p95ms':>7} {'p99ms':>7} "
        f"{'cpu':>6} {'mem':>6}"
    )
    print(_fila("estable", estable))
    print(_fila("canary", canary))
    print(f"\nDECISION: {decision}")
    for razon in razones:
        print(f"  - {razon}")
    return CODIGOS_SALIDA[decision]


if __name__ == "__main__":
    sys.exit(main())
