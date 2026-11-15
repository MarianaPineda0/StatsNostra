#!/usr/bin/env bash
# Mejora de la ronda 1: alerta de Cloud Logging sobre Services expuestos.
# La política avisa a un tema de Pub/Sub, de donde el experimento lee la hora real de la alerta
# para medir el MTTD sin depender de un correo.
#
# Uso: seguridad/mejoras/alerta.sh crear|quitar|estado
set -euo pipefail
cd "$(dirname "$0")/../.."

PROYECTO=project-3f57bb8c-371e-4b9c-949
NUMERO=599897195726
TEMA=alertas-caos
SUSCRIPCION=alertas-caos-sub
CANAL="StatsNostra: alertas del experimento de seguridad"
# regla -> nombre de la política (las reglas están en seguridad/deteccion/reglas.py)
declare -A POLITICAS=(
  [service-expuesto]="StatsNostra: Service expuesto en GKE"
  [credencial-senuelo]="StatsNostra: credencial señuelo leída"
)
API="https://monitoring.googleapis.com/v3"
SERVICEUSAGE="https://serviceusage.googleapis.com/v1beta1"
TMP="${TMPDIR:-/tmp}/politica-alerta.json"

export USE_GKE_GCLOUD_AUTH_PLUGIN=True
export GODEBUG="${GODEBUG:-http2client=0}"
llamar() { curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json" "$@"; }

# Nombre del recurso de Monitoring con ese displayName. $1: notificationChannels o alertPolicies
nombre_de() {
  llamar "$API/projects/$PROYECTO/$1" | python -c "
import json, sys
for r in json.load(sys.stdin).get(sys.argv[1], []):
    if r.get('displayName') == sys.argv[2]:
        print(r['name'])
" "$1" "$2"
}

crear() {
  gcloud pubsub topics describe "$TEMA" --project="$PROYECTO" >/dev/null 2>&1 \
    || gcloud pubsub topics create "$TEMA" --project="$PROYECTO" >/dev/null
  gcloud pubsub subscriptions describe "$SUSCRIPCION" --project="$PROYECTO" >/dev/null 2>&1 \
    || gcloud pubsub subscriptions create "$SUSCRIPCION" --topic="$TEMA" --project="$PROYECTO" >/dev/null
  # La cuenta que publica las notificaciones no existe hasta que se genera su identidad
  curl -s -X POST "$SERVICEUSAGE/projects/$PROYECTO/services/monitoring.googleapis.com:generateServiceIdentity" \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json" \
    -d '{}' >/dev/null
  gcloud pubsub topics add-iam-policy-binding "$TEMA" --project="$PROYECTO" \
    --member="serviceAccount:service-$NUMERO@gcp-sa-monitoring-notification.iam.gserviceaccount.com" \
    --role=roles/pubsub.publisher >/dev/null

  local canal politica
  canal=$(nombre_de notificationChannels "$CANAL")
  if [ -z "$canal" ]; then
    canal=$(llamar -X POST "$API/projects/$PROYECTO/notificationChannels" -d "{\"type\": \"pubsub\", \"displayName\": \"$CANAL\", \"labels\": {\"topic\": \"projects/$PROYECTO/topics/$TEMA\"}}" \
      | python -c "import json,sys; print(json.load(sys.stdin)['name'])")
  fi
  local regla
  for regla in "${!POLITICAS[@]}"; do
    politica=$(nombre_de alertPolicies "${POLITICAS[$regla]}")
    if [ -z "$politica" ]; then
      python seguridad/mejoras/politica_alerta.py "$regla" "$canal" "${POLITICAS[$regla]}" > "$TMP"
      llamar -X POST "$API/projects/$PROYECTO/alertPolicies" -d @"$TMP"         | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('name') or d)"
    fi
  done
  echo "alerta lista: tema $TEMA, canal y política creados"
}

quitar() {
  local politica canal
  local regla
  for regla in "${!POLITICAS[@]}"; do
    politica=$(nombre_de alertPolicies "${POLITICAS[$regla]}")
    if [ -n "$politica" ]; then llamar -X DELETE "$API/$politica" >/dev/null; fi
  done
  canal=$(nombre_de notificationChannels "$CANAL")
  if [ -n "$canal" ]; then llamar -X DELETE "$API/$canal?force=true" >/dev/null; fi
  gcloud pubsub subscriptions delete "$SUSCRIPCION" --project="$PROYECTO" --quiet 2>/dev/null || true
  gcloud pubsub topics delete "$TEMA" --project="$PROYECTO" --quiet 2>/dev/null || true
  echo "alerta quitada"
}

case "${1:-}" in
  crear) crear ;;
  quitar) quitar ;;
  estado)
    for regla in "${!POLITICAS[@]}"; do
      echo "política $regla: $(nombre_de alertPolicies "${POLITICAS[$regla]}")"
    done
    echo "canal: $(nombre_de notificationChannels "$CANAL")"
    gcloud pubsub topics list --project="$PROYECTO" --format='value(name)' | grep "$TEMA" || true
    ;;
  *)
    sed -n '2,/^set -euo/{/^#/p}' "$0" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
