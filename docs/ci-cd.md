# CI/CD

## Herramienta

Se usa **GitHub Actions** como herramienta SaaS de CI/CD (integrada directo
en el repositorio, sin necesidad de configurar un servicio externo).

## Dos pipelines independientes

| Pipeline | Archivo | Se dispara con | Cobertura mínima |
|---|---|---|---|
| Pruebas | `.github/workflows/pruebas.yml` | push a `develop` | ≥ 60% |
| Producción | `.github/workflows/produccion.yml` (pendiente) | push a `main` | ≥ 85% |

## Qué hace el pipeline de Pruebas, paso a paso

1. **Checkout** del código del repositorio.
2. **Configura Python** 3.12.
3. **Build / instalación de dependencias** (`pip install -r requirements-dev.txt`).
4. **Levanta un PostgreSQL efímero**, exclusivo de esa ejecución del pipeline
   (no es ni tu Postgres local ni el de Render — se crea al iniciar el
   pipeline y se destruye al terminar).
5. **Aplica las migraciones** de Alembic sobre ese Postgres temporal.
6. **Corre las pruebas automatizadas con `pytest`**, validando además la
   cobertura mínima (`--cov-fail-under=60`) — si la cobertura es menor,
   este paso falla.
7. **Lint** (`ruff check .`) y **formato** (`black --check .`).
8. **Construye la imagen Docker**, para confirmar que el `Dockerfile` sigue
   siendo válido.
9. **Despliega a Render**, pero **solo si todos los pasos anteriores
   pasaron**.

## Cómo se bloquea el despliegue si algo falla

El pipeline está dividido en dos *jobs*: `test` y `deploy`. El job `deploy`
tiene la directiva `needs: test` — en GitHub Actions, esto significa que
`deploy` **no se ejecuta en absoluto** si `test` termina en error. No es una
validación manual ni una condición que alguien pueda saltarse: es una regla
estructural del pipeline.

## Cómo se conecta con Render

El despliegue se dispara llamando a un **Deploy Hook** (una URL privada que
Render genera por servicio). Esa URL se guarda como un **GitHub Secret**
(`RENDER_DEPLOY_HOOK_PRUEBAS`), nunca como texto plano en el repositorio —
el workflow la referencia como `${{ secrets.RENDER_DEPLOY_HOOK_PRUEBAS }}`,
así que ni siquiera aparece en los logs del pipeline.

## Pendiente

- Validar el pipeline con una ejecución real, incluyendo la prueba
  deliberada de que un test fallido bloquea el despliegue.
- Crear el pipeline equivalente para Producción (`produccion.yml`), con
  cobertura ≥85% y su propio Deploy Hook (`RENDER_DEPLOY_HOOK_PRODUCCION`).
