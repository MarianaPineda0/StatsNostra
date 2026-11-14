"""Convierte informe-caos-mari.html en PDF (informe-caos-mari.pdf) con PyMuPDF.

Uso: python caos/informe/generar_pdf.py    (imprime el número de páginas)
Las imágenes del informe (arquitectura.png y tablero.png) se leen de esta carpeta.
"""
from pathlib import Path

import pymupdf

AQUI = Path(__file__).resolve().parent
html = (AQUI / "informe-caos-mari.html").read_text(encoding="utf-8")
historia = pymupdf.Story(html=html, archive=pymupdf.Archive(str(AQUI)))
escritor = pymupdf.DocumentWriter(str(AQUI / "informe-caos-mari.pdf"))
pagina = pymupdf.paper_rect("a4")
zona = pagina + (40, 36, -40, -36)

hay_mas = True
while hay_mas:
    dispositivo = escritor.begin_page(pagina)
    hay_mas, _ = historia.place(zona)
    historia.draw(dispositivo)
    escritor.end_page()
escritor.close()
print("páginas:", pymupdf.open(str(AQUI / "informe-caos-mari.pdf")).page_count)
