"""Dibuja el diagrama de arquitectura del experimento (arquitectura.png)."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

AZUL, ROJO, GRIS, VERDE = "#0072B2", "#D55E00", "#555555", "#009E73"
fig, ax = plt.subplots(figsize=(9.2, 3.3))
ax.set_xlim(0, 100)
ax.set_ylim(0, 36)
ax.axis("off")


def caja(x, y, w, h, texto, color, relleno="white", tam=8, negrita=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2",
                                fc=relleno, ec=color, lw=1.6))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=tam,
            fontweight="bold" if negrita else "normal", color="#222")


def flecha(x1, y1, x2, y2, color=GRIS):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4))


caja(1, 14, 12, 8, "k6\n5, 15 y 30\nusuarios", GRIS)
caja(19, 14, 17, 8, "Coordinador\n(Azure, Juan)\nflujo con X-Trace-Id", AZUL)
caja(42, 24, 15, 8, "API de Pipe\n(AWS)", AZUL)
ax.add_patch(FancyBboxPatch((42, 3), 55, 18, boxstyle="round,pad=0.3,rounding_size=1.2",
                            fc="#F6FAFD", ec=AZUL, lw=1.6))
ax.text(44, 19, "GKE zonal (Dataplane V2) · API de Mari, IP 34.68.14.217", fontsize=8, fontweight="bold", va="center")
caja(45, 6, 13, 8, "Servicio\nbalanceador", GRIS, tam=7.5)
caja(62, 10.5, 15, 6.5, "Pod 1 · API\n(el que se satura)", ROJO, "#FBEFE6", tam=7.5)
caja(62, 4, 15, 6, "Pod 2 · API\n(+ HPA: hasta 4)", AZUL, tam=7.5)
caja(82, 7, 13, 8, "Cloud SQL\n(por proxy)", GRIS, tam=7.5)
flecha(13, 18, 19, 18)
flecha(36, 20, 42, 27)
flecha(36, 16, 45, 11)
flecha(58, 11, 62, 13.5)
flecha(58, 10, 62, 7)
flecha(77, 13, 82, 11.5)
flecha(77, 7, 82, 9.5)
ax.text(1, 9, "Falla: un pod consume\nCPU 180 s (POST /fault/cpu)", color=ROJO, fontsize=7.5, fontweight="bold", va="top")
ax.text(1, 3.5, "Se mide: p95 del flujo (k6),\nretraso del bucle y CPU por pod", color=GRIS, fontsize=7.5, va="top")
fig.savefig(Path(__file__).with_name("arquitectura.png"), dpi=150, bbox_inches="tight")
