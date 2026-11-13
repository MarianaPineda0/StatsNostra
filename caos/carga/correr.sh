#!/usr/bin/env bash
# Corre el perfil de carga fijo con k6 (en Docker, sin instalar nada) y guarda la
# evidencia de la corrida: el resumen de k6 y la hora de inicio y fin en UTC, para
# cruzarla con los logs y con el tablero.
#
# Uso: caos/carga/correr.sh CARPETA NUMERO
#   CARPETA  donde se guarda la evidencia (p. ej. caos/evidencia/estado-estable)
#   NUMERO   número de la corrida (1, 2, 3...)
# Variables: BASE_URL, TRADE_ID, PERFIL (script de k6), P95_MAX_MS (umbral de p95) y
# FORZAR=1 para saltar la guarda.
set -euo pipefail
cd "$(dirname "$0")/../.."

CARPETA="${1:?Falta la carpeta de evidencia}"
NUMERO="${2:?Falta el número de corrida}"
BASE_URL="${BASE_URL:-https://api-coordinador.jollybeach-fbb8b9ad.eastus.azurecontainerapps.io}"
TRADE_ID="${TRADE_ID:-5540}"
PERFIL="${PERFIL:-caos/carga/perfil.js}"

mkdir -p "$CARPETA"

# Si alguien más está mandando carga, esta corrida no mediría solo lo que se quiere
# medir. Se mira el tráfico que acaba de llegar a la API; sin kubectl no se puede.
if [ "${FORZAR:-0}" != 1 ] && command -v kubectl >/dev/null 2>&1; then
  recientes="$(bash caos/acciones/cpu.sh trafico | grep -o '[0-9]*$')"
  if [ "${recientes:-0}" -gt 0 ]; then
    echo "No se corre: llegaron $recientes peticiones en los últimos 45 s (¿hay otra medición en curso?)." >&2
    echo "Coordina la ventana con el grupo, o repite con FORZAR=1 si es a propósito." >&2
    exit 3
  fi
fi

# Docker en Windows necesita la ruta de Windows para montar la carpeta
destino="$(cd "$CARPETA" && (pwd -W 2>/dev/null || pwd))"
inicio="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Corrida $NUMERO contra $BASE_URL (trade $TRADE_ID), inicio $inicio"

codigo=0
MSYS_NO_PATHCONV=1 docker run --rm -i \
  -e BASE_URL="$BASE_URL" -e TRADE_ID="$TRADE_ID" -e P95_MAX_MS="${P95_MAX_MS:-}" \
  -v "$destino:/salida" \
  grafana/k6 run \
  --summary-trend-stats="avg,min,med,max,p(90),p(95),p(99)" \
  --summary-export="/salida/corrida-$NUMERO.json" - < "$PERFIL" || codigo=$?

fin="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# Un resumen que no cumple los umbrales también es evidencia: se guarda y se
# informa el código de salida de k6 (99 = umbrales no cumplidos)
printf '{"corrida": %s, "inicio_utc": "%s", "fin_utc": "%s", "codigo_k6": %s, "base_url": "%s", "trade_id": "%s"}\n' \
  "$NUMERO" "$inicio" "$fin" "$codigo" "$BASE_URL" "$TRADE_ID" > "$CARPETA/corrida-$NUMERO.meta.json"
echo "Fin $fin, código de k6: $codigo"
exit "$codigo"
