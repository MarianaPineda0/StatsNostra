# Infraestructura de StatsNostra en Google Cloud

Terraform crea todo lo que necesita la API en GKE. El estado vive en un bucket de Cloud Storage
(`backend.tf`), no en el repositorio.

## Qué crea

| Archivo | Recursos |
|---|---|
| `apis.tf` | Habilita las APIs de Google Cloud que usa el proyecto (`disable_on_destroy = false`, para no apagar las que usan otros recursos) |
| `network.tf` | Red y subred propias, con registro de flujos de red (muestreo del 50 %) |
| `gke.tf` | Clúster zonal con Dataplane V2 (`ADVANCED_DATAPATH`, que aplica las NetworkPolicy) y un grupo de nodos e2-medium de 2 a 3 nodos con arranque seguro |
| `cuentas.tf` | Cuenta de servicio de los nodos con solo los permisos que necesitan (logs, métricas, imágenes, Cloud SQL) |
| `cloudsql.tf` | PostgreSQL db-g1-small sin redes autorizadas: solo se entra por el Cloud SQL Auth Proxy |
| `secretos.tf` | Contraseña de la base y URL de conexión en Secret Manager |
| `artifact_registry.tf` | Repositorio de imágenes Docker |
| `ip.tf` | IP pública reservada para el Service de la API |

La contraseña de la base es efímera: se genera en cada ejecución y se pasa a Cloud SQL con un
atributo de solo escritura (`password_wo`), así que no queda guardada en el estado de Terraform.
Por eso hace falta Terraform 1.11 o superior.

## Cómo usarlo

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars    # opcional: todos los valores tienen defecto
terraform init -backend-config="bucket=NOMBRE-DEL-BUCKET-DE-ESTADO"
terraform plan
terraform apply
```

El bucket de estado se crea a mano una vez, antes del primer `init`, con acceso uniforme y
versionado. Si las subidas del estado se cortan, `GODEBUG=http2client=0` evita los errores de
HTTP/2.

`terraform output` devuelve la IP de la API, el clúster, la conexión de Cloud SQL y el
repositorio de imágenes. Después se despliega la API con `scripts/desplegar-gke.sh` (ver el
README de la raíz).

## Costo y destrucción

Con todo encendido, la infraestructura cuesta unos 3,5 USD al día. Al terminar la entrega:

```bash
terraform plan -destroy     # revisar que solo aparezcan recursos de esta infraestructura
terraform destroy
```

El clúster tiene `deletion_protection = false` a propósito, para poder destruirlo así.
