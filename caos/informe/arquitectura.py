"""Dibuja el diagrama del flujo y de dónde se inyecta la falla (arquitectura.png)."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

AZUL, NARANJA, GRIS = "#2a78d6", "#eb6834", "#8a8a85"
TINTA, FONDO = "#0b0b0b", "#fcfcfb"

fig, ax = plt.subplots(figsize=(9.4, 3.4))
fig.patch.set_facecolor(FONDO)
ax.set_xlim(0, 100)
ax.set_ylim(0, 38)
ax.axis("off")


def caja(x, y, w, h, titulo, detalle, borde, relleno=FONDO):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2", fc=relleno, ec=borde, lw=1.6))
    ax.text(x + w / 2, y + h * 0.62, titulo, ha="center", va="center", fontsize=8.8, fontweight="bold", color=TINTA)
    if detalle:
        ax.text(x + w / 2, y + h * 0.27, detalle, ha="center", va="center", fontsize=7.4, color="#52514e")


def flecha(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color="#52514e", lw=1.3))


caja(1, 15, 13, 9, "k6", "hasta 30 usuarios", GRIS)
caja(20, 15, 19, 9, "trading-journal", "Azure · arma el flujo", AZUL)
caja(45, 28, 17, 8, "ecommerce", "AWS", AZUL)
ax.add_patch(FancyBboxPatch((45, 1.5), 53, 21, boxstyle="round,pad=0.25,rounding_size=1.2", fc="#f3f7fc", ec=AZUL, lw=1.6))
ax.text(47, 20, "StatsNostra en GKE · 34.68.14.217", fontsize=8.8, fontweight="bold", va="center", color=TINTA)
caja(47.5, 5, 14.5, 9, "Balanceador", "reparte el tráfico", GRIS)
caja(65, 11.5, 15, 6.5, "Pod saturado", "consume CPU 180 s", NARANJA, "#fdf0ea")
caja(65, 3, 15, 6.5, "Pods sanos", "2 al inicio, hasta 4", AZUL)
caja(84, 6.5, 13, 8, "Cloud SQL", "por proxy", GRIS)
flecha(14, 19.5, 20, 19.5)
flecha(39, 22, 45, 30)
flecha(39, 18, 48, 11)
flecha(61, 11.5, 65, 14.5)
flecha(61, 8.5, 65, 6.5)
flecha(80, 14.5, 84, 12)
flecha(80, 6.5, 84, 9)
fig.savefig(Path(__file__).with_name("arquitectura.png"), dpi=170, bbox_inches="tight")
