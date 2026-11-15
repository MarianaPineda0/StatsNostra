#!/usr/bin/env bash
# Tendencia: identidades de máquina con mínimo privilegio.
# Inventaría las cuentas de servicio del proyecto, prueba que la cuenta del despliegue (la que usa
# GitHub Actions) sigue pudiendo hacer lo que el despliegue de la v5 necesita, y le quita los roles
# que sobran. La prueba se hace suplantando a la cuenta, así que no hace falta lanzar el despliegue.
#
# Uso: seguridad/tendencias/minimo_privilegio.sh COMANDO
#   inventario ARCHIVO   escribe un JSON con las cuentas, sus llaves y sus roles
#   probar               prueba con la identidad del despliegue cada operación que necesita
#   aplicar              deja a la cuenta del despliegue solo con los roles necesarios
#   restaurar            devuelve los roles que tenía antes (seguridad/evidencia/identidades/antes.json)
set -euo pipefail
cd "$(dirname "$0")/../.."

P=project-3f57bb8c-371e-4b9c-949
CI="statsnostra-ci@$P.iam.gserviceaccount.com"
CLUSTER=statsnostra-v5-gke
ZONA=us-central1-a
SECRETO=statsnostra-v5-database-url
SALIDA=seguridad/evidencia/identidades

export USE_GKE_GCLOUD_AUTH_PLUGIN=True
export GODEBUG="${GODEBUG:-http2client=0}"

# Roles que necesita el despliegue de la v5 (scripts/desplegar-gke.sh y desplegar-gke.yml)
NECESARIOS=(
  roles/artifactregistry.writer     # docker push de la imagen
  roles/container.admin             # kubectl apply: namespace, secret, configmap, job, deployment, service, hpa
  roles/cloudsql.viewer             # gcloud sql instances list (nombre de la conexión)
  roles/compute.viewer              # gcloud compute addresses describe (IP reservada)
  roles/serviceusage.serviceUsageConsumer
  roles/logging.logWriter
  roles/monitoring.viewer
)

roles_actuales() {
  gcloud projects get-iam-policy "$P" --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:$CI" --format="value(bindings.role)" | tr -d '\r' | sort
}

inventario() {
  python - "$1" <<'PY'
import json, shutil, subprocess, sys

P = "project-3f57bb8c-371e-4b9c-949"


def gcloud(*args):
    return subprocess.run([shutil.which("gcloud"), *args], capture_output=True, text=True, check=True).stdout


cuentas = json.loads(gcloud("iam", "service-accounts", "list", "--project", P, "--format=json"))
politica = json.loads(gcloud("projects", "get-iam-policy", P, "--format=json"))
resultado = []
for c in cuentas:
    correo = c["email"]
    llaves = json.loads(
        gcloud("iam", "service-accounts", "keys", "list", "--iam-account", correo,
               "--managed-by=user", "--format=json")
    )
    roles = sorted(
        b["role"] for b in politica["bindings"] if f"serviceAccount:{correo}" in b.get("members", [])
    )
    resultado.append({"cuenta": correo, "llaves_de_usuario": len(llaves), "roles": roles,
                      "roles_admin": [r for r in roles if r.endswith("Admin") or r.endswith(".admin") or r == "roles/editor" or r == "roles/owner"]})
json.dump(resultado, open(sys.argv[1], "w", encoding="utf-8"), indent=2, ensure_ascii=False)
for r in resultado:
    print(f"{r['cuenta'].split('@')[0]}: {len(r['roles'])} roles, {len(r['roles_admin'])} de administración, {r['llaves_de_usuario']} llaves")
PY
}

probar() {
  local token endpoint ca fallos=0
  token=$(gcloud auth print-access-token --impersonate-service-account="$CI" 2>/dev/null)
  ok() { echo "  ok    $1"; }
  mal() { echo "  FALLA $1"; fallos=$((fallos + 1)); }

  CLOUDSDK_AUTH_ACCESS_TOKEN="$token" gcloud sql instances list --project="$P" --format='value(name)' >/dev/null 2>&1 \
    && ok "listar instancias de Cloud SQL" || mal "listar instancias de Cloud SQL"
  CLOUDSDK_AUTH_ACCESS_TOKEN="$token" gcloud compute addresses describe statsnostra-v5-ip --region=us-central1 --project="$P" >/dev/null 2>&1 \
    && ok "leer la IP reservada" || mal "leer la IP reservada"
  CLOUDSDK_AUTH_ACCESS_TOKEN="$token" gcloud secrets versions access latest --secret="$SECRETO" --project="$P" >/dev/null 2>&1 \
    && ok "leer la URL de la base en Secret Manager" || mal "leer la URL de la base en Secret Manager"
  CLOUDSDK_AUTH_ACCESS_TOKEN="$token" gcloud artifacts repositories describe statsnostra-v5-repo --location=us-central1 --project="$P" >/dev/null 2>&1 \
    && ok "ver el repositorio de imágenes" || mal "ver el repositorio de imágenes"
  CLOUDSDK_AUTH_ACCESS_TOKEN="$token" gcloud container clusters get-credentials "$CLUSTER" --zone="$ZONA" --project="$P" >/dev/null 2>&1 \
    && ok "obtener credenciales del clúster" || mal "obtener credenciales del clúster"

  endpoint=$(gcloud container clusters describe "$CLUSTER" --zone="$ZONA" --project="$P" --format='value(endpoint)')
  ca=$(mktemp)
  gcloud container clusters describe "$CLUSTER" --zone="$ZONA" --project="$P" --format='value(masterAuth.clusterCaCertificate)' | tr -d '[:space:]' | base64 -d > "$ca"
  for verbo in "create namespaces" "patch namespaces" "create secrets -n statsnostra" "patch secrets -n statsnostra" \
      "patch configmaps -n statsnostra" "create jobs -n statsnostra" "delete jobs -n statsnostra" \
      "patch deployments -n statsnostra" "patch services -n statsnostra" "create horizontalpodautoscalers.autoscaling -n statsnostra" \
      "get pods/log -n statsnostra"; do
    r=$(kubectl --server="https://$endpoint" --certificate-authority="$ca" --token="$token" auth can-i $verbo 2>/dev/null || true)
    [ "$r" = yes ] && ok "kubectl puede $verbo" || mal "kubectl puede $verbo ($r)"
  done
  rm -f "$ca"
  echo "fallos: $fallos"
  return "$fallos"
}

aplicar() {
  mkdir -p "$SALIDA"
  [ -f "$SALIDA/antes.json" ] || inventario "$SALIDA/antes.json" >/dev/null
  # Primero se agregan los que faltan y después se quitan los que sobran: nunca queda sin permisos
  local actuales rol
  actuales=$(roles_actuales)
  for rol in "${NECESARIOS[@]%% *}"; do
    echo "$actuales" | grep -qx "$rol" \
      || gcloud projects add-iam-policy-binding "$P" --member="serviceAccount:$CI" --role="$rol" --condition=None --quiet >/dev/null
  done
  for rol in $actuales; do
    printf '%s\n' "${NECESARIOS[@]%% *}" | grep -qx "$rol" \
      || gcloud projects remove-iam-policy-binding "$P" --member="serviceAccount:$CI" --role="$rol" --condition=None --quiet >/dev/null
  done
  # La URL de la base se lee de un solo secreto: el permiso va sobre ese secreto, no sobre el proyecto
  gcloud secrets add-iam-policy-binding "$SECRETO" --project="$P" --member="serviceAccount:$CI" \n    --role=roles/secretmanager.secretAccessor --quiet >/dev/null
  roles_actuales
}

restaurar() {
  python - <<'PY' | while read -r rol; do
import json
for c in json.load(open("seguridad/evidencia/identidades/antes.json", encoding="utf-8")):
    if c["cuenta"].startswith("statsnostra-ci@"):
        print("\n".join(c["roles"]))
PY
    gcloud projects add-iam-policy-binding "$P" --member="serviceAccount:$CI" --role="$rol" --condition=None --quiet >/dev/null
  done
  roles_actuales
}

case "${1:-}" in
  inventario) inventario "${2:?Falta el archivo de salida}" ;;
  probar) probar ;;
  aplicar) aplicar ;;
  restaurar) restaurar ;;
  *)
    sed -n '2,/^set -euo/{/^#/p}' "$0" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
