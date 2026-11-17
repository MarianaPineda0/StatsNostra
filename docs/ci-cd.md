# CI/CD

Se usa GitHub Actions. En esta rama hay dos pipelines que importan.

| Pipeline | Archivo | Cuándo corre |
|---|---|---|
| Pruebas | `.github/workflows/pruebas.yml` | push a `v5-develop` y pull requests hacia `v5` |
| Despliegue a GKE | `.github/workflows/desplegar-gke.yml` | push a `v5` que cambie `app/`, `migrations/`, `k8s/`, `Dockerfile`, `requirements.txt`, `alembic.ini` o `scripts/desplegar-gke.sh`, o a mano |

(`produccion.yml` es de la línea v1 a v4 y solo se dispara con `main`.)

## Pruebas

1. Instala las dependencias de Python 3.12.
2. Levanta un PostgreSQL efímero para esa ejecución y aplica las migraciones de Alembic.
3. Corre `pytest` (107 pruebas, contra la base real).
4. Revisa el código con `ruff check .` y el formato con `black --check .`.

Si cualquier paso falla, el pipeline falla y el PR no se puede fusionar.

## Despliegue

El workflow hace lo mismo que `scripts/desplegar-gke.sh`, para que haya una sola forma de
desplegar:

1. Se autentica en Google Cloud con Workload Identity Federation, sin llaves guardadas.
2. Construye la imagen y la sube a Artifact Registry.
3. Ejecuta el Job de migración de Alembic y espera a que termine.
4. Aplica los manifiestos de `k8s/` (ConfigMap, Deployment, Service y HPA) y espera el rollout.
5. Hace una prueba de humo por la IP pública: espera un 200 en `/health/ready`, consulta
   `/api/v1/partidos` y `/api/v1/predicciones` y comprueba la cabecera `X-App-Name`.

Un merge a `v5` que cambie esos archivos reinicia los pods. Si otra API del grupo está midiendo
con carga en ese momento, conviene avisarles antes de fusionar.

## Flujo de ramas

`v5-develop` es la rama de trabajo; cada cambio llega a `v5` por pull request con las pruebas en
verde. Los commits usan GitMoji y las versiones siguen SemVer: `v5.0.0` para el experimento de
DevOps y `v5.1.0` para el de seguridad.
