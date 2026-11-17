"""Arma la tabla comparativa de las dos rondas del experimento 2 (resultados.md).

Todo sale de seguridad/evidencia/: la línea base, el resultado de cada ronda y la cuenta de
falsos positivos (alertas recibidas fuera del evento inyectado). Nada está escrito a mano.

Uso: python seguridad/resumen.py
"""

import json
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EVIDENCIA = AQUI / "evidencia"
T1_S, T2_S = 300, 600


def segundos(inicio: str, fin: str) -> float:
    a = datetime.fromisoformat(inicio.replace("Z", "+00:00"))
    b = datetime.fromisoformat(fin.replace("Z", "+00:00"))
    return (b - a).total_seconds()


def cargar(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


base = cargar(EVIDENCIA / "linea-base" / "medicion.json")
r0 = cargar(EVIDENCIA / "ronda-0" / "resultado.json")
r1 = cargar(EVIDENCIA / "ronda-1" / "resultado.json")


def fila(r: dict) -> dict:
    alerta = r["alerta"] != "sin_alerta"
    mttd = segundos(r["creacion_utc"], r["alerta"]) if alerta else None
    contencion = r["segundos_hasta_contencion"]
    return {
        "alerta": alerta,
        "mttd": mttd,
        "mttc": segundos(r["alerta"], r["contencion_utc"]) if alerta else None,
        "total": contencion,
        "senal_s": (
            float(r["senal_en_logs"].split()[0])
            if r["senal_en_logs"] != "sin_deteccion"
            else None
        ),
        "b": r["http_este_oeste"],
        "c": r["http_salida"],
        "nodeport": r["http_nodeport_desde_fuera"],
    }


a, b = fila(r0), fila(r1)


def s(valor, formato="{:.0f} s", vacio="no hubo"):
    return formato.format(valor) if valor is not None else vacio


def bloqueo(codigo: str) -> str:
    return "bloqueada" if codigo == "000" else f"pasó (HTTP {codigo})"


def cumple(r: dict, f: dict) -> str:
    if not f["alerta"]:
        return "se refuta: no hay alerta"
    ok = f["mttd"] <= T1_S and f["total"] <= T2_S
    return "se cumple" if ok else "no se cumple"


lineas = [
    "# Resultados del experimento 2: exposición y segmentación",
    "",
    "Generado por `seguridad/resumen.py` a partir de `evidencia/`. La hipótesis: con la red tal "
    f"como está, al crearse un Service que expone el puerto de administración hay alerta en "
    f"{T1_S // 60} minutos o menos (T1) y contención en {T2_S // 60} minutos o menos (T2).",
    "",
    "| | Ronda 0 (sin mejoras) | Ronda 1 (alerta y NetworkPolicy) |",
    "|---|---|---|",
    f"| Alerta recibida | {'sí' if a['alerta'] else 'no'} | {'sí' if b['alerta'] else 'no'} |",
    f"| MTTD (creación a alerta) | {s(a['mttd'], vacio='no se detectó')} | {s(b['mttd'])} |",
    f"| MTTC (alerta a contención) | {s(a['mttc'], vacio='sin alerta no hubo quién contuviera')} | {s(b['mttc'])} |",
    f"| Contención desde la creación | {s(a['total'])} (la hizo el operador, que ya sabía del evento) | {s(b['total'])} |",
    f"| Evento consultable en Cloud Logging | {s(a['senal_s'])} | {s(b['senal_s'])} |",
    f"| A: NodePort alcanzado desde fuera de la red | {bloqueo(a['nodeport'])} | {bloqueo(b['nodeport'])} |",
    f"| B: salto este-oeste desde otro namespace | {bloqueo(a['b'])} | {bloqueo(b['b'])} |",
    f"| C: salida a Internet sin filtro | {bloqueo(a['c'])} | {bloqueo(b['c'])} |",
    f"| Hipótesis | {cumple(r0, a)} | {cumple(r1, b)} |",
    "",
    "## Línea base de la señal",
    "",
    f"Con un Service inofensivo, el evento de creación se pudo consultar en Cloud Logging a los "
    f"{base['segundos_hasta_consultar']} s. Es el piso de cualquier detección basada en esos registros.",
    "",
    "## Cobertura",
    "",
    "De las tres inyecciones, la alerta cubre la A (1 de 3). La B y la C no generan alerta: se "
    "previenen con la NetworkPolicy, pero hoy no dejan una señal propia. Es un pendiente "
    "explícito (alerta sobre los registros de flujo denegados).",
    "",
    "## Hallazgo posterior (17 de noviembre)",
    "",
    "Al dejar la NetworkPolicy en el despliegue, los pods nuevos no pudieron abrir conexiones a la "
    "base ni a Grafana: `/api/v1/partidos` dio 500 tras 30 s de espera en un pod y la exportación "
    "de telemetría agotó el tiempo. Al borrar las políticas el servicio volvió en segundos y se "
    "sacaron del despliegue. En la ronda 1 el flujo seguía dando 200 porque las conexiones ya "
    "abiertas no necesitan resolver nombres ni renovar certificados. Causa probable, sin "
    "confirmar: falta permitir la salida de DNS hacia la caché local de nodos (node-local-dns). "
    "Antes de volver a dejarla hay que probarla con pods recién creados.",
    "",
]
(AQUI / "resultados.md").write_text("\n".join(lineas), encoding="utf-8")
print("\n".join(lineas))
