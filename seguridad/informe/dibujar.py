"""Gráficas del informe de seguridad, calculadas con seguridad/evidencia/ y la bitácora.

Escribe cronologia.png, resultados.png, identidades.png y capas.png en esta carpeta. Los
tiempos salen de los JSON de cada ronda y de las filas de la bitácora; los conteos, de los
JSON del inventario de identidades. Misma paleta que el informe de caos: azul para la referencia, morado
para lo que falla o queda abierto y verde para lo que se controla.

Uso: python seguridad/informe/dibujar.py
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

AQUI = Path(__file__).resolve().parent
SEGURIDAD = AQUI.parent
EVIDENCIA = SEGURIDAD / "evidencia"

AZUL, MORADO, VERDE = "#3b8eea", "#7b3fb0", "#12a150"
TINTA, TINTA_SUAVE, FONDO, REJILLA = "#14213d", "#4b5563", "#ffffff", "#e5e7eb"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 11,
        "text.color": TINTA,
        "axes.labelcolor": TINTA_SUAVE,
        "xtick.color": TINTA_SUAVE,
        "ytick.color": TINTA_SUAVE,
        "axes.edgecolor": "#9ca3af",
        "figure.facecolor": FONDO,
        "axes.facecolor": FONDO,
        "savefig.facecolor": FONDO,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.unicode_minus": True,
    }
)


def cargar(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


def utc(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00")).replace(tzinfo=None)


def filas_bitacora():
    """(hora UTC, texto de la acción) de cada fila de la bitácora que tiene hora."""
    filas = []
    dia = None
    for linea in (SEGURIDAD / "bitacora.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(\d\d):(\d\d):(\d\d)\s*\|[^|]*\|([^|]*)\|", linea)
        if not m:
            continue
        h, mi, s, accion = int(m[1]), int(m[2]), int(m[3]), m[4].strip()
        dia = dia or datetime(2026, 11, 15)
        filas.append((dia + timedelta(hours=h + 5, minutes=mi, seconds=s), accion))
    return filas


def eventos(ronda: int):
    """Eventos de una ronda en segundos desde la creación del Service."""
    r = cargar(EVIDENCIA / f"ronda-{ronda}" / "resultado.json")
    t0 = utc(r["creacion_utc"])
    ev = {"A": 0.0}
    for hora, accion in filas_bitacora():
        if not accion.startswith(f"Ronda {ronda}"):
            continue
        t = (hora - t0).total_seconds()
        if "inyección B" in accion:
            ev["B"] = t
        elif "inyección C" in accion:
            ev["C"] = t
    ev["Log"] = (
        float(r["senal_en_logs"].split()[0]) if r["senal_en_logs"] != "sin_deteccion" else None
    )
    ev["Alerta"] = (
        (utc(r["alerta"]) - t0).total_seconds() if r["alerta"] != "sin_alerta" else None
    )
    ev["Contención"] = (utc(r["contencion_utc"]) - t0).total_seconds()
    return ev, r


NOMBRES = {
    "A": "A: creo el Service\nexpuesto",
    "B": "B: salto este-oeste",
    "C": "C: salida a Internet",
    "Log": "evento visible\nen Cloud Logging",
    "Alerta": "llega la alerta",
    "Contención": "contención\n(borro el Service)",
}


def cronologia() -> None:
    """Un renglón por evento y un panel por ronda, para leerla de arriba abajo."""
    orden = ["A", "B", "C", "Log", "Alerta", "Contención"]
    nombres = {
        "A": "A: creo el Service expuesto",
        "B": "B: salto este-oeste",
        "C": "C: salida a Internet",
        "Log": "evento visible en Cloud Logging",
        "Alerta": "llega la alerta",
        "Contención": "contención: borro el Service",
    }
    fig, ejes = plt.subplots(
        1, 2, figsize=(9.8, 3.4), sharey=True, gridspec_kw={"wspace": 0.08}
    )
    datos = [eventos(0), eventos(1)]
    techo = max(ev["Contención"] for ev, _ in datos) * 1.22
    for ax, (ev, _), color, titulo in zip(
        ejes,
        datos,
        (MORADO, VERDE),
        ("Ronda 0, sin mejoras", "Ronda 1, con alerta y NetworkPolicy"),
        strict=True,
    ):
        for fila, clave in enumerate(orden):
            y = len(orden) - 1 - fila
            valor = ev.get(clave)
            ax.axhline(y, color=REJILLA, lw=0.8, zorder=0)
            if valor is None:
                ax.text(
                    0.5,
                    y,
                    "no ocurrió",
                    va="center",
                    fontsize=9.5,
                    color=MORADO,
                    fontweight="bold",
                )
                continue
            ax.hlines(y, 0, valor, color=color, lw=2.2, alpha=0.5)
            ax.plot(valor, y, "o", color=color, ms=9, zorder=3)
            ax.text(
                valor + techo * 0.02,
                y,
                f"{valor:.0f} s",
                va="center",
                fontsize=10,
                fontweight="bold",
            )
        ax.set_xlim(-1, techo)
        ax.set_ylim(-0.6, len(orden) - 0.4)
        ax.set_yticks(range(len(orden)), [nombres[c] for c in reversed(orden)])
        ax.tick_params(axis="y", length=0)
        ax.set_xlabel("segundos desde que se crea el Service")
        ax.set_title(titulo, loc="left", fontsize=12, fontweight="bold")
        ax.spines["left"].set_visible(False)
    fig.savefig(AQUI / "cronologia.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def resultados() -> None:
    _, r0 = eventos(0)
    _, r1 = eventos(1)
    filas = [
        (
            "A: Service expuesto",
            "alerta",
            r0["alerta"] != "sin_alerta",
            r1["alerta"] != "sin_alerta",
        ),
        (
            "B: salto este-oeste",
            "bloqueo",
            r0["http_este_oeste"] == "000",
            r1["http_este_oeste"] == "000",
        ),
        (
            "C: salida a Internet",
            "bloqueo",
            r0["http_salida"] == "000",
            r1["http_salida"] == "000",
        ),
    ]
    fig, ax = plt.subplots(figsize=(7.6, 2.9))
    ax.set_xlim(0, 3.2)
    ax.set_ylim(0, 3.6)
    ax.axis("off")
    ax.text(1.6, 3.35, "Ronda 0", ha="center", fontsize=12, fontweight="bold", color=MORADO)
    ax.text(2.7, 3.35, "Ronda 1", ha="center", fontsize=12, fontweight="bold", color=VERDE)
    for i, (nombre, tipo, ok0, ok1) in enumerate(filas):
        y = 2.3 - i * 1.0
        ax.text(0.05, y + 0.25, nombre, fontsize=11.5, va="center", fontweight="bold")
        ax.text(
            0.05,
            y - 0.05,
            "se mide con una alerta" if tipo == "alerta" else "se previene con la política",
            fontsize=9,
            va="center",
            color=TINTA_SUAVE,
        )
        for x, ok in ((1.6, ok0), (2.7, ok1)):
            texto = (
                ("alerta" if tipo == "alerta" else "bloqueada")
                if ok
                else ("sin alerta" if tipo == "alerta" else "pasó")
            )
            color = VERDE if ok else MORADO
            ax.add_patch(
                FancyBboxPatch(
                    (x - 0.46, y - 0.2),
                    0.92,
                    0.7,
                    boxstyle="round,pad=0.02,rounding_size=0.12",
                    fc=color,
                    ec="none",
                    alpha=0.92,
                )
            )
            ax.text(
                x,
                y + 0.15,
                texto,
                ha="center",
                va="center",
                color="white",
                fontsize=11.5,
                fontweight="bold",
            )
    fig.savefig(AQUI / "resultados.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def identidades() -> None:
    antes = {
        c["cuenta"].split("@")[0]: c for c in cargar(EVIDENCIA / "identidades" / "antes.json")
    }
    despues = {
        c["cuenta"].split("@")[0]: c
        for c in cargar(EVIDENCIA / "identidades" / "despues.json")
    }
    cuenta = "statsnostra-ci"
    a, d = antes[cuenta], despues[cuenta]
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    etiquetas = ["Roles en el proyecto", "De ellos, de administración"]
    antes_v = [len(a["roles"]), len(a["roles_admin"])]
    despues_v = [len(d["roles"]), len(d["roles_admin"])]
    ancho = 0.34
    ax.bar([x - ancho / 2 for x in range(2)], antes_v, ancho, color=MORADO, label="antes")
    ax.bar([x + ancho / 2 for x in range(2)], despues_v, ancho, color=VERDE, label="después")
    for x, (v0, v1) in enumerate(zip(antes_v, despues_v, strict=True)):
        ax.text(x - ancho / 2, v0 + 0.3, str(v0), ha="center", fontweight="bold")
        ax.text(x + ancho / 2, v1 + 0.3, str(v1), ha="center", fontweight="bold")
    ax.set_xticks(range(2), etiquetas)
    ax.set_ylim(0, max(antes_v) * 1.25)
    ax.legend(frameon=False, loc="upper right")
    ax.grid(axis="y", color=REJILLA, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_title(
        "Cuenta del despliegue (statsnostra-ci)", loc="left", fontsize=12, fontweight="bold"
    )
    fig.savefig(AQUI / "identidades.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def capas() -> None:
    inventario = (SEGURIDAD / "inventario-controles.md").read_text(encoding="utf-8")
    cuenta = {}
    for bloque in re.split(r"^## ", inventario, flags=re.M)[1:]:
        titulo = bloque.splitlines()[0].strip()
        if titulo == "Cómo se usa":
            continue
        cerrados = bloque.count("cerrado el 15 nov")
        activos = bloque.count("| Activo") - cerrados
        cuenta[titulo] = (activos, cerrados, bloque.count("**Hueco**"))
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, len(cuenta) * 10 + 8)
    ax.axis("off")
    inyecciones = {"Red": "inyecciones A, B y C", "Detección y respuesta": "señal de A"}
    colores = (VERDE, AZUL, MORADO)
    for i, (capa, conteo) in enumerate(reversed(list(cuenta.items()))):
        y = 2 + i * 10
        ax.add_patch(
            FancyBboxPatch(
                (1, y),
                19,
                7,
                boxstyle="round,pad=0.2,rounding_size=1",
                fc="#eaf1fb",
                ec=AZUL,
                lw=1.4,
            )
        )
        ax.text(10.5, y + 3.5, capa, ha="center", va="center", fontsize=10, fontweight="bold")
        x = 23
        for n_estado, color in zip(conteo, colores, strict=True):
            for _ in range(n_estado):
                ax.add_patch(
                    FancyBboxPatch(
                        (x, y + 1),
                        4.6,
                        5,
                        boxstyle="round,pad=0.1,rounding_size=0.8",
                        fc=color,
                        ec="none",
                    )
                )
                x += 5.6
        if capa in inyecciones:
            ax.text(
                99,
                y + 3.5,
                inyecciones[capa],
                ha="right",
                va="center",
                fontsize=9.5,
                color=MORADO,
                fontweight="bold",
            )
    # Leyenda
    for k, (texto, color) in enumerate(
        (
            ("activo desde el inicio", VERDE),
            ("cerrado en este trabajo", AZUL),
            ("hueco abierto", MORADO),
        )
    ):
        x0 = 23 + k * 26
        ax.add_patch(
            FancyBboxPatch(
                (x0, len(cuenta) * 10 + 3.2),
                3,
                3,
                boxstyle="round,pad=0.05,rounding_size=0.5",
                fc=color,
                ec="none",
            )
        )
        ax.text(
            x0 + 4.5,
            len(cuenta) * 10 + 4.7,
            texto,
            va="center",
            fontsize=10,
            color=TINTA_SUAVE,
        )
    fig.savefig(AQUI / "capas.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    cronologia()
    resultados()
    identidades()
    capas()
    print("gráficas escritas en", AQUI)
