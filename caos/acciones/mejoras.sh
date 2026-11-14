#!/usr/bin/env bash
# Aplica o revierte las mejoras de la ronda 1 del experimento de agotamiento de CPU.
#
# Uso: caos/acciones/mejoras.sh COMANDO
#   aplicar     recursos y sonda nuevos, READINESS_LAG_MS=50 y el HPA (reinicia los pods;
#               se niega si hay tráfico reciente, FORZAR=1 lo salta)
#   revertir    vuelve a los valores de la ronda 0 y quita el HPA (reinicia los pods)
#   estado      muestra recursos, sonda, umbral y HPA vigentes
#   probar      valida todo contra el API del clúster sin cambiar nada
set -euo pipefail
cd "$(dirname "$0")/../.."

NS="${NAMESPACE:-statsnostra}"
DEPLOY="statsnostra-api"
CONFIGMAP="statsnostra-config"
UMBRAL_LAG_MS=50

export USE_GKE_GCLOUD_AUTH_PLUGIN=True
export GODEBUG="${GODEBUG:-http2client=0}"

parchar_lag() {
  kubectl patch configmap "$CONFIGMAP" -n "$NS" --type merge \
    -p "{\"data\":{\"READINESS_LAG_MS\":\"$1\"}}" "${@:2}"
}

# Reiniciar pods mientras otro grupo mide con k6 tira sus resultados
exigir_sin_trafico() {
  [ "${FORZAR:-0}" = 1 ] && return 0
  local recientes
  recientes="$(bash caos/acciones/cpu.sh trafico | grep -o '[0-9]*$')"
  if [ "${recientes:-0}" -gt 0 ]; then
    echo "No se aplica: llegaron $recientes peticiones en los últimos 45 s (¿hay una medición en curso?)." >&2
    echo "Coordina la ventana con el grupo, o repite con FORZAR=1 si es a propósito." >&2
    exit 3
  fi
}

esperar_pods() {
  kubectl rollout status "deployment/$DEPLOY" -n "$NS" --timeout=300s
}

case "${1:-}" in
  aplicar)
    exigir_sin_trafico
    # Primero el ConfigMap y después el Deployment: el cambio del Deployment es el que
    # reinicia los pods, y así arrancan ya con el umbral nuevo
    parchar_lag "$UMBRAL_LAG_MS" >/dev/null
    kubectl patch deployment "$DEPLOY" -n "$NS" --patch-file k8s/mejoras/recursos-y-sondas.yaml >/dev/null
    kubectl apply -n "$NS" -f k8s/hpa.yaml >/dev/null
    esperar_pods
    echo "Mejoras aplicadas."
    ;;
  revertir)
    exigir_sin_trafico
    kubectl delete hpa statsnostra-api-hpa -n "$NS" --ignore-not-found >/dev/null
    parchar_lag 0 >/dev/null
    kubectl patch deployment "$DEPLOY" -n "$NS" --patch-file k8s/mejoras/recursos-y-sondas-base.yaml >/dev/null
    esperar_pods
    echo "Valores de la ronda 0 restaurados."
    ;;
  estado)
    kubectl get deployment "$DEPLOY" -n "$NS" -o jsonpath='{range .spec.template.spec.containers[?(@.name=="api")]}requests={.resources.requests.cpu} limite={.resources.limits.cpu} sonda: cada {.readinessProbe.periodSeconds}s, {.readinessProbe.failureThreshold} fallos{"\n"}{end}'
    echo "READINESS_LAG_MS=$(kubectl get configmap "$CONFIGMAP" -n "$NS" -o jsonpath='{.data.READINESS_LAG_MS}')"
    kubectl get hpa -n "$NS" 2>/dev/null || true
    ;;
  probar)
    parchar_lag "$UMBRAL_LAG_MS" --dry-run=server
    kubectl patch deployment "$DEPLOY" -n "$NS" --patch-file k8s/mejoras/recursos-y-sondas.yaml --dry-run=server
    kubectl patch deployment "$DEPLOY" -n "$NS" --patch-file k8s/mejoras/recursos-y-sondas-base.yaml --dry-run=server
    kubectl apply -n "$NS" -f k8s/hpa.yaml --dry-run=server
    ;;
  *)
    sed -n '2,/^set -euo/{/^#/p}' "$0" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
