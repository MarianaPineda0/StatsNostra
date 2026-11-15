"""Dibuja las gráficas del experimento de CPU a partir de la evidencia del repositorio.

Escribe en esta carpeta resultados.png, tablero.png y reparto.png. No hay ningún número
escrito a mano: todo sale de evidencia/ y de datos/ (ver README.md de esta carpeta).

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

RAIZ = Path(__file__).resolve().parent
EVIDENCIA = RAIZ.parent / "evidencia"

AZUL, NARANJA, GRIS = "#2a78d6", "#eb6834", "#8a8a85"
TINTA, TINTA_SUAVE, FONDO = "#0b0b0b", "#52514e", "#fcfcfb"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "text.color": TINTA, "axes.labelcolor": TINTA_SUAVE,
    "xtick.color": TINTA_SUAVE, "ytick.color": TINTA_SUAVE, "axes.edgecolor": "#c9c8c2",
    "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
    "axes.spines.top": False, "axes.spines.right": False,
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


def etiqueta_directa(ax, x, y, texto, **kw):
    ax.text(x, y, texto, ha=kw.pop("ha", "left"), va=kw.pop("va", "center"), fontsize=kw.pop("fontsize", 9), **kw)


def resultados() -> None:
    est, r0, r1 = estable(), resumen_k6("0"), resumen_k6("1")
    nombres = ["Estado estable", "Ronda 0\n(sin mejoras)", "Ronda 1\n(con mejoras)"]
    colores = [GRIS, NARANJA, AZUL]
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.1), gridspec_kw={"width_ratios": [1.25, 1]})

    p95 = [est["p95"], r0["p95"], r1["p95"]]
    a.barh(nombres[::-1], p95[::-1], color=colores[::-1], height=0.58)
    a.axvline(est["x"], color=TINTA, ls="--", lw=1, zorder=0)
    etiqueta_directa(a, est["x"] + 40, 0.5, f"límite {miles(est['x'])} ms", fontsize=8, color=TINTA_SUAVE)
    for i, v in enumerate(p95[::-1]):
        etiqueta_directa(a, v + 50, i, f"{miles(v)} ms", fontweight="bold",
                         bbox=dict(facecolor=FONDO, edgecolor="none", pad=1.5))
    a.set_xlim(0, max(p95) * 1.22)
    a.set_title("Latencia p95 del flujo", loc="left", fontsize=10, fontweight="bold")
    a.tick_params(axis="y", length=0)
    a.set_xlabel("milisegundos, medido con k6")

    flujos = [est["flujos"], r0["flujos"], r1["flujos"]]
    b.bar(range(3), flujos, color=colores, width=0.58)
    for i, v in enumerate(flujos):
        etiqueta_directa(b, i, v + max(flujos) * 0.03, miles(v), ha="center", fontweight="bold")
    b.set_xticks(range(3), ["Estable", "Ronda 0", "Ronda 1"])
    b.set_ylim(0, max(flujos) * 1.18)
    b.set_title("Flujos completados en la prueba", loc="left", fontsize=10, fontweight="bold")
    b.tick_params(axis="x", length=0)
    fig.tight_layout()
    fig.savefig(RAIZ / "resultados.png", dpi=170)
    plt.close(fig)


def trazar(ax, series, saturado, etiquetar=False):
    sanos = sorted(p for p in series if p != saturado)
    for i, pod in enumerate(sanos):
        x, y = zip(*series[pod])
        ax.plot(x, y, color=AZUL, alpha=0.9 - 0.2 * i if len(sanos) > 1 else 0.9, lw=1.3,
                label="pods sanos" if (etiquetar and i == 0) else None)
    if saturado in series:
        x, y = zip(*series[saturado])
        ax.plot(x, y, color=NARANJA, lw=2.2, label="pod saturado" if etiquetar else None)


def tablero() -> None:
    rondas = {"0": "Ronda 0, sin mejoras", "1": "Ronda 1, con mejoras"}
    limites = {"0": 250, "1": 500}
    datos = {r: cargar_ronda(r) for r in rondas}
    fig, ejes = plt.subplots(3, 2, figsize=(10.2, 7.6), sharex=True)
    filas = [("servidor", "p95 que ve el servidor (ms)"), ("lag", "retraso del bucle (ms)"),
             ("cpu", "CPU por pod (milicores)")]
    for c, r in enumerate(rondas):
        d = datos[r]
        for f, (clave, etiqueta) in enumerate(filas):
            ax = ejes[f][c]
            ax.axvspan(0, d["duracion_min"], color=NARANJA, alpha=0.08, lw=0)
            trazar(ax, d[clave], d["saturado"], etiquetar=(f == 0 and c == 0))
            ax.grid(axis="y", alpha=0.25)
            ax.set_xlim(-0.1, 4.4)
            if c == 0:
                ax.set_ylabel(etiqueta, fontsize=8.5)
        ejes[2][c].axhline(limites[r], color=TINTA_SUAVE, ls="--", lw=1)
        etiqueta_directa(ejes[2][c], 4.35, limites[r], f"límite {limites[r]}m", ha="right", va="bottom",
                         fontsize=8, color=TINTA_SUAVE)
        if r == "1":
            ejes[1][c].axhline(50, color=TINTA_SUAVE, ls="--", lw=1)
            etiqueta_directa(ejes[1][c], 4.35, 50, "umbral 50 ms", ha="right", va="bottom",
                             fontsize=8, color=TINTA_SUAVE)
            sube = next((m for m, n in d["pods"] if n > 2), None)
            if sube is not None:
                ejes[2][c].annotate("el HPA suma réplicas", xy=(sube, 0), xytext=(sube + 0.25, 40),
                                    fontsize=8, color=TINTA_SUAVE,
                                    arrowprops=dict(arrowstyle="-", color=TINTA_SUAVE, lw=0.8))
        ejes[0][c].set_title(rondas[r], loc="left", fontsize=10, fontweight="bold")
        ejes[2][c].set_xlabel("minutos desde que empezó el fallo (zona naranja: CPU saturada)", fontsize=8.5)
    for f in range(3):
        techo = max(ejes[f][0].get_ylim()[1], ejes[f][1].get_ylim()[1])
        ejes[f][0].set_ylim(0, techo)
        ejes[f][1].set_ylim(0, techo)
    ejes[0][0].legend(loc="upper left", frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(RAIZ / "tablero.png", dpi=150)
    plt.close(fig)


def reparto() -> None:
    res = json_de(RAIZ / "datos" / "resumen-pods.json")
    fig, ax = plt.subplots(figsize=(5.4, 2.9))
    ancho = 0.36
    for desplaza, r, color, nombre in ((-ancho / 2, "ronda0", NARANJA, "Ronda 0"), (ancho / 2, "ronda1", AZUL, "Ronda 1")):
        minutos = [m for m in res[r]["reparto_por_minuto"] if m["minuto"] <= 2]
        xs = [m["minuto"] + desplaza for m in minutos]
        vals = [100 * m["parte_saturado"] for m in minutos]
        ax.bar(xs, vals, ancho, color=color, label=nombre)
        for x, v in zip(xs, vals):
            etiqueta_directa(ax, x, v + 0.8, f"{v:.0f} %", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(range(3), ["minuto 1", "minuto 2", "minuto 3"])
    ax.set_ylabel("% de las llamadas del API")
    ax.set_ylim(0, 27)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("Parte del tráfico que recibió el pod saturado", loc="left", fontsize=10, fontweight="bold")
    fig.tight_layout()
    fig.savefig(RAIZ / "reparto.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    resultados()
    tablero()
    reparto()
    print("gráficas escritas en", RAIZ)
