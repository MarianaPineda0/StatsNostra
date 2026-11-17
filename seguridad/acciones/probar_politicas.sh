#!/usr/bin/env bash
# Pone las NetworkPolicy de la API y comprueba que los pods NUEVOS siguen pudiendo resolver
# nombres y abrir conexiones. En el experimento de exposición solo se había mirado el flujo con
# conexiones ya abiertas, y eso no basta: un pod recién creado necesita DNS, el servidor de
# metadatos, la API de Cloud SQL y la base. Si algo falla, quita las políticas y sale con error.
#
# Uso: seguridad/acciones/probar_politicas.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

NS=statsnostra
IP_PUBLICA=34.68.14.217
OTLP=otlp-gateway-prod-us-east-6.grafana.net
export USE_GKE_GCLOUD_AUTH_PLUGIN=True
export MSYS_NO_PATHCONV=1
export GODEBUG="${GODEBUG:-http2client=0}"

revertir() {
  echo "FALLÓ: $1. Quito las políticas." >&2
  kubectl delete networkpolicy --all -n "$NS" >/dev/null
  exit 1
}

pods() { kubectl get pods -n "$NS" -l app=statsnostra-api -o jsonpath='{.items[*].metadata.name}'; }

# Una sola mirada al tráfico: si hay alguien midiendo, no se toca nada
recientes="$(bash caos/acciones/cpu.sh trafico | grep -o '[0-9]*$')"
[ "${recientes:-0}" -eq 0 ] || { echo "Hay tráfico reciente ($recientes); no se prueba." >&2; exit 3; }

# Solo las políticas del namespace de la API (la del namespace de prueba es del experimento)
python - <<'PY' | kubectl apply -f -
import sys
t = open("seguridad/mejoras/networkpolicy.yaml", encoding="utf-8").read().replace("\r\n", "\n")
docs = [d for d in t.split("\n---\n")[1:] if "namespace: caos-seguridad" not in d]
sys.stdout.write("\n---\n".join(d.strip("\n") for d in docs) + "\n")
PY
sleep 10

echo "== pods ya en marcha: DNS y conexiones nuevas"
for p in $(pods); do
  kubectl exec "$p" -n "$NS" -c api -- python -c "
import socket
for host, puerto in (('sqladmin.googleapis.com', 443), ('$OTLP', 443)):
    socket.create_connection((host, puerto), 6).close()
    print('  ok', host, puerto)
" || revertir "el pod $p no resuelve o no conecta"
done

echo "== arranque en frío: borro un pod y espero a que el nuevo quede listo con las políticas puestas"
kubectl delete pod "$(pods | awk '{print $1}')" -n "$NS" >/dev/null
sleep 5
kubectl rollout status deployment/statsnostra-api -n "$NS" --timeout=240s || revertir "el pod nuevo no quedó listo"
sleep 20

echo "== la API con pods nuevos"
for i in $(seq 1 10); do
  codigo="$(curl -s -o /dev/null -m 20 -w '%{http_code}' "http://$IP_PUBLICA/api/v1/partidos" || true)"
  printf '%s ' "$codigo"
  [ "$codigo" = 200 ] || { echo; revertir "/api/v1/partidos dio $codigo"; }
done
echo
for p in $(pods); do
  fallos="$(kubectl logs "$p" -n "$NS" -c api --since=90s 2>&1 | grep -c 'Failed to export' || true)"
  echo "  $p: $fallos errores de exportación"
  [ "$fallos" = 0 ] || revertir "la exportación a Grafana falla en $p"
done
echo "OK: las políticas funcionan con pods nuevos."
