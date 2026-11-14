"""Dibuja el tablero de las dos rondas del experimento de agotamiento de CPU.

Un panel por métrica y una columna por ronda, con el eje en minutos desde que
arrancó el fallo, para que las dos rondas se lean una sobre la otra. La franja
sombreada es la ventana de inyección (180 s). Lee solo archivos del repositorio:
la evidencia de cada ronda y los datos de datos/.

Uso: python caos/tablero/dibujar.py   (escribe tablero.png y comparacion.png aquí)
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parent
EVIDENCIA = RAIZ.parent / "evidencia"
ROJO, AZUL, GRIS = "#D55E00", "#0072B2", "#8A8A8A"
RONDAS = {
    "0": {"titulo": "Ronda 0: sin mejoras", "limite_cpu": 250},
    "1": {"titulo": "Ronda 1: con mejoras", "limite_cpu": 500},
}


def hora(texto: str) -> float:
    return datetime.fromisoformat(texto.replace("Z", "+00:00")).replace(tzinfo=timezone.utc).timestamp()


def cargar(ronda: str) -> dict:
    inyeccion = json.loads((RAIZ / "datos" / f"inyeccion-ronda{ronda}.json").read_text(encoding="utf-8"))
    inicio = hora(inyeccion["inicio_utc"])
    saturado = inyeccion["pod_saturado"]

    servidor = {}
    for f in csv.DictReader(open(RAIZ / "datos" / f"servidor-ronda{ronda}.csv", encoding="utf-8")):
        servidor.setdefault(f["pod"], []).append(((hora(f["ventana_utc"]) - inicio) / 60, float(f["p95_ms"])))

    lag = {}
    for f in csv.DictReader(open(EVIDENCIA / f"ronda-{ronda}" / "lag-pods.csv", encoding="utf-8")):
        if f["lag_ms"] != "NA":
            lag.setdefault(f["pod"], []).append(((hora(f["timestamp_utc"]) - inicio) / 60, float(f["lag_ms"])))

    cpu = {}
    for linea in (EVIDENCIA / f"ronda-{ronda}" / "cpu-pods.txt").read_text(encoding="utf-8").splitlines():
        partes = linea.split()
        if not partes:
            continue
        minuto = (hora(partes[0]) - inicio) / 60
        for par in partes[1:]:
            pod, valor = par.split("=")
            cpu.setdefault(pod, []).append((minuto, float(valor.rstrip("m"))))
    return {"saturado": saturado, "servidor": servidor, "lag": lag, "cpu": cpu}


def trazar(ax, series: dict, saturado: str) -> None:
    sanos = [p for p in series if p != saturado]
    for i, pod in enumerate(sorted(sanos)):
        x, y = zip(*series[pod])
        ax.plot(x, y, color=AZUL, alpha=0.35 + 0.5 * (i + 1) / max(len(sanos), 1), lw=1.4,
                label="pod sano" if i == 0 else None)
    if saturado in series:
        x, y = zip(*series[saturado])
        ax.plot(x, y, color=ROJO, lw=2.2, label="pod saturado")


def tablero() -> None:
    datos = {r: cargar(r) for r in RONDAS}
    fig, ejes = plt.subplots(3, 2, figsize=(12, 9), sharex=True, constrained_layout=True)
    filas = [
        ("servidor", "p95 del API de negocio por pod\n(ms, ventanas de 10 s)", None),
        ("lag", "Retraso del bucle de eventos\n(ms)", 50),
        ("cpu", "CPU por pod\n(milicores)", None),
    ]
    for c, (ronda, info) in enumerate(RONDAS.items()):
        d = datos[ronda]
        for f, (clave, etiqueta, umbral) in enumerate(filas):
            ax = ejes[f][c]
            ax.axvspan(0, 3, color=ROJO, alpha=0.08, lw=0)
            trazar(ax, d[clave], d["saturado"])
            if clave == "cpu":
                ax.axhline(info["limite_cpu"], color=GRIS, ls="--", lw=1)
                ax.text(4.45, info["limite_cpu"], f"límite {info['limite_cpu']}m", ha="right", va="bottom", color=GRIS, fontsize=8)
            if clave == "lag" and ronda == "1":
                ax.axhline(umbral, color=GRIS, ls="--", lw=1)
                ax.text(4.45, umbral, "umbral de readiness 50 ms", ha="right", va="bottom", color=GRIS, fontsize=8)
            if c == 0:
                ax.set_ylabel(etiqueta, fontsize=9)
            ax.grid(alpha=0.25)
            ax.set_xlim(-0.2, 4.5)
            for lado in ("top", "right"):
                ax.spines[lado].set_visible(False)
        ejes[0][c].set_title(info["titulo"], fontsize=11, fontweight="bold")
        ejes[2][c].set_xlabel("minutos desde el inicio del fallo (franja = 180 s de CPU saturada)", fontsize=9)
    # Mismo eje vertical en las dos rondas para poder compararlas a simple vista
    for f in range(3):
        techo = max(ejes[f][0].get_ylim()[1], ejes[f][1].get_ylim()[1])
        ejes[f][0].set_ylim(0, techo)
        ejes[f][1].set_ylim(0, techo)
    ejes[0][0].legend(loc="upper left", fontsize=8, frameon=False)
    fig.suptitle("Agotamiento de CPU de un pod del API de Mari en GKE", fontsize=13, fontweight="bold")
    fig.savefig(RAIZ / "tablero.png", dpi=130)
    plt.close(fig)


def resumen(ronda: str) -> dict:
    m = json.loads((EVIDENCIA / f"ronda-{ronda}" / "corrida-1.json").read_text(encoding="utf-8"))["metrics"]
    d = m["http_req_duration"]
    return {"p50": d["med"], "p95": d["p(95)"], "p99": d["p(99)"], "max": d["max"],
            "exito": 100 * (1 - m["http_req_failed"]["value"]), "peticiones": m["http_reqs"]["count"]}


def comparacion() -> None:
    estable = json.loads((EVIDENCIA / "estado-estable" / "estado-estable.json").read_text(encoding="utf-8"))
    base = estable["mediana"]
    r0, r1 = resumen("0"), resumen("1")
    fig, ax = plt.subplots(figsize=(8, 4.2), constrained_layout=True)
    etiquetas = ["p50", "p95", "p99"]
    valores = {
        "Estado estable": [base["p50_ms"], base["p95_ms"], base["p99_ms"]],
        "Ronda 0 (sin mejoras)": [r0["p50"], r0["p95"], r0["p99"]],
        "Ronda 1 (con mejoras)": [r1["p50"], r1["p95"], r1["p99"]],
    }
    colores = [GRIS, ROJO, AZUL]
    ancho = 0.26
    for i, ((nombre, v), color) in enumerate(zip(valores.items(), colores)):
        pos = [k + (i - 1) * ancho for k in range(3)]
        barras = ax.bar(pos, v, ancho, label=nombre, color=color)
        for b, y in zip(barras, v):
            ax.text(b.get_x() + b.get_width() / 2, y + 40, f"{y:.0f}", ha="center", fontsize=8)
    ax.axhline(estable["x_ms"], color="black", ls="--", lw=1)
    ax.text(-0.45, estable["x_ms"] + 40, f"X = {estable['x_ms']} ms (p95 máximo aceptado)", ha="left", fontsize=8)
    ax.set_xticks(range(3), etiquetas)
    ax.set_ylabel("Latencia del flujo medida con k6 (ms)")
    ax.set_title("Latencia del flujo: estado estable y las dos rondas", fontsize=11, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.25)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    fig.savefig(RAIZ / "comparacion.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    tablero()
    comparacion()
    print("tablero.png y comparacion.png escritos en", RAIZ)
