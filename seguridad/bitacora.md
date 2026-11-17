# Bitácora de los experimentos de seguridad de StatsNostra

Una fila por acción, con la hora de Colombia, quién la hizo y qué resultó. Se llena durante la
ventana, no después.

| Hora | Quién | Acción | Resultado |
|---|---|---|---|
| | | | |
| 16:13:29 | StatsNostra | Ventana: las tres APIs aceptaron las reglas y confirmaron en el grupo que no hacen cambios ni peticiones (domingo 15 de noviembre) | acordada |
| 16:13:40 | StatsNostra | Línea base: creo un Service ClusterIP inofensivo (linea-base) | creado a las 2026-11-15T21:13:39Z |
| 16:14:09 | StatsNostra | Línea base: borro el Service | el evento se pudo consultar a los 28 s (registro de 2026-11-15T21:13:40.486973Z) |
| 16:14:29 | StatsNostra | Prueba de reversión antes de la ronda 0: creo admin-expuesto y ejecuto los tres comandos de parada | servicios, políticas y /health/ready en orden |
| 16:15:18 | StatsNostra | Ronda 0: empieza | preparado el namespace caos-seguridad y el pod visitante |
| 16:15:20 | StatsNostra | Ronda 0, inyección A: creo el Service admin-expuesto (NodePort 9090) | creado a las 2026-11-15T21:15:18Z |
| 16:15:22 | StatsNostra | Ronda 0, inyección B: visitante llama a la API desde otro namespace | HTTP 200 |
| 16:15:23 | StatsNostra | Ronda 0, inyección C: visitante sale a Internet (a la IP pública de la API) | HTTP 200 |
| 16:15:31 | StatsNostra | Ronda 0: pruebo el NodePort 32260 desde fuera de la red | HTTP 000 (000 = sin respuesta) |
| 16:15:39 | StatsNostra | Ronda 0, detección: la regla de Services expuestos coincide | a los 7 s de la creación |
| 16:15:45 | StatsNostra | Ronda 0, alerta: no hay política de alerta | no se esperó ninguna notificación |
| 16:15:46 | StatsNostra | Ronda 0, contención: borro el Service admin-expuesto | borrado a las 2026-11-15T21:15:46Z (28 s después de crearlo) |
| 16:15:48 | StatsNostra | Ronda 0: verifico el estado inicial | servicios, políticas y /health/ready en orden |
| 16:23:56 | StatsNostra | Mejora 1: creo la alerta de Services expuestos (política y tema de Pub/Sub) | creada |
| 16:24:03 | StatsNostra | Mejora 2: aplico la NetworkPolicy de denegación por defecto | aplicada en statsnostra y caos-seguridad |
| 16:24:27 | StatsNostra | Verifico el flujo normal con las políticas puestas | ready=200 partidos=200 flujo_por_coordinador=200 réplicas_listas=2 |
| 16:25:08 | StatsNostra | Ronda 1: empieza | preparado el namespace caos-seguridad y el pod visitante |
| 16:25:10 | StatsNostra | Ronda 1, inyección A: creo el Service admin-expuesto (NodePort 9090) | creado a las 2026-11-15T21:25:08Z |
| 16:25:17 | StatsNostra | Ronda 1, inyección B: visitante llama a la API desde otro namespace | HTTP 000 |
| 16:25:25 | StatsNostra | Ronda 1, inyección C: visitante sale a Internet (a la IP pública de la API) | HTTP 000 |
| 16:25:33 | StatsNostra | Ronda 1: pruebo el NodePort 32502 desde fuera de la red | HTTP 000 (000 = sin respuesta) |
| 16:25:54 | StatsNostra | Ronda 1, detección: la regla de Services expuestos coincide | a los 21 s de la creación |
| 16:26:07 | StatsNostra | Ronda 1, alerta: llegó al tema de Pub/Sub | 2026-11-15T21:25:52.952Z |
| 16:26:08 | StatsNostra | Ronda 1, contención: borro el Service admin-expuesto | borrado a las 2026-11-15T21:26:08Z (60 s después de crearlo) |
| 16:26:11 | StatsNostra | Ronda 1: verifico el estado inicial | servicios, políticas y /health/ready en orden |
| 16:27:26 | StatsNostra | Control extra: quito la política de caos-seguridad y llamo a la API por su ClusterIP, para aislar la política de entrada de statsnostra (la B anterior falló ya en el DNS) | HTTP 000 (000 = bloqueado por la política de entrada) |
| 16:28:20 | StatsNostra | Parada y reversión al terminar la ronda 1: borro políticas y namespace de prueba | servicios, políticas y /health/ready en orden |
