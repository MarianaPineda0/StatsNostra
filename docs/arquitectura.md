# 🏗️ Arquitectura

## 🧱 Capas y responsabilidad de cada una

```
Peticion HTTP
     |
     v
app/api/routes/*      valida el request (Pydantic), llama al servicio,
                       devuelve la respuesta. No conoce SQL ni reglas de negocio.
     |
     v
app/services/*        reglas de negocio (las 7 reglas, el sistema de puntos,
                       las validaciones de duplicados/estado). No conoce HTTP.
     |
     v
app/repositories/*     acceso a datos: SELECT/INSERT/UPDATE/DELETE via
                       SQLAlchemy. No conoce reglas de negocio.
     |
     v
app/models/*           tablas reales de PostgreSQL (SQLAlchemy ORM)
```

Cada capa solo conoce a la de abajo, nunca a la de arriba. Una ruta nunca
importa `sqlalchemy` directamente; un repositorio nunca lanza una excepción
de "regla de negocio violada". Esto permite, por ejemplo, cambiar de FastAPI
a otro framework web sin tocar una sola línea de `services/` o `models/`.

## 🤔 Por qué esta separación (y no todo junto en la ruta)

Con tres entidades y reglas de negocio explícitas (7 reglas + sistema de
puntos), meter todo en la función de la ruta habría mezclado validación
HTTP, lógica de negocio y SQL en un mismo lugar — difícil de probar de
forma aislada y difícil de razonar. Separando:

- Las reglas de negocio (`services/`) se prueban sin necesidad de un
  cliente HTTP.
- El sistema de puntos (`services/puntos.py`) es una función pura, sin
  base de datos, con pruebas unitarias triviales.
- Los repositorios se pueden auditar para SQL injection o queries
  ineficientes sin tener que leer reglas de negocio.

## 📦 Entidades y relaciones

```
Apostador (1) ──────< Prediccion >────── (1) Partido
```

- Un **Apostador** tiene muchas **Predicciones** (o ninguna).
- Un **Partido** recibe muchas **Predicciones** (o ninguna).
- Una **Prediccion** pertenece exactamente a un Apostador y a un Partido —
  y esa combinación (apostador_id, partido_id) es única (constraint
  `UNIQUE`, reforzando la regla de negocio "sin predicciones duplicadas").

La integridad referencial (foreign keys `apostador_id`, `partido_id`) y las
restricciones de datos (equipos distintos, resultados no negativos,
username/email únicos) están declaradas directamente en los modelos de
SQLAlchemy y se materializan como constraints reales de PostgreSQL — no son
solo validaciones de la aplicación que se podrían saltar con un INSERT
directo.

## 🔍 El repositorio de consultas (`ConsultaRepository`/`ConsultaService`)

No es una cuarta entidad — es una capa que compone lecturas sobre las tres
tablas existentes (por ejemplo, el ranking hace un `JOIN` entre `Apostador`
y `Prediccion` con `GROUP BY`). Se separó de los repositorios/servicios de
cada entidad porque estas consultas no pertenecen naturalmente a una sola
tabla.

## ⚙️ Capa de configuración (`app/core/`)

- `config.py`: lee toda la configuración desde variables de entorno
  (`pydantic-settings`), nunca hardcodeada.
- `exceptions.py`: excepciones de dominio (`RecursoNoEncontrado`,
  `ConflictoDeDatos`, `ReglaDeNegocioViolada`) que los servicios lanzan sin
  saber nada de HTTP — `app/main.py` las traduce a códigos de estado
  (404/409/400 respectivamente) en un solo lugar.
- `middleware.py`: el mecanismo de compatibilidad del verbo QUERY (ver
  [`docs/pruebas.md`](pruebas.md) para el porqué).

## 🔌 Inyección de dependencias

`app/api/dependencies.py` arma cada servicio con su(s) repositorio(s) y la
sesión de base de datos de esa petición específica, usando el sistema de
`Depends` de FastAPI. Cada ruta pide `service: XService = Depends(get_x_service)`
y recibe una instancia lista para usar — sin construirla a mano ni acoplar
la ruta a los detalles de qué repositorios necesita cada servicio.
