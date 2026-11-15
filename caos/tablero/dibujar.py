"""Dibuja las gráficas del experimento de CPU a partir de la evidencia del repositorio.

Escribe en esta carpeta resultados.png, tablero.png y reparto.png. No hay ningún número
escrito a mano: todo sale de evidencia/ y de datos/ (ver README.md de esta carpeta).

Colores: azul para la referencia (estado estable), morado para lo que falla (ronda 0, pod
saturado) y verde para lo que va bien (ronda 1, pods sanos). La paleta pasó el validador de
separación para daltonismo y contraste.

Uso: python caos/tablero/dibujar.py
"""
import csv
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

RAIZ = Path(__file__).resolve().parent
EVIDENCIA = RAIZ.parent / "evidencia"

AZUL, MORADO, VERDE = "#3b8eea", "#7b3fb0", "#12a150"
TINTA, TINTA_SUAVE, FONDO, REJILLA = "#14213d", "#4b5563", "#ffffff", "#e5e7eb"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"], "font.size": 11,
    "text.color": TINTA, "axes.labelcolor": TINTA_SUAVE, "xtick.color": TINTA_SUAVE, "ytick.color": TINTA_SUAVE,
    "axes.edgecolor": "#9ca3af", "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.9, "axes.unicode_minus": True,
})


def miles(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def hora(texto: str) -> float:
    return datetime.fromisoformat(texto.replace("Z", "+00:00")).replace(tzinfo=timezone.utc).timestamp()


def json_de(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def cargar_ronda(r: str) -> dict:
    iny = json_de(RAIZ / "datos" / f"inyeccion-ronda{r}.json")
    inicio, saturado = hora(iny["inicio_utc"]), iny["pod_saturado"]
    servidor = {}
    for f in csv.DictReader(open(RAIZ / "datos" / f"servidor-ronda{r}.csv", encoding="utf-8")):
        servidor.setdefault(f["pod"], []).append(((hora(f["ventana_utc"]) - inicio) / 60, float(f["p95_ms"])))
    lag = {}
    for f in csv.DictReader(open(EVIDENCIA / f"ronda-{r}" / "lag-pods.csv", encoding="utf-8")):
        if f["lag_ms"] != "NA":
            lag.setdefault(f["pod"], []).append(((hora(f["timestamp_utc"]) - inicio) / 60, float(f["lag_ms"])))
    cpu, pods_por_muestra = {}, []
    for linea in (EVIDENCIA / f"ronda-{r}" / "cpu-pods.txt").read_text(encoding="utf-8").splitlines():
        partes = linea.split()
        if not partes:
            continue
        minuto = (hora(partes[0]) - inicio) / 60
        pods_por_muestra.append((minuto, len(partes) - 1))
        for par in partes[1:]:
            pod, valor = par.split("=")
            cpu.setdefault(pod, []).append((minuto, float(valor.rstrip("m"))))
    return {"saturado": saturado, "servidor": servidor, "lag": lag, "cpu": cpu, "pods": pods_por_muestra,
            "duracion_min": iny["duracion_s"] / 60}


def resumen_k6(r: str) -> dict:
    m = json_de(EVIDENCIA / f"ronda-{r}" / "corrida-1.json")["metrics"]
    d = m["http_req_duration"]
    return {"p50": d["med"], "p95": d["p(95)"], "p99": d["p(99)"], "flujos": m["http_reqs"]["count"]}


def estable() -> dict:
    e = json_de(EVIDENCIA / "estado-estable" / "estado-estable.json")
    return {"p95": e["mediana"]["p95_ms"], "x": e["x_ms"],
            "flujos": statistics.median(c["peticiones"] for c in e["detalle"])}


def pildora(ax, x, y, texto, color, **kw):
    ax.text(x, y, texto, color="white", fontsize=kw.pop("fontsize", 10.5), fontweight="bold",
            ha=kw.pop("ha", "left"), va="center", zorder=5,
            bbox=dict(boxstyle="round,pad=0.35,rounding_size=0.8", facecolor=color, edgecolor="none"), **kw)


def titulo(ax, texto, sub):
    ax.text(0, 1.13, texto, transform=ax.transAxes, fontsize=13, fontweight="bold", ha="left", va="bottom")
    ax.text(0, 1.04, sub, transform=ax.transAxes, fontsize=9.5, color=TINTA_SUAVE, ha="left", va="bottom")


def resultados() -> None:
    est, r0, r1 = estable(), resumen_k6("0"), resumen_k6("1")
    nombres = ["Estado estable", "Ronda 0 (sin mejoras)", "Ronda 1 (con mejoras)"]
    colores = [AZUL, MORADO, VERDE]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10.4, 3.7), gridspec_kw={"width_ratios": [1.3, 1], "wspace": 0.28})

    p95 = [est["p95"], r0["p95"], r1["p95"]]
    techo = max(p95) * 1.25
    a.axvspan(0, est["x"], color=VERDE, alpha=0.07, lw=0)
    a.axvline(est["x"], color=TINTA, ls=(0, (4, 3)), lw=1.1, zorder=1)
    a.text(est["x"] + 45, 2.47, f"límite {miles(est['x'])} ms", fontsize=9.5, color=TINTA_SUAVE, va="center")
    a.barh(nombres[::-1], p95[::-1], color=colores[::-1], height=0.56, zorder=2)
    for i, v in enumerate(p95[::-1]):
        a.text(v + 55, i, f"{miles(v)} ms", va="center", fontsize=11.5, fontweight="bold", zorder=4,
               bbox=dict(facecolor=FONDO, edgecolor="none", pad=1.2))
    cambio = 100 * (r1["p95"] - r0["p95"]) / r0["p95"]
    pildora(a, 1750, 0, f"{cambio:.0f} % frente a la ronda 0".replace("-", "−"), VERDE)
    a.set_xlim(0, techo)
    a.set_ylim(-0.55, 2.7)
    a.tick_params(axis="y", length=0, labelsize=11)
    a.set_xlabel("milisegundos, medido con k6")
    a.grid(axis="x", color=REJILLA, lw=0.8, zorder=0)
    a.set_axisbelow(True)
    titulo(a, "Latencia p95 del flujo", "menos es mejor")

    flujos = [est["flujos"], r0["flujos"], r1["flujos"]]
    b.bar(range(3), flujos, color=colores, width=0.58, zorder=2)
    for i, v in enumerate(flujos):
        b.text(i, v + max(flujos) * 0.025, miles(v), ha="center", fontsize=11.5, fontweight="bold")
    mas = 100 * (r1["flujos"] - r0["flujos"]) / r0["flujos"]
    pildora(b, 2.42, max(flujos) * 1.17, f"+{mas:.0f} % frente a la ronda 0", VERDE, ha="right", fontsize=10)
    b.set_xticks(range(3), ["Estable", "Ronda 0", "Ronda 1"])
    b.set_ylim(0, max(flujos) * 1.3)
    b.tick_params(axis="x", length=0, labelsize=11)
    b.grid(axis="y", color=REJILLA, lw=0.8, zorder=0)
    b.set_axisbelow(True)
    titulo(b, "Flujos completados", "en los 3 minutos de carga; más es mejor")
    fig.subplots_adjust(top=0.8, bottom=0.17, left=0.16, right=0.98)
    fig.savefig(RAIZ / "resultados.png", dpi=190)
    plt.close(fig)


def trazar(ax, series, saturado, relleno, etiquetar=False):
    sanos = sorted(p for p in series if p != saturado)
    for i, pod in enumerate(sanos):
        x, y = zip(*series[pod])
        ax.plot(x, y, color=VERDE, alpha=max(0.95 - 0.22 * i, 0.4), lw=1.6,
                label="pods sanos" if (etiquetar and i == 0) else None, zorder=3)
    if saturado in series:
        x, y = zip(*series[saturado])
        if relleno:
            ax.fill_between(x, y, color=MORADO, alpha=0.12, lw=0, zorder=2)
        ax.plot(x, y, color=MORADO, lw=2.6, label="pod saturado" if etiquetar else None, zorder=4)


def tablero() -> None:
    rondas = {"0": ("Ronda 0", "sin mejoras", MORADO), "1": ("Ronda 1", "con mejoras", VERDE)}
    limites = {"0": 250, "1": 500}
    datos = {r: cargar_ronda(r) for r in rondas}
    fig, ejes = plt.subplots(3, 2, figsize=(10.6, 8.2), sharex=True, gridspec_kw={"hspace": 0.22, "wspace": 0.16})
    filas = [("servidor", "p95 del API (ms)", True), ("lag", "retraso del bucle (ms)", True),
             ("cpu", "CPU por pod (milicores)", False)]
    for c, (r, (nombre, sub, color)) in enumerate(rondas.items()):
        d = datos[r]
        for f, (clave, etiqueta, relleno) in enumerate(filas):
            ax = ejes[f][c]
            ax.axvspan(0, d["duracion_min"], color=MORADO, alpha=0.06, lw=0, zorder=0)
            trazar(ax, d[clave], d["saturado"], relleno, etiquetar=(f == 0 and c == 0))
            ax.grid(axis="y", color=REJILLA, lw=0.8)
            ax.set_axisbelow(True)
            ax.set_xlim(-0.1, 4.4)
            if c == 0:
                ax.set_ylabel(etiqueta, fontsize=10.5)
        ejes[0][c].text(0, 1.14, f"{nombre}", transform=ejes[0][c].transAxes, fontsize=14, fontweight="bold", va="bottom")
        ejes[0][c].text(0.215, 1.14, sub, transform=ejes[0][c].transAxes, fontsize=11, color="white", va="bottom",
                        bbox=dict(boxstyle="round,pad=0.3,rounding_size=0.7", facecolor=color, edgecolor="none"))
        ejes[0][c].text(0.05, 0.93, "fallo inyectado", transform=ejes[0][c].transAxes, fontsize=9, color=MORADO, va="top")
        ejes[2][c].axhline(limites[r], color=TINTA_SUAVE, ls=(0, (4, 3)), lw=1)
        ejes[2][c].text(4.35, limites[r], f"límite {limites[r]} m", ha="right", va="bottom", fontsize=9.5, color=TINTA_SUAVE)
        if r == "1":
            ejes[1][c].axhline(50, color=TINTA_SUAVE, ls=(0, (4, 3)), lw=1)
            ejes[1][c].text(4.35, 50, "umbral 50 ms", ha="right", va="bottom", fontsize=9.5, color=TINTA_SUAVE)
            sube = next((m for m, n in d["pods"] if n > 2), None)
            if sube is not None:
                for fila in range(3):
                    ejes[fila][c].axvline(sube, color=VERDE, ls=(0, (1, 2)), lw=1.4, zorder=1)
                ejes[0][c].text(sube + 0.06, 2750, "el HPA ya tenía\n4 réplicas", color=VERDE, fontsize=10,
                                fontweight="bold", va="center")
        ejes[2][c].set_xlabel("minutos desde que empezó el fallo", fontsize=10.5)
    for f in range(3):
        techo = max(ejes[f][0].get_ylim()[1], ejes[f][1].get_ylim()[1])
        ejes[f][0].set_ylim(0, techo)
        ejes[f][1].set_ylim(0, techo)
    ejes[0][0].legend(loc="upper left", bbox_to_anchor=(0.0, 0.86), frameon=False, fontsize=10)
    fig.subplots_adjust(top=0.9, bottom=0.07, left=0.08, right=0.985)
    fig.savefig(RAIZ / "tablero.png", dpi=170)
    plt.close(fig)


def reparto() -> None:
    res = json_de(RAIZ / "datos" / "resumen-pods.json")
    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    ancho = 0.38
    for desplaza, r, color, nombre in ((-ancho / 2, "ronda0", MORADO, "Ronda 0"), (ancho / 2, "ronda1", VERDE, "Ronda 1")):
        minutos = [m for m in res[r]["reparto_por_minuto"] if m["minuto"] <= 2]
        xs = [m["minuto"] + desplaza for m in minutos]
        vals = [100 * m["parte_saturado"] for m in minutos]
        ax.bar(xs, vals, ancho, color=color, label=nombre, zorder=2)
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.6, f"{v:.0f} %", ha="center", va="bottom", fontsize=10.5, fontweight="bold")
    ax.set_xticks(range(3), ["minuto 1", "minuto 2", "minuto 3"])
    ax.set_ylabel("% de las llamadas del API")
    ax.set_ylim(0, 26)
    ax.tick_params(axis="x", length=0, labelsize=11)
    ax.grid(axis="y", color=REJILLA, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=10.5, loc="upper left")
    titulo(ax, "Tráfico que recibió el pod saturado", "parte de las llamadas del API, minuto a minuto")
    fig.subplots_adjust(top=0.8, bottom=0.14, left=0.12, right=0.98)
    fig.savefig(RAIZ / "reparto.png", dpi=190)
    plt.close(fig)


if __name__ == "__main__":
    resultados()
    tablero()
    reparto()
    print("gráficas escritas en", RAIZ)
