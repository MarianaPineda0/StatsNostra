# Pruebas

## Enfoque

Las pruebas corren contra una base de datos **PostgreSQL real** (no mocks ni
datos simulados en memoria) — así se valida que las restricciones reales de
la base de datos (usernames únicos, `equipo_local != equipo_visitante`,
predicciones duplicadas, etc.) funcionan de verdad, no solo que el código
"parece" correcto.

Cada prueba corre dentro de una transacción que se revierte al final
(`tests/conftest.py`), así que no deja rastro en la base de datos entre
ejecuciones, aunque comparta la misma BD que se usa para desarrollo manual.

## Cobertura

```
43 pruebas, 43 exitosas
Cobertura total: 97.18%
```

Ambos quality gates de la rúbrica, verificados localmente:

```bash
pytest --cov=app --cov-fail-under=60   # Pruebas -> pasa
pytest --cov=app --cov-fail-under=85   # Produccion -> pasa
```

## Qué se prueba

- **Apostador**: CRUD completo, username/email únicos, apostador inexistente.
- **Partido**: CRUD completo, equipos distintos, resultados no negativos,
  finalización (y bloqueo de doble finalización).
- **Predicción**: CRUD completo y las 5 reglas de negocio (apostador
  existente/activo, partido existente/no finalizado, sin duplicados).
- **Sistema de puntos**: pruebas unitarias puras (marcador exacto = 3,
  resultado correcto = 1, incorrecto = 0), sin tocar la base de datos.
- **QUERY**: los 6 endpoints, incluyendo filtros, y el mecanismo de
  compatibilidad vía `POST` + `X-HTTP-Method-Override`.

## Validación real del bloqueo de despliegue

La rúbrica exige demostrar, no solo afirmar, que un test fallido bloquea el
despliegue. Se hizo así, con evidencia en GitHub Actions:

| Run | Commit | Resultado |
|---|---|---|
| #1 | `315c507` | Pipeline configurado, pasa correctamente |
| #2 | `500d5e8` | Prueba fallida agregada a propósito -> pipeline en **failure** -> job de deploy queda **skipped** (nunca se ejecuta) |
| #3 | `2436428` | Prueba artificial eliminada -> pipeline vuelve a **success** -> deploy corre de nuevo |

Esto confirma que la regla `needs: test` en
`.github/workflows/pruebas.yml` realmente impide el despliegue cuando algo
falla — no es una validación manual que alguien pueda saltarse.

## Cómo correr las pruebas localmente

```bash
docker compose up -d db
pytest -v
pytest --cov=app --cov-report=html   # abre htmlcov/index.html
ruff check .
black --check .
```
