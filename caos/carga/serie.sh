#!/usr/bin/env bash
# Serie de corridas del perfil fijo con su evidencia: la instantánea del entorno,
# el consumo de cada pod cada 15 s, las corridas de k6 y el resumen. Es el mismo
# protocolo para el estado estable y para las rondas 0 y 1, así se comparan en
# igualdad de condiciones.
#
# Uso: caos/carga/serie.sh CARPETA [CORRIDAS=3] [PAUSA_S=60]
set -uo pipefail
cd "$(dirname "$0")/../.."

CARPETA="${1:?Falta la carpeta de evidencia}"
CORRIDAS="${2:-3}"
PAUSA="${3:-60}"
mkdir -p "$CARPETA"

export USE_GKE_GCLOUD_AUTH_PLUGIN=True
export GODEBUG="${GODEBUG:-http2client=0}"

# Entorno: lo que permite afirmar después que fueron "los mismos recursos"
{
  echo "# instantánea $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  kubectl get deployment statsnostra-api -n statsnostra \
    -o jsonpath='imagen={.spec.template.spec.containers[0].image}{"\n"}réplicas={.status.readyReplicas}/{.spec.replicas}{"\n"}'
  kubectl get deployment statsnostra-api -n statsnostra \
    -o jsonpath='requests={.spec.template.spec.containers[0].resources.requests}{"\n"}limits={.spec.template.spec.containers[0].resources.limits}{"\n"}'
  kubectl get configmap statsnostra-config -n statsnostra \
    -o jsonpath='FAULT_HEADER_ENABLED={.data.FAULT_HEADER_ENABLED}{"\n"}READINESS_LAG_MS={.data.READINESS_LAG_MS}{"\n"}APP_VERSION={.data.APP_VERSION}{"\n"}'
  echo "hpa=$(kubectl get hpa -n statsnostra --no-headers 2>/dev/null | wc -l)"
  kubectl get pods -n statsnostra -o wide --no-headers | grep -v migracion
} > "$CARPETA/entorno.txt" 2>&1

# Si el sistema no está en su estado base, la serie no mide lo que dice medir
if ! grep -q 'réplicas=2/2' "$CARPETA/entorno.txt" || ! grep -q 'FAULT_HEADER_ENABLED=false' "$CARPETA/entorno.txt"; then
  echo "El entorno no está en su estado base (ver $CARPETA/entorno.txt); no se corre nada." >&2
  exit 4
fi

# Consumo de cada pod durante toda la serie, para el diagnóstico
muestrear() {
  while true; do
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(kubectl top pods -n statsnostra --no-headers 2>/dev/null | awk '{printf "%s=%s ", $1, $2}')" >> "$CARPETA/cpu-pods.txt"
    sleep 15
  done
}
muestrear &
MUESTREO=$!
trap 'kill "$MUESTREO" 2>/dev/null' EXIT

for n in $(seq 1 "$CORRIDAS"); do
  bash caos/carga/correr.sh "$CARPETA" "$n"
  codigo=$?
  # 3 es la guarda: esa corrida no se hizo y seguir daría una serie inválida.
  # Cualquier otro código (como 99, umbrales no cumplidos) sí deja evidencia.
  if [ "$codigo" = 3 ]; then
    echo "Corrida $n rechazada por la guarda; se detiene la serie." >&2
    exit 3
  fi
  if [ "$n" -lt "$CORRIDAS" ]; then sleep "$PAUSA"; fi
done

python caos/carga/resumen.py "$CARPETA"
