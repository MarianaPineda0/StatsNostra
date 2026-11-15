#!/usr/bin/env bash
# Tendencia: honeytoken. Un secreto señuelo que nadie usa y que avisa cuando alguien lo abre.
#
# Uso: seguridad/tendencias/honeytoken.sh probar
#   probar   caso negativo (mirar los datos del secreto, sin abrirlo) y caso positivo (abrirlo),
#            y mide cuánto tarda en llegar la alerta al tema de Pub/Sub
set -euo pipefail
cd "$(dirname "$0")/../.."

P=project-3f57bb8c-371e-4b9c-949
SECRETO=statsnostra-admin-respaldo
SUSCRIPCION=alertas-caos-sub
SALIDA=seguridad/evidencia/honeytoken
export USE_GKE_GCLOUD_AUTH_PLUGIN=True
export GODEBUG="${GODEBUG:-http2client=0}"

esperar_alerta() {  # $1 = segundos máximos; imprime la hora de publicación o nada
  local fin=$(($(date +%s) + $1)) m
  while [ "$(date +%s)" -lt "$fin" ]; do
    m=$(gcloud pubsub subscriptions pull "$SUSCRIPCION" --project="$P" --limit=1 --auto-ack \
      --format='value(message.publishTime)' 2>/dev/null || true)
    if [ -n "$m" ]; then echo "$m"; return 0; fi
    sleep 10
  done
  return 1
}

probar() {
  mkdir -p "$SALIDA"
  esperar_alerta 5 >/dev/null || true   # se vacía lo que hubiera pendiente

  # Caso negativo: leer los metadatos del secreto no es abrirlo y no debe alertar
  gcloud secrets describe "$SECRETO" --project="$P" >/dev/null
  local alerta_negativo=""
  alerta_negativo=$(esperar_alerta 150 || true)

  # Caso positivo: abrir el secreto
  local t0 t0s alerta
  t0=$(date -u +%Y-%m-%dT%H:%M:%SZ); t0s=$(date +%s)
  gcloud secrets versions access latest --secret="$SECRETO" --project="$P" >/dev/null
  alerta=$(esperar_alerta 420 || true)
  printf '{"apertura_utc": "%s", "alerta_utc": "%s", "alerta_en_caso_negativo": "%s"}\n' \
    "$t0" "${alerta:-sin_alerta}" "${alerta_negativo:-ninguna}" > "$SALIDA/resultado.json"
  echo "apertura $t0, alerta ${alerta:-sin_alerta} (${alerta_negativo:-sin alerta en el caso negativo})"
  [ -n "$alerta" ] && [ -z "$alerta_negativo" ]
}

case "${1:-}" in
  probar) probar ;;
  *)
    sed -n '2,/^set -euo/{/^#/p}' "$0" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
