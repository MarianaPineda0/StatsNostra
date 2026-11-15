"""Regla de detección "Service expuesto en GKE" como código.

Una sola definición sirve para dos cosas: armar el filtro que se pega en Cloud Logging (y en la
alerta) y evaluarlo contra los casos de prueba de casos/, sin tocar la nube. Así el filtro que
se prueba es el mismo que se despliega.

Qué detecta: la creación de un Service de tipo NodePort o LoadBalancer en el clúster, fuera del
Service público de la API. Es la ruta no declarada del experimento de exposición y
segmentación (ATT&CK T1190, Exploit Public-Facing Application).
"""

CLUSTER = "statsnostra-v5-gke"
SERVICE_LEGITIMO = "statsnostra-api-service"
TIPOS_EXPUESTOS = ("NodePort", "LoadBalancer")

# Condiciones que se evalúan sobre la entrada de log; (campo, valor o valores admitidos)
IGUALDAD = [
    ("resource.type", "k8s_cluster"),
    ("resource.labels.cluster_name", CLUSTER),
    ("protoPayload.methodName", "io.k8s.core.v1.services.create"),
    ("protoPayload.request.spec.type", TIPOS_EXPUESTOS),
]


def filtro() -> str:
    """El filtro de Cloud Logging que implementa la regla."""
    partes = ['log_id("cloudaudit.googleapis.com/activity")']
    for campo, valor in IGUALDAD:
        if isinstance(valor, tuple):
            partes.append(f"{campo}=({' OR '.join(chr(34) + v + chr(34) for v in valor)})")
        else:
            partes.append(f'{campo}="{valor}"')
    partes.append(f'NOT protoPayload.resourceName:"/services/{SERVICE_LEGITIMO}"')
    return "\n".join(partes)


def _valor(entrada: dict, campo: str):
    actual = entrada
    for clave in campo.split("."):
        if not isinstance(actual, dict) or clave not in actual:
            return None
        actual = actual[clave]
    return actual


def coincide(entrada: dict) -> bool:
    """Evalúa la regla sobre una entrada de log, con la misma lógica que el filtro."""
    if not str(entrada.get("logName", "")).endswith("cloudaudit.googleapis.com%2Factivity"):
        return False
    for campo, valor in IGUALDAD:
        encontrado = _valor(entrada, campo)
        admitidos = valor if isinstance(valor, tuple) else (valor,)
        if encontrado not in admitidos:
            return False
    recurso = _valor(entrada, "protoPayload.resourceName") or ""
    return f"/services/{SERVICE_LEGITIMO}" not in recurso


if __name__ == "__main__":
    print(filtro())
