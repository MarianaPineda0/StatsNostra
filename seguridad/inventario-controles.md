# Inventario de controles de StatsNostra

Lo que hay hoy en la API que corre en GKE, por capa. "Estado" es lo que se comprobó en el
repositorio o en el clúster; los huecos están marcados como tales porque son los que cierran las
mejoras del experimento 2.

Mapeo con MITRE D3FEND (técnicas comprobadas en d3fend.mitre.org) y con las normas de la
trazabilidad: ISO/IEC 27001:2022 Anexo A, NIST SP 800-53 y NIST SP 800-207.

## Identidad

| Control | Dónde | Estado | Señal | D3FEND / normas |
|---|---|---|---|---|
| Despliegue sin llaves: GitHub entra a Google Cloud con Workload Identity Federation | `desplegar-gke.yml`, pool `github-pool` | Activo | Registros de auditoría de IAM | ISO 5.15, 8.2; NIST AC-6, IA-5 |
| Cuenta de los nodos con permisos mínimos (logs, métricas, imágenes, Cloud SQL) | `terraform/cuentas.tf` | Activo | Registros de auditoría de IAM | ISO 8.2; NIST AC-6 |
| Contraseña de la base efímera, sin quedar en el estado de Terraform, y guardada en Secret Manager | `terraform/cloudsql.tf`, `secretos.tf` | Activo | Auditoría de Secret Manager | ISO 5.17; NIST IA-5 |
| Auditoría de lectura de secretos (registros de acceso a datos) | Secret Manager | Activo (cerrado el 15 nov): se habilitó la lectura de datos del servicio | `cloudaudit.googleapis.com/data_access` | NIST AU-2 |
| Cuenta del despliegue con mínimo privilegio: 7 roles en el proyecto en vez de 18 | IAM, `seguridad/tendencias/minimo_privilegio.sh` | Activo (cerrado el 15 nov) | Registros de auditoría de IAM | ISO 5.15, 8.2; NIST AC-6 |

## Red

| Control | Dónde | Estado | Señal | D3FEND / normas |
|---|---|---|---|---|
| Red y subred propias, con registros de flujo (cada 5 s, muestreo del 50 %) | `terraform/network.tf` | Activo | Registros `vpc_flows` en Cloud Logging | D3-NTA (Network Traffic Analysis); ISO 8.16; NIST SI-4 |
| Dataplane V2: el clúster hace cumplir las NetworkPolicy | `terraform/gke.tf` | Activo | Registros de decisiones de red | D3-NI (Network Isolation); NIST SC-7 |
| Entrada pública solo al puerto 80 del Service, hacia el 8000 de la API | `k8s/service.yaml` | Activo | Registros de flujo | D3-ITF (Inbound Traffic Filtering); ISO 8.20 |
| Cloud SQL sin redes autorizadas: solo se entra por el proxy | `terraform/cloudsql.tf` | Activo | Registros de Cloud SQL | D3-ITF; ISO 8.20 |
| NetworkPolicy de denegación por defecto y permisos explícitos | `statsnostra` | Activo (cerrado el 17 nov): entrada solo al puerto de la API y salida solo a DNS (incluida la caché local de nodos), metadatos, 443 y 3307; probada con un pod recién creado | Ninguna propia | D3-NI, D3-ITF; ISO 8.22; NIST AC-4, SC-7; NIST SP 800-207 (microsegmentación) |
| Filtrado de salida de los pods | `statsnostra` | Activo (cerrado el 17 nov): solo por puerto, no por destino | Registros de flujo | D3-OTF (Outbound Traffic Filtering); ISO 8.23; NIST SC-7 |

## Carga de trabajo

| Control | Dónde | Estado | Señal | D3FEND / normas |
|---|---|---|---|---|
| Imagen sin root (`appuser`), sin escalada de privilegios y sin capacidades | `Dockerfile`, `k8s/deployment.yaml` | Activo | Registros de auditoría de Kubernetes | ISO 8.9; NIST CM-7 |
| Requests y límites de CPU y memoria | `k8s/deployment.yaml` | Activo | Métricas del clúster | NIST SC-6 |
| Nodos con arranque seguro y monitoreo de integridad | `terraform/gke.tf` | Activo | Registros de nodos | ISO 8.9 |
| Sistema de archivos de solo lectura y estándares de seguridad de pods por namespace | `statsnostra` | **Hueco**: no están configurados | Ninguna hoy | ISO 8.9; NIST CM-6 |

## Datos

| Control | Dónde | Estado | Señal | Normas |
|---|---|---|---|---|
| Solo datos sintéticos | todo el proyecto | Activo | | ISO 8.11 |
| Cifrado en reposo y en tránsito hacia la base (proxy) | Cloud SQL | Activo (predeterminado de Google) | | ISO 8.24; NIST SC-28 |
| Copias de seguridad de Cloud SQL | `terraform/cloudsql.tf` | **Hueco**: no están configuradas | Ninguna hoy | ISO 8.13; NIST CP-9 |

## Detección y respuesta

| Control | Dónde | Estado | Señal | D3FEND / normas |
|---|---|---|---|---|
| Registros de auditoría de Kubernetes (actividad de administración) en Cloud Logging | GKE | Activo | `cloudaudit.googleapis.com/activity` con `io.k8s.core.v1.services.create` y similares | ISO 8.15; NIST AU-2, AU-12 |
| Log JSON de cada petición con trace id, ruta, status y duración | `app/core/middleware.py` | Activo | Cloud Logging | ISO 8.15; NIST AU-3 |
| Alerta sobre servicios nuevos expuestos | Cloud Logging y Pub/Sub | Activo (cerrado el 15 nov) | Alerta a los 45 s en la ronda 1 | ISO 8.16; NIST SI-4, IR-4 |
| Secreto señuelo con alerta de lectura | Secret Manager | Activo (cerrado el 15 nov) | Alerta al abrir `statsnostra-admin-respaldo` | ISO 8.16; NIST SI-4 |
| Alerta sobre tráfico este-oeste no declarado | Cloud Logging | **Hueco**: no existe | Ninguna hoy | D3-NTA; ISO 8.16 |

## Cómo se usa

Los huecos eran la base del experimento 2: la ronda 0 midió la detección con el control tal como
estaba (sin alertas ni NetworkPolicy) y la ronda 1 la repitió después de cerrar dos. Los que se
cerraron después dicen "cerrado el N nov" en la columna de estado. La NetworkPolicy se aplicó
en la ronda 1 y se revirtió; el 17 de noviembre se dejó permanente, falló con pods nuevos por una
regla de DNS que faltaba (la caché local de nodos), y ya está corregida y probada.
dejarla de forma permanente. Las técnicas de ATT&CK emuladas, comprobadas en attack.mitre.org, son
Exploit Public-Facing Application (T1190), Remote Services (T1021) y Exfiltration Over
Alternative Protocol (T1048).
