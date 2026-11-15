#!/usr/bin/env bash
# Experimento 2 de seguridad: exposición y segmentación de StatsNostra en GKE.
# Solo se usa con las reglas de compromiso aceptadas (seguridad/reglas-de-compromiso.md).
#
# Uso: seguridad/acciones/exposicion.sh COMANDO [argumentos]
#   preparar          crea el namespace caos-seguridad y el pod de prueba (visitante)
#   linea-base        mide con un evento inofensivo cuánto tarda la señal en verse en los logs
#   ronda N           corre la ronda N (0 o 1): inyecta A, B y C y mide detección y contención
#   mejoras           aplica las mejoras de la ronda 1 (NetworkPolicy y alerta)
#   parar             interruptor de parada: borra todo lo que crea el experimento
#   estado            muestra lo que hay hoy en los dos namespaces
set -euo pipefail
cd "$(dirname "$0")/../.."

NS=statsnostra
NS_PRUEBA=caos-seguridad
CLUSTER=statsnostra-v5-gke
IP_PUBLICA=34.68.14.217
T1_S=300   # la hipótesis espera la alerta en 5 minutos o menos
EVIDENCIA=seguridad/evidencia

export USE_GKE_GCLOUD_AUTH_PLUGIN=True
export GODEBUG="${GODEBUG:-http2client=0}"

ahora() { date -u +%Y-%m-%dT%H:%M:%SZ; }
hora_colombia() { date -u -d '-5 hours' +%H:%M:%S; }

# Una fila en la bitácora del grupo (hora de Colombia, quién, qué, resultado)
bitacora() {
  printf '| %s | StatsNostra | %s | %s |\n' "$(hora_colombia)" "$1" "$2" >> seguridad/bitacora.md
  echo "[$(hora_colombia)] $1: $2"
}

filtro_servicio() { python seguridad/deteccion/reglas.py; }

# Segundos hasta que el evento de creación del Service se puede consultar en Cloud Logging.
# Devuelve vacío si no aparece en el tiempo dado.
esperar_log() {
  local desde="$1" limite="$2" inicio actual hallado
  inicio=$(date +%s)
  while :; do
    hallado=$(gcloud logging read "$(filtro_servicio)
timestamp>=\"$desde\"" --limit=1 --format='value(timestamp)' 2>/dev/null || true)
    actual=$(date +%s)
    if [ -n "$hallado" ]; then echo "$((actual - inicio)) $hallado"; return 0; fi
    [ $((actual - inicio)) -ge "$limite" ] && return 1
    sleep 10
  done
}

preparar() {
  kubectl get namespace "$NS_PRUEBA" >/dev/null 2>&1 || kubectl create namespace "$NS_PRUEBA"
  kubectl apply -n "$NS_PRUEBA" -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: visitante
  labels:
    app: visitante
spec:
  containers:
    - name: curl
      image: curlimages/curl:8.10.1
      command: ["sleep", "3600"]
      resources:
        requests: { cpu: "10m", memory: "16Mi" }
        limits: { cpu: "50m", memory: "32Mi" }
      securityContext:
        allowPrivilegeEscalation: false
        runAsNonRoot: true
        runAsUser: 100
        capabilities: { drop: ["ALL"] }
YAML
  kubectl wait -n "$NS_PRUEBA" --for=condition=Ready pod/visitante --timeout=120s
}

parar() {
  kubectl delete service admin-expuesto -n "$NS" --ignore-not-found
  kubectl delete service linea-base -n "$NS" --ignore-not-found
  kubectl delete networkpolicy --all -n "$NS" --ignore-not-found
  kubectl delete namespace "$NS_PRUEBA" --ignore-not-found --wait=false
}

verificar_reversion() {
  local listo
  listo=$(curl -s -o /dev/null -w '%{http_code}' "http://$IP_PUBLICA/health/ready" || true)
  echo "servicios: $(kubectl get service -n "$NS" --no-headers | awk '{print $1}' | tr '\n' ' ')"
  echo "políticas: $(kubectl get networkpolicy -n "$NS" --no-headers 2>/dev/null | wc -l)"
  echo "/health/ready por la IP pública: $listo"
  [ "$listo" = 200 ]
}

linea_base() {
  local t0 f resultado
  t0=$(ahora)
  kubectl create service clusterip linea-base --tcp=9090:9090 -n "$NS" >/dev/null
  bitacora "Línea base: creo un Service ClusterIP inofensivo (linea-base)" "creado a las $t0"
  # Con una regla sobre ClusterIP (que no es un servicio expuesto) se mediría solo la demora de
  # los registros: se busca el evento de creación a secas
  f='log_id("cloudaudit.googleapis.com/activity")
resource.type="k8s_cluster"
protoPayload.methodName="io.k8s.core.v1.services.create"
protoPayload.resourceName:"/services/linea-base"'
  local inicio actual hallado
  inicio=$(date +%s)
  while :; do
    hallado=$(gcloud logging read "$f
timestamp>=\"$t0\"" --limit=1 --format='value(timestamp)' 2>/dev/null || true)
    actual=$(date +%s)
    [ -n "$hallado" ] && break
    [ $((actual - inicio)) -ge 300 ] && break
    sleep 5
  done
  kubectl delete service linea-base -n "$NS" >/dev/null
  resultado="el evento se pudo consultar a los $((actual - inicio)) s (registro de $hallado)"
  bitacora "Línea base: borro el Service" "$resultado"
  mkdir -p "$EVIDENCIA/linea-base"
  printf '{"creacion_utc": "%s", "segundos_hasta_consultar": %s, "registro_utc": "%s"}\n' \
    "$t0" "$((actual - inicio))" "$hallado" > "$EVIDENCIA/linea-base/medicion.json"
}

ronda() {
  local n="$1" carpeta="$EVIDENCIA/ronda-$1" t0 t0s t_log t_ctn http_b http_c nodeip nodeport fuera
  mkdir -p "$carpeta"
  preparar >/dev/null
  bitacora "Ronda $n: empieza" "preparado el namespace $NS_PRUEBA y el pod visitante"

  # Inyección A: un Service que expone el puerto de administración (9090 del proxy)
  t0=$(ahora); t0s=$(date +%s)
  kubectl create service nodeport admin-expuesto --tcp=9090:9090 -n "$NS" >/dev/null
  kubectl patch service admin-expuesto -n "$NS" --type merge \
    -p '{"spec":{"selector":{"app":"statsnostra-api"}}}' >/dev/null
  bitacora "Ronda $n, inyección A: creo el Service admin-expuesto (NodePort 9090)" "creado a las $t0"

  # Inyección B: el pod del otro namespace llama a la API (salto este-oeste)
  http_b=$(kubectl exec -n "$NS_PRUEBA" visitante -- curl -s -o /dev/null -m 6 \
    -w '%{http_code}' "http://statsnostra-api-service.$NS/health/live" || true)
  bitacora "Ronda $n, inyección B: visitante llama a la API desde otro namespace" "HTTP $http_b"

  # Inyección C: el pod sale a Internet sin filtro (a la IP pública de esta misma API)
  http_c=$(kubectl exec -n "$NS_PRUEBA" visitante -- curl -s -o /dev/null -m 6 \
    -w '%{http_code}' "http://$IP_PUBLICA/health/live" || true)
  bitacora "Ronda $n, inyección C: visitante sale a Internet (a la IP pública de la API)" "HTTP $http_c"

  # ¿Se puede llegar al NodePort desde fuera de la red? (lo normal es que el firewall lo bloquee)
  nodeip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')
  nodeport=$(kubectl get service admin-expuesto -n "$NS" -o jsonpath='{.spec.ports[0].nodePort}')
  fuera=$(curl -s -o /dev/null -m 6 -w '%{http_code}' "http://$nodeip:$nodeport/" || true)
  bitacora "Ronda $n: pruebo el NodePort $nodeport desde fuera de la red" "HTTP $fuera (000 = sin respuesta)"

  # Detección: tiempo hasta que la señal se puede consultar en Cloud Logging
  if t_log=$(esperar_log "$t0" "$T1_S"); then
    bitacora "Ronda $n, detección: la regla de Services expuestos coincide" "a los ${t_log%% *} s de la creación"
  else
    t_log="sin_deteccion"
    bitacora "Ronda $n, detección: la regla no coincidió" "no hubo señal en $T1_S s"
  fi

  # Alerta: la ronda 1 tiene una política; se mira si llegó un mensaje al tema de pruebas
  local alerta="sin_alerta"
  if gcloud pubsub subscriptions describe alertas-caos-sub >/dev/null 2>&1; then
    local resto=$((T1_S - ($(date +%s) - t0s)))
    [ "$resto" -lt 0 ] && resto=0
    local fin=$(($(date +%s) + resto + 60))
    while [ "$(date +%s)" -lt "$fin" ]; do
      alerta=$(gcloud pubsub subscriptions pull alertas-caos-sub --limit=1 --auto-ack \
        --format='value(message.publishTime)' 2>/dev/null || true)
      [ -n "$alerta" ] && break
      alerta="sin_alerta"
      sleep 10
    done
    bitacora "Ronda $n, alerta: llegó al tema de Pub/Sub" "$alerta"
  else
    bitacora "Ronda $n, alerta: no hay política de alerta" "no se esperó ninguna notificación"
  fi

  # Contención: se borra el Service (lo que haría quien reciba la alerta)
  kubectl delete service admin-expuesto -n "$NS" >/dev/null
  t_ctn=$(ahora)
  bitacora "Ronda $n, contención: borro el Service admin-expuesto" "borrado a las $t_ctn ($(( $(date +%s) - t0s )) s después de crearlo)"

  printf '{"ronda": %s, "creacion_utc": "%s", "contencion_utc": "%s", "http_este_oeste": "%s", "http_salida": "%s", "http_nodeport_desde_fuera": "%s", "senal_en_logs": "%s", "alerta": "%s", "segundos_hasta_contencion": %s}\n' \
    "$n" "$t0" "$t_ctn" "$http_b" "$http_c" "$fuera" "$t_log" "$alerta" "$(( $(date +%s) - t0s ))" > "$carpeta/resultado.json"
  verificar_reversion && bitacora "Ronda $n: verifico el estado inicial" "servicios, políticas y /health/ready en orden"
}

# Prueba de que el flujo normal sigue funcionando (se usa después de aplicar las mejoras)
verificar_flujo() {
  local ready partidos flujo listos
  ready=$(curl -s -o /dev/null -m 10 -w '%{http_code}' "http://$IP_PUBLICA/health/ready" || true)
  partidos=$(curl -s -o /dev/null -m 10 -w '%{http_code}' "http://$IP_PUBLICA/api/v1/partidos" || true)
  flujo=$(curl -s -o /dev/null -m 20 -w '%{http_code}' -H "X-Trace-Id: seg-$(date +%s)" \
    "https://api-coordinador.jollybeach-fbb8b9ad.eastus.azurecontainerapps.io/api/v2/trades/5540" || true)
  listos=$(kubectl get deployment statsnostra-api -n "$NS" -o jsonpath='{.status.readyReplicas}')
  echo "ready=$ready partidos=$partidos flujo_por_coordinador=$flujo réplicas_listas=$listos"
  [ "$ready" = 200 ] && [ "$partidos" = 200 ] && [ "$flujo" = 200 ] && [ "${listos:-0}" -ge 2 ]
}

mejoras() {
  bash seguridad/mejoras/alerta.sh crear
  bitacora "Mejora 1: creo la alerta de Services expuestos (política y tema de Pub/Sub)" "creada"
  preparar >/dev/null
  kubectl apply -f seguridad/mejoras/networkpolicy.yaml
  bitacora "Mejora 2: aplico la NetworkPolicy de denegación por defecto" "aplicada en $NS y $NS_PRUEBA"
  sleep 20
  if resultado=$(verificar_flujo); then
    bitacora "Verifico el flujo normal con las políticas puestas" "$resultado"
  else
    kubectl delete networkpolicy --all -n "$NS" >/dev/null
    bitacora "El flujo normal falló con las políticas: las quito" "$resultado"
    return 1
  fi
}

case "${1:-}" in
  mejoras) mejoras ;;
  preparar) preparar ;;
  linea-base) linea_base ;;
  ronda) ronda "${2:?Falta el número de ronda}" ;;
  parar) parar ;;
  estado)
    kubectl get service,networkpolicy,pods -n "$NS"
    kubectl get all -n "$NS_PRUEBA" 2>/dev/null || true
    ;;
  *)
    sed -n '2,/^set -euo/{/^#/p}' "$0" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
