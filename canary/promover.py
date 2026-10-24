"""Promueve el canary por etapas y aborta solo si una etapa falla.

En cada etapa sube el porcentaje de trafico, deja correr carga durante el
tiempo de horneado (bake time), mide las dos revisiones y le pregunta a la
puerta de calidad (canary/gate.py, umbrales en canary/slo.yaml). Si una etapa
no pasa, deja 0 % canary / 100 % estable y termina con error para que el
workflow quede en rojo.

Uso, desde la raiz del repositorio:
    python -m canary.promover --url URL --canary REV --estable REV \\
        --etapas 10,50,100 --bake 3 [--fault "error=0.5"]
"""

import argparse
import math
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from canary import carga, gate

SALIDA_OK, SALIDA_ABORTADO = 0, 20


@dataclass
class Entorno:
    """Todo lo que toca el exterior. En las pruebas se reemplaza por falsos."""

    fijar_trafico: Callable[[dict[str, int]], None]
    generar_carga: Callable[[int], None]  # segundos de carga
    medir: Callable[[int], tuple[gate.Medicion, gate.Medicion]]  # (canary, estable)
    dormir: Callable[[float], None]


def promover(
    slo: dict,
    etapas: list[int],
    bake_min: int,
    espera_metricas_s: int,
    canary: str,
    estable: str,
    entorno: Entorno,
    log: Callable[[str], None] = print,
) -> int:
    pausa = slo["pausa"]
    for porcentaje in etapas:
        log(f"\n=== Etapa {porcentaje} % canary, {bake_min} min de horneado ===")
        entorno.fijar_trafico({estable: 100 - porcentaje, canary: porcentaje})
        entorno.generar_carga(bake_min * 60)
        # Cloud Monitoring tarda en publicar lo que acaba de pasar
        entorno.dormir(espera_metricas_s)

        # Ventana que cubre el horneado y la espera, con un minuto de margen
        ventana = bake_min + math.ceil(espera_metricas_s / 60) + 1
        for intento in range(pausa["reintentos_max"] + 1):
            medicion_canary, medicion_estable = entorno.medir(ventana)
            decision, razones = gate.decidir(slo, medicion_canary, medicion_estable)
            log(_resumen(medicion_canary, medicion_estable, decision, razones))
            if decision != gate.PAUSAR:
                break
            if intento == pausa["reintentos_max"]:
                decision = gate.ABORTAR
                razones = [f"sin evidencia suficiente tras {intento + 1} evaluaciones"]
                log(f"  -> {razones[0]}")
                break
            log(f"  -> PAUSA: se reevalua en {pausa['espera_segundos']} s con mas carga")
            entorno.generar_carga(pausa["espera_segundos"])
            entorno.dormir(espera_metricas_s)

        if decision == gate.ABORTAR:
            log("\nABORTADO: 0 % canary, 100 % estable")
            entorno.fijar_trafico({estable: 100, canary: 0})
            return SALIDA_ABORTADO
        log(f"Etapa {porcentaje} % superada")

    log(f"\nPROMOVIDO: el canary atiende el {etapas[-1]} % del trafico")
    return SALIDA_OK


def _resumen(canary: gate.Medicion, estable: gate.Medicion, decision: str, razones) -> str:
    lineas = [
        f"{'':<8} {'peticion':>8} {'err5xx':>7} {'p50ms':>7} {'p95ms':>7} {'p99ms':>7}",
        gate._fila("estable", estable),
        gate._fila("canary", canary),
        f"  -> {decision}: " + "; ".join(razones),
    ]
    return "\n".join(lineas)


# --- Entorno real (gcloud y Cloud Monitoring) ---


def _entorno_real(args) -> Entorno:
    gcloud = shutil.which("gcloud") or "gcloud"
    cabeceras = carga.cabeceras_de(args.fault)

    def fijar_trafico(reparto: dict[str, int]) -> None:
        asignacion = ",".join(
            f"{revision}={porcentaje}" for revision, porcentaje in reparto.items()
        )
        subprocess.run(
            [
                gcloud, "run", "services", "update-traffic", args.servicio,
                f"--project={args.proyecto}", f"--region={args.region}",
                f"--to-revisions={asignacion}",
            ],
            check=True,
        )  # fmt: skip

    def generar_carga(segundos: int) -> None:
        resultados = carga.generar(args.url, segundos, args.hilos, cabeceras)
        carga.imprimir(resultados, segundos, args.hilos)

    def medir(ventana: int):
        token = gate._token()
        return (
            gate.medir(args.proyecto, args.servicio, args.canary, ventana, token),
            gate.medir(args.proyecto, args.servicio, args.estable, ventana, token),
        )

    return Entorno(fijar_trafico, generar_carga, medir, time.sleep)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", required=True, help="URL publica del servicio")
    parser.add_argument("--canary", required=True, help="revision canary")
    parser.add_argument("--estable", required=True, help="revision estable (linea base)")
    parser.add_argument("--etapas", default="10,50,100", help="porcentajes separados por coma")
    parser.add_argument("--bake", type=int, default=3, help="minutos de horneado por etapa")
    parser.add_argument("--espera-metricas", type=int, default=90, help="segundos")
    parser.add_argument("--hilos", type=int, default=20)
    parser.add_argument("--fault", default="", help='simula una regresion, ej. "error=0.5"')
    parser.add_argument("--proyecto", default="project-3f57bb8c-371e-4b9c-949")
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--servicio", default="statsnostra-api")
    parser.add_argument("--slo", type=Path, default=gate.SLO_POR_DEFECTO)
    args = parser.parse_args()

    slo = yaml.safe_load(args.slo.read_text(encoding="utf-8"))
    etapas = [int(porcentaje) for porcentaje in args.etapas.split(",")]
    return promover(
        slo, etapas, args.bake, args.espera_metricas, args.canary, args.estable,
        _entorno_real(args),
    )  # fmt: skip


if __name__ == "__main__":
    sys.exit(main())
