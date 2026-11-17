# Resultados del experimento 2: exposición y segmentación

Generado por `seguridad/resumen.py` a partir de `evidencia/`. La hipótesis: con la red tal como está, al crearse un Service que expone el puerto de administración hay alerta en 5 minutos o menos (T1) y contención en 10 minutos o menos (T2).

| | Ronda 0 (sin mejoras) | Ronda 1 (alerta y NetworkPolicy) |
|---|---|---|
| Alerta recibida | no | sí |
| MTTD (creación a alerta) | no se detectó | 45 s |
| MTTC (alerta a contención) | sin alerta no hubo quién contuviera | 15 s |
| Contención desde la creación | 28 s (la hizo el operador, que ya sabía del evento) | 61 s |
| Evento consultable en Cloud Logging | 7 s | 21 s |
| A: NodePort alcanzado desde fuera de la red | bloqueada | bloqueada |
| B: salto este-oeste desde otro namespace | pasó (HTTP 200) | bloqueada |
| C: salida a Internet sin filtro | pasó (HTTP 200) | bloqueada |
| Hipótesis | se refuta: no hay alerta | se cumple |

## Línea base de la señal

Con un Service inofensivo, el evento de creación se pudo consultar en Cloud Logging a los 28 s. Es el piso de cualquier detección basada en esos registros.

## Cobertura

De las tres inyecciones, la alerta cubre la A (1 de 3). La B y la C no generan alerta: se previenen con la NetworkPolicy, pero hoy no dejan una señal propia. Es un pendiente explícito (alerta sobre los registros de flujo denegados).

## Hallazgo posterior (17 de noviembre)

Al dejar la NetworkPolicy en el despliegue, los pods nuevos no pudieron abrir conexiones a la base ni a Grafana: `/api/v1/partidos` dio 500 tras 30 s de espera en un pod y la exportación de telemetría agotó el tiempo. Al borrar las políticas el servicio volvió en segundos. En la ronda 1 el flujo seguía dando 200 porque las conexiones ya abiertas no necesitan resolver nombres ni renovar certificados. La causa: los pods resuelven por el ClusterIP de kube-dns y los nodos redirigen esa consulta a la caché local (node-local-dns), a la que las reglas no daban salida. Corregido y probado con DNS, conexiones nuevas, un arranque en frío y diez peticiones a la base con las políticas puestas (`acciones/probar_politicas.sh`); la política quedó permanente en el despliegue.
