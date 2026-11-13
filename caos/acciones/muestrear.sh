#!/usr/bin/env bash
# Muestrea los pods durante una ronda para poder diagnosticar después qué pasó:
#   cpu-pods.txt   consumo de CPU y memoria de cada pod, cada 15 s (kubectl top)
#   lag-pods.csv   retraso del bucle de eventos de cada pod, cada 5 s (/metrics)
# El retraso es la señal que usa la readiness por saturación, así que esta serie
# es la que permite elegir su umbral con datos medidos.
#
# Uso: caos/acciones/muestrear.sh CARPETA [SEGUNDOS=240]
# Hay que lanzarlo DESPUÉS de encender el interruptor: ese paso reinicia los pods y
# cambia sus nombres.
set -uo pipefail

CARPETA="${1:?Falta la carpeta de evidencia}"
SEGUNDOS="${2:-240}"
NS="${NAMESPACE:-statsnostra}"
PUERTO_BASE=19000

export USE_GKE_GCLOUD_AUTH_PLUGIN=True
export GODEBUG="${GODEBUG:-http2client=0}"
mkdir -p "$CARPETA"

pods=($(kubectl get pods -n "$NS" -l app=statsnostra-api -o jsonpath='{.items[*].metadata.name}'))
echo "timestamp_utc,pod,lag_ms" > "$CARPETA/lag-pods.csv"

# Un túnel por pod abierto durante todo el muestreo. Se consulta /metrics (que el
# interruptor de fallos no toca) y no se ejecuta nada dentro del pod, para no
# sumar carga al que se está saturando.
tuneles=()
for i in "${!pods[@]}"; do
  kubectl port-forward -n "$NS" "pod/${pods[$i]}" "$((PUERTO_BASE + i)):8000" >/dev/null 2>&1 &
  tuneles+=($!)
done
trap 'kill "${tuneles[@]}" 2>/dev/null' EXIT
sleep 3

fin=$((SECONDS + SEGUNDOS))
ciclo=0
while [ "$SECONDS" -lt "$fin" ]; do
  ahora="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  for i in "${!pods[@]}"; do
    lag="$(curl -s -m 3 "http://127.0.0.1:$((PUERTO_BASE + i))/metrics" \
      | awk '/^statsnostra_event_loop_lag_ms /{print $2}')"
    # Si el pod no contesta a tiempo se anota NA: también es un dato
    echo "$ahora,${pods[$i]},${lag:-NA}" >> "$CARPETA/lag-pods.csv"
  done
  if [ $((ciclo % 3)) = 0 ]; then
    echo "$ahora $(kubectl top pods -n "$NS" --no-headers 2>/dev/null | awk '{printf "%s=%s ", $1, $2}')" \
      >> "$CARPETA/cpu-pods.txt"
  fi
  ciclo=$((ciclo + 1))
  sleep 5
done
