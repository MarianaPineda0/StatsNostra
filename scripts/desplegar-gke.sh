#!/usr/bin/env bash
# Despliega el API en el clúster GKE de la v5: construye y sube la imagen,
# migra la base y actualiza los manifiestos. Lo usan igual quien despliega a
# mano y el workflow de GitHub Actions, para que haya una sola forma de hacerlo.
#
# Uso:   scripts/desplegar-gke.sh [etiqueta-de-la-imagen]
# Antes: gcloud auth login (o la autenticación del workflow), docker y kubectl.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-3f57bb8c-371e-4b9c-949}"
REGION="${REGION:-us-central1}"
ZONA="${ZONA:-us-central1-a}"
CLUSTER="${CLUSTER:-statsnostra-v5-gke}"
NAMESPACE="statsnostra"
REPOSITORIO="${REGION}-docker.pkg.dev/${PROJECT_ID}/statsnostra-v5-repo/statsnostra-api"

# Versión que el API devuelve en X-App-Version
export APP_VERSION="${APP_VERSION:-5.0.0}"
ETIQUETA="${1:-$(git rev-parse --short HEAD)}"
export IMAGE="${REPOSITORIO}:${ETIQUETA}"

export USE_GKE_GCLOUD_AUTH_PLUGIN=True
# La conexión HTTP/2 se corta a ratos al hablar con las APIs de Google desde
# algunas redes; HTTP/1.1 evita esos cortes
export GODEBUG="${GODEBUG:-http2client=0}"

paso() { printf '\n== %s\n' "$1"; }

paso "Imagen ${IMAGE}"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >/dev/null 2>&1
docker build -t "${IMAGE}" .
docker push "${IMAGE}"

paso "Conexión al clúster ${CLUSTER}"
gcloud container clusters get-credentials "${CLUSTER}" --zone="${ZONA}" --project="${PROJECT_ID}"

# Los datos que cambian entre ambientes se leen de GCP y no se escriben en el
# repositorio, así el despliegue sigue valiendo si se recrea la infraestructura
export CLOUDSQL_CONNECTION_NAME
CLOUDSQL_CONNECTION_NAME="$(gcloud sql instances list --project="${PROJECT_ID}" \
  --filter='name~statsnostra-v5-db' --format='value(connectionName)')"
export LB_IP
LB_IP="$(gcloud compute addresses describe statsnostra-v5-ip --region="${REGION}" \
  --project="${PROJECT_ID}" --format='value(address)')"

paso "Namespace, secreto y configuración"
kubectl apply -f k8s/namespace.yaml

# La URL de la base lleva la contraseña: se enmascara en los logs del workflow
# y se pasa por tubería para no dejarla en un archivo
URL_BASE="$(gcloud secrets versions access latest --secret=statsnostra-v5-database-url \
  --project="${PROJECT_ID}")"
if [ -n "${GITHUB_ACTIONS:-}" ]; then echo "::add-mask::${URL_BASE}"; fi
kubectl create secret generic statsnostra-secrets --namespace "${NAMESPACE}" \
  --from-literal=DATABASE_URL="${URL_BASE}" --dry-run=client -o yaml | kubectl apply -f -
unset URL_BASE

envsubst < k8s/configmap.yaml | kubectl apply -f -

paso "Migración de la base"
# El Job tiene nombre fijo: se borra el anterior para poder crearlo de nuevo
kubectl delete job statsnostra-migracion --namespace "${NAMESPACE}" --ignore-not-found --wait=true
envsubst < k8s/migracion-job.yaml | kubectl apply -f -
if ! kubectl wait --for=condition=complete job/statsnostra-migracion \
  --namespace "${NAMESPACE}" --timeout=300s; then
  echo "La migración no terminó; esto dijo:" >&2
  kubectl logs job/statsnostra-migracion --namespace "${NAMESPACE}" --all-containers --tail=50 >&2 || true
  exit 1
fi
kubectl logs job/statsnostra-migracion --namespace "${NAMESPACE}" -c migracion --tail=5

paso "Despliegue del API"
envsubst < k8s/deployment.yaml | kubectl apply -f -
envsubst < k8s/service.yaml | kubectl apply -f -
kubectl rollout status deployment/statsnostra-api --namespace "${NAMESPACE}" --timeout=300s

paso "Listo"
kubectl get pods --namespace "${NAMESPACE}" -o wide
echo "URL del API: http://${LB_IP}  (puede tardar un par de minutos en responder la primera vez)"
