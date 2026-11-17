"""Genera el objeto sintético de StatsNostra para el experimento 4 (resiliencia de los datos).

El objeto es una predicción con la forma real de la API (PrediccionRespuesta) y datos
inventados. Junto al archivo se escribe <nombre>.sha256 en el formato de sha256sum
("hash  nombre"), y el hash se calcula sobre los bytes del archivo tal cual: UTF-8, saltos
de línea LF y una línea final. Para que Git no los cambie, seguridad/datos/objetos/ se marca
como binario en .gitattributes.

Uso:
    python seguridad/datos/generar_objeto.py            escribe el objeto y su .sha256
    python seguridad/datos/generar_objeto.py verificar  comprueba el archivo contra su hash
"""

import hashlib
import json
import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "objetos" / "statsnostra"
NOMBRE = "statsnostra-prediccion.json"

OBJETO = {
    "api": "statsnostra",
    "tipo": "prediccion",
    "sintetico": True,
    "id": 9001,
    "apostador_id": 9007,
    "partido_id": 9012,
    "goles_local_pred": 2,
    "goles_visitante_pred": 1,
    "fecha_prediccion": "2026-11-16T15:00:00Z",
    "acertada": None,
    "puntos": None,
}


def contenido() -> bytes:
    """Los bytes exactos del objeto: JSON con sangría de 2, UTF-8, LF y una línea final."""
    return (json.dumps(OBJETO, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def escribir() -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    datos = contenido()
    (CARPETA / NOMBRE).write_bytes(datos)
    (CARPETA / f"{NOMBRE}.sha256").write_bytes(f"{sha256(datos)}  {NOMBRE}\n".encode())
    print(f"{NOMBRE}: {len(datos)} bytes, sha256 {sha256(datos)}")


def verificar() -> int:
    datos = (CARPETA / NOMBRE).read_bytes()
    esperado = (CARPETA / f"{NOMBRE}.sha256").read_text(encoding="utf-8").split()[0]
    real = sha256(datos)
    print("coincide" if real == esperado else f"NO coincide: {real} frente a {esperado}")
    return 0 if real == esperado else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verificar":
        raise SystemExit(verificar())
    escribir()
