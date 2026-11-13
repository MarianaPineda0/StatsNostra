#!/usr/bin/env bash
# Acciones del experimento de agotamiento de CPU de un pod. Las usa el
# experimento (caos/experimentos/03-agotamiento.json) y se pueden correr a mano.
#
# Uso: caos/acciones/cpu.sh COMANDO [argumentos]
#   habilitar            enciende el interruptor de fallos y reinicia los pods
#   deshabilitar         lo apaga y reinicia los pods (parada de emergencia)
#   saturar [seg] [i]    satura la CPU del pod número i (0 por defecto) seg segundos
#   detener              detiene el consumo en todos los pods
#   estado               muestra el consumo de cada pod y su CPU real
set -euo pipefail

NS="${NAMESPACE:-statsnostra}"
DEPLOY="statsnostra-api"
CONFIGMAP="statsnostra-config"
PUERTO_BASE=18080

export USE_GKE_GCLOUD_AUTH_PLUGIN=True
# HTTP/1.1 evita los cortes de HTTP/2 que se ven a ratos contra las APIs de Google
export GODEBUG="${GODEBUG:-http2client=0}"

pods() { kubectl get pods -n "$NS" -l app="$DEPLOY" -o jsonpath='{.items[*].metadata.name}'; }

# Llama a un pod concreto por port-forward. El balanceador reparte entre las dos
# réplicas, y el experimento necesita saturar solo una: por eso no se pasa por él.
llamar_pod() {
  local pod="$1" metodo="$2" ruta="$3"
  shift 3
  local puerto=$((PUERTO_BASE + RANDOM % 1000))
  kubectl port-forward -n "$NS" "pod/$pod" "$puerto:8000" >/dev/null 2>&1 &
  local reenvio=$!
  local listo=0
  for _ in $(seq 1 30); do
    if curl -s -o /dev/null -m 2 "http://127.0.0.1:$puerto/health/live"; then listo=1; break; fi
    sleep 0.5
  done
  local codigo=0
  if [ "$listo" = 1 ]; then
    curl -s -m 20 -w '  [HTTP %{http_code}]\n' -X "$metodo" "$@" "http://127.0.0.1:$puerto$ruta" || codigo=$?
  else
    echo "  no se pudo abrir el túnel al pod $pod" >&2
    codigo=1
  fi
  kill "$reenvio" 2>/dev/null || true
  wait "$reenvio" 2>/dev/null || true
  return "$codigo"
}

cambiar_interruptor() {
  local valor="$1"
  kubectl patch configmap "$CONFIGMAP" -n "$NS" --type merge \
    -p "{\"data\":{\"FAULT_HEADER_ENABLED\":\"$valor\"}}" >/dev/null
  # Los pods leen la configuración al arrancar: sin reinicio no cambia nada
  kubectl rollout restart "deployment/$DEPLOY" -n "$NS" >/dev/null
  kubectl rollout status "deployment/$DEPLOY" -n "$NS" --timeout=240s
  echo "FAULT_HEADER_ENABLED=$valor"
}

case "${1:-}" in
  habilitar) cambiar_interruptor true ;;
  deshabilitar) cambiar_interruptor false ;;
  saturar)
    segundos="${2:-180}"
    indice="${3:-0}"
    lista=($(pods))
    pod="${lista[$indice]:?no existe el pod número $indice}"
    echo "Saturando la CPU del pod $pod durante ${segundos}s"
    llamar_pod "$pod" POST "/fault/cpu?segundos=$segundos" -H "X-Inject-Fault: cpu"
    ;;
  detener)
    # Se intenta en todos los pods y no se corta si uno falla: parar tiene que ser
    # lo más seguro posible
    for pod in $(pods); do
      printf '%s: ' "$pod"
      llamar_pod "$pod" DELETE /fault/cpu || echo "  (no respondió)"
    done
    ;;
  estado)
    for pod in $(pods); do
      printf '%s: ' "$pod"
      llamar_pod "$pod" GET /fault/cpu || echo "  (sin endpoint)"
    done
    kubectl top pods -n "$NS" --no-headers
    ;;
  *)
    sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
