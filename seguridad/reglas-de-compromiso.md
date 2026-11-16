# Reglas de compromiso

Acuerdo del grupo para los experimentos de seguridad. Mientras las tres APIs no lo acepten, no se
ejecuta ningún experimento. Los valores de la sección 4 en adelante son los de StatsNostra
(experimento 2, exposición y segmentación); trading-journal y ecommerce completan los suyos
en sus repositorios con el mismo formato.

## 1. Ventana

Hora de Colombia. Propuesta, a confirmar en el grupo antes de cada ronda:

| Ronda | Inicio | Fin |
|---|---|---|
| Medición del estado estable de seguridad | lunes 16 de noviembre, 09:00 | 09:30 |
| Ronda 0 | lunes 16 de noviembre, 10:00 | 10:40 |
| Ronda 1 | lunes 16 de noviembre, 14:00 | 14:40 |

Fuera de la ventana no se crea, modifica ni borra ningún recurso del experimento.

## 2. Alcance

Solo cuentas, proyectos y suscripciones del grupo en Azure, Google Cloud, AWS y Oracle. Para
StatsNostra: el proyecto de Google Cloud `project-3f57bb8c-371e-4b9c-949`, el clúster
`statsnostra-v5-gke` y los namespaces `statsnostra` y `caos-seguridad`.

Está prohibido actuar sobre servicios, cuentas, redes o datos de terceros, de la Universidad o de
otros grupos. Tampoco se hacen accesos desde otros orígenes con cuentas de directorios de
empresa: lo que se simula es una configuración no prevista, no un inicio de sesión ajeno.

## 3. Datos

Solo datos sintéticos del proyecto. Los experimentos no leen, copian ni envían datos reales.

## 4. Radio de impacto (StatsNostra)

- Un Service de prueba llamado `admin-expuesto` en el namespace `statsnostra`, de tipo NodePort,
  que apunta al puerto 9090 (el de salud del Cloud SQL Auth Proxy). Cloud SQL no se toca y el
  firewall del proyecto no abre ese rango de puertos a Internet.
- Un namespace `caos-seguridad` con un solo pod de prueba que intenta llamar a la API desde otro
  namespace (salto este-oeste) y salir a Internet.
- Una NetworkPolicy con denegación por defecto en `statsnostra` solo durante la ronda 1.
- Máximo 10 peticiones por prueba. No se modifican el Service público, el Deployment ni los pods
  del API, y no se envía carga con k6 durante la ventana.
- Un namespace `caos-seguridad` con su propia política de denegación por defecto, para aislar el
  pod de prueba. Es un namespace del experimento, así que solo reduce el riesgo.

### Tendencias (15 de noviembre, después de las rondas)

Tres cambios en el proyecto de Google Cloud que no estaban en el radio de arriba y se declaran
aquí. Ninguno toca el tráfico ni reinicia pods, y cada uno se puede deshacer:

- **Secreto señuelo** `statsnostra-admin-respaldo` en Secret Manager, con un valor sintético, y
  una alerta que avisa si alguien lo abre. Se borra al terminar la entrega.
- **Registros de lectura de datos de Secret Manager** habilitados en el proyecto, que antes no
  estaban. Se pueden volver a apagar quitando esa configuración de auditoría.
- **Cuenta de servicio del despliegue** con 7 roles en el proyecto en vez de 18, más lectura de
  un solo secreto. Cada operación del despliegue se probó suplantando a la cuenta, y
  `seguridad/tendencias/minimo_privilegio.sh restaurar` devuelve los roles anteriores.

### Experimento 4 (datos)

StatsNostra aporta un único objeto sintético, una predicción en JSON, en
`seguridad/datos/objetos/statsnostra/` con su archivo `.sha256`. No se usa ningún dato real y
no se toca ninguna infraestructura de StatsNostra: el bucket y el ataque son los de las reglas
del grupo (trading-journal).

## 5. Interruptor de parada

Lo acciona StatsNostra; lo puede accionar cualquiera de los tres con acceso al clúster:

```bash
kubectl delete service admin-expuesto -n statsnostra --ignore-not-found
kubectl delete namespace caos-seguridad --ignore-not-found
kubectl delete networkpolicy --all -n statsnostra
```

## 6. Reversión

Los tres comandos anteriores dejan el clúster como antes. Se verifica así:

```bash
kubectl get service,networkpolicy -n statsnostra     # solo statsnostra-api-service, sin políticas
curl -s -o /dev/null -w "%{http_code}\n" http://34.68.14.217/health/ready    # 200
```

Más una consulta del flujo completo por trading-journal con un trace id nuevo. La reversión se
prueba antes de la ronda 0 y el resultado se anota en la bitácora.

## 7. Bitácora

Cada acción se registra con hora, responsable y resultado en [`bitacora.md`](bitacora.md).

## 8. Condiciones de aborto

Se ejecuta el interruptor de parada y se anota la causa si ocurre cualquiera de estas:

- `/health/ready` de StatsNostra no responde 200 durante más de 60 s.
- El flujo completo falla en una prueba de humo.
- Se detecta tráfico o un recurso fuera del alcance de la sección 2.
- Se llega al fin de la ventana con el experimento sin terminar.
- Cualquiera de las tres APIs pide parar.

## Aceptan

| API | Aceptado | Fecha |
|---|---|---|
| StatsNostra | [x] | 2026-11-15 |
| trading-journal | [x] | 2026-11-15 |
| ecommerce | [x] | 2026-11-15 |

StatsNostra también acepta las reglas del grupo para los experimentos 1 y 4, publicadas en el
repositorio de trading-journal (aceptadas el 16 de noviembre de 2026 en el chat del grupo).
