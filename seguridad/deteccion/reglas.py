"""Reglas de detección de StatsNostra como código.

Cada regla se define una sola vez y sirve para dos cosas: armar el filtro que se pega en
Cloud Logging (y en la alerta) y evaluarlo contra los casos de prueba de casos/, sin tocar la
nube. Así el filtro que se prueba es el mismo que se despliega.

- Service expuesto: la creación de un Service NodePort o LoadBalancer en el clúster, fuera del
  Service público de la API. Es la ruta no declarada del experimento de exposición y
  segmentación (ATT&CK T1190, Exploit Public-Facing Application).
- Credencial señuelo: cualquier lectura del secreto que no usa nadie. Si alguien lo abre, es
  que está buscando credenciales (ATT&CK T1552, Unsecured Credentials).
"""

from dataclasses import dataclass, field

CLUSTER = "statsnostra-v5-gke"
SERVICE_LEGITIMO = "statsnostra-api-service"
TIPOS_EXPUESTOS = ("NodePort", "LoadBalancer")
SECRETO_SENUELO = "statsnostra-admin-respaldo"


@dataclass(frozen=True)
class Regla:
    nombre: str
    registro: str  # log_id de Cloud Audit Logs: activity o data_access
    igualdad: list = field(default_factory=list)  # (campo, valor o valores admitidos)
    contiene: list = field(default_factory=list)  # (campo, fragmento que debe aparecer)
    excluir_recurso: str = ""  # fragmento de protoPayload.resourceName que se descarta

    def filtro(self) -> str:
        """El filtro de Cloud Logging que implementa la regla."""
        partes = [f'log_id("cloudaudit.googleapis.com/{self.registro}")']
        for campo, valor in self.igualdad:
            if isinstance(valor, tuple):
                opciones = " OR ".join(f'"{v}"' for v in valor)
                partes.append(f"{campo}=({opciones})")
            else:
                partes.append(f'{campo}="{valor}"')
        for campo, fragmento in self.contiene:
            partes.append(f'{campo}:"{fragmento}"')
        if self.excluir_recurso:
            partes.append(f'NOT protoPayload.resourceName:"{self.excluir_recurso}"')
        return "\n".join(partes)

    def coincide(self, entrada: dict) -> bool:
        """Evalúa la regla sobre una entrada de log, con la misma lógica que el filtro."""
        if not str(entrada.get("logName", "")).endswith(
            f"cloudaudit.googleapis.com%2F{self.registro}"
        ):
            return False
        for campo, valor in self.igualdad:
            admitidos = valor if isinstance(valor, tuple) else (valor,)
            if _valor(entrada, campo) not in admitidos:
                return False
        for campo, fragmento in self.contiene:
            if fragmento not in str(_valor(entrada, campo) or ""):
                return False
        recurso = _valor(entrada, "protoPayload.resourceName") or ""
        return not (self.excluir_recurso and self.excluir_recurso in recurso)


def _valor(entrada: dict, campo: str):
    actual = entrada
    for clave in campo.split("."):
        if not isinstance(actual, dict) or clave not in actual:
            return None
        actual = actual[clave]
    return actual


SERVICE_EXPUESTO = Regla(
    nombre="service-expuesto",
    registro="activity",
    igualdad=[
        ("resource.type", "k8s_cluster"),
        ("resource.labels.cluster_name", CLUSTER),
        ("protoPayload.methodName", "io.k8s.core.v1.services.create"),
        ("protoPayload.request.spec.type", TIPOS_EXPUESTOS),
    ],
    excluir_recurso=f"/services/{SERVICE_LEGITIMO}",
)

CREDENCIAL_SENUELO = Regla(
    nombre="credencial-senuelo",
    registro="data_access",
    igualdad=[
        ("resource.type", "audited_resource"),
        ("protoPayload.serviceName", "secretmanager.googleapis.com"),
        (
            "protoPayload.methodName",
            "google.cloud.secretmanager.v1.SecretManagerService.AccessSecretVersion",
        ),
    ],
    contiene=[("protoPayload.resourceName", f"/secrets/{SECRETO_SENUELO}/")],
)

REGLAS = {r.nombre: r for r in (SERVICE_EXPUESTO, CREDENCIAL_SENUELO)}

# Atajos de la primera regla, que es la que usan el script del experimento y sus pruebas
filtro = SERVICE_EXPUESTO.filtro
coincide = SERVICE_EXPUESTO.coincide


if __name__ == "__main__":
    import sys

    print(REGLAS[sys.argv[1] if len(sys.argv) > 1 else "service-expuesto"].filtro())
