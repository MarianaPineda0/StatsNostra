"""Escribe en la salida estándar la política de alerta de Cloud Monitoring (JSON) de una regla.

El filtro sale de seguridad/deteccion/reglas.py, así que la alerta usa exactamente la regla que
se probó con los casos positivos y negativos. Lo llama alerta.sh.

Uso: python seguridad/mejoras/politica_alerta.py REGLA NOMBRE_DEL_CANAL "Nombre de la política"
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from seguridad.deteccion import reglas  # noqa: E402

TEXTOS = {
    "service-expuesto": (
        "Se creó un Service NodePort o LoadBalancer",
        "Se creó un Service expuesto en statsnostra-v5-gke. Revisar quién y por qué lo creó; "
        "si no estaba previsto, borrarlo con `kubectl delete service NOMBRE -n NAMESPACE`.",
    ),
    "credencial-senuelo": (
        "Se leyó el secreto señuelo",
        "Alguien abrió el secreto señuelo, que ninguna aplicación usa. Revisar con qué cuenta "
        "y desde dónde, y rotar las credenciales reales de esa cuenta.",
    ),
}

regla, canal, nombre = sys.argv[1], sys.argv[2], sys.argv[3]
condicion, documentacion = TEXTOS[regla]
print(
    json.dumps(
        {
            "displayName": nombre,
            "combiner": "OR",
            "enabled": True,
            "conditions": [
                {
                    "displayName": condicion,
                    "conditionMatchedLog": {"filter": reglas.REGLAS[regla].filtro()},
                }
            ],
            "alertStrategy": {"notificationRateLimit": {"period": "300s"}},
            "notificationChannels": [canal],
            "documentation": {"mimeType": "text/markdown", "content": documentacion},
        }
    )
)
