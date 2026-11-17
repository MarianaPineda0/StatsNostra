#!/usr/bin/env bash
# Baja de Cloud Logging las peticiones de una ventana (un registro por llamada que
# recibió el API) y las deja como CSV para agregar_logs.py.
#
# Uso: caos/tablero/exportar_logs.sh DESDE HASTA SALIDA.csv
#   p. ej. caos/tablero/exportar_logs.sh 2026-11-14T17:53:30Z 2026-11-14T17:58:30Z ronda0.csv
set -euo pipefail
export USE_GKE_GCLOUD_AUTH_PLUGIN=True GODEBUG="${GODEBUG:-http2client=0}"
gcloud logging read "resource.type=\"k8s_container\" AND resource.labels.namespace_name=\"statsnostra\" AND resource.labels.container_name=\"api\" AND jsonPayload.message=\"peticion\" AND timestamp>=\"$1\" AND timestamp<=\"$2\"" \
  --limit=30000 \
  --format='csv[no-heading](jsonPayload.timestamp,resource.labels.pod_name,jsonPayload.ruta,jsonPayload.status,jsonPayload.ms,jsonPayload.traceId)' > "$3"
echo "$(wc -l < "$3") registros en $3"
