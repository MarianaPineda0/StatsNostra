# Docker

## Qué se ejecuta

`docker compose up --build` levanta dos servicios:

- **`db`**: PostgreSQL 16, con dos bases de datos reales (`statsnostra_pruebas`,
  `statsnostra_produccion`), cada una con su propio rol de conexión aislado
  (ver [`arquitectura.md`](arquitectura.md) y `scripts/db/init-databases.sh`).
- **`api`**: la aplicación FastAPI, construida a partir del `Dockerfile`.

Ambos quedan conectados en una red interna que Docker Compose crea
automáticamente. Dentro de esa red, `api` se conecta a la base de datos usando
el nombre del servicio (`db`) como host — no `localhost`, porque `localhost`
dentro de un contenedor se refiere al propio contenedor, no a otro.

## Por qué un Dockerfile multi-stage

El `Dockerfile` tiene dos etapas:

1. **`builder`**: instala las dependencias de Python dentro de un entorno
   virtual (`/opt/venv`).
2. **Etapa final**: parte de una imagen limpia (`python:3.12-slim`) y solo
   copia el entorno virtual ya construido y el código de la app — sin las
   herramientas de compilación ni la caché de `pip` que se usaron para
   instalar las dependencias.

Resultado: una imagen final más liviana, porque no arrastra nada que solo
sirvió para el proceso de instalación.

## Buenas prácticas aplicadas

- **Usuario no root** (`appuser`): si alguien lograra ejecutar código dentro
  del contenedor, no tendría privilegios de administrador sobre el sistema
  de archivos del contenedor.
- **`PYTHONDONTWRITEBYTECODE=1`**: evita que Python genere archivos `.pyc`
  innecesarios dentro de la imagen.
- **`PYTHONUNBUFFERED=1`**: los logs de la aplicación se escriben en tiempo
  real, sin quedar retenidos en un buffer (importante para ver logs en vivo
  en Render o en `docker logs`).
- **`.dockerignore`**: evita copiar archivos innecesarios o sensibles
  (`.env`, `.git`, `tests/`, etc.) al contexto de construcción de la imagen.
- **Migraciones automáticas**: el comando de arranque del servicio `api`
  ejecuta `alembic upgrade head` antes de iniciar Uvicorn, así que un
  `docker compose up --build` desde cero deja la base de datos con las
  tablas ya creadas, sin pasos manuales adicionales.
- **Health checks**: tanto `db` como `api` tienen verificación de salud
  (`pg_isready` y una petición real a `/health`, respectivamente), lo que le
  permite a Docker Compose saber cuándo cada servicio está realmente listo
  para recibir tráfico (no solo "iniciado").

## Verificación realizada

`docker compose down -v && docker compose up --build` desde cero:
migraciones aplicadas automáticamente, escritura real a la base de datos
verificada (`POST /apostadores` → 201), método QUERY verificado (`QUERY
/query/apostadores/ranking` → 200), Swagger accesible en `/docs`. Imagen
final: 324 MB. Usuario dentro del contenedor confirmado como `appuser`
(no root).
