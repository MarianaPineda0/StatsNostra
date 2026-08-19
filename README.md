# 🏆 StatsNostra

API RESTful de predicciones deportivas. Los usuarios (apostadores) predicen
el marcador de partidos y acumulan puntos según qué tan acertada haya sido
su predicción una vez el partido finaliza.

<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy"/>
  <img src="https://img.shields.io/badge/Alembic-Migrations-8A2BE2?style=for-the-badge" alt="Alembic"/>
</p>
<p>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/Docker%20Compose-Orquestado-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Compose"/>
  <img src="https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions"/>
  <img src="https://img.shields.io/badge/Render-Deploy-46E3B7?style=for-the-badge&logo=render&logoColor=white" alt="Render"/>
  <img src="https://img.shields.io/badge/Pytest-97%25%20coverage-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest coverage"/>
</p>

## 🔗 Enlaces en vivo

| | Ambiente | URL |
|---|---|---|
| 🟢 | **Pruebas** — API | [statsnostra-pruebas.onrender.com](https://statsnostra-pruebas.onrender.com) |
| 📘 | **Pruebas** — Swagger | [statsnostra-pruebas.onrender.com/docs](https://statsnostra-pruebas.onrender.com/docs) |
| 🔵 | **Producción** — API | [statsnostra-produccion.onrender.com](https://statsnostra-produccion.onrender.com) |
| 📘 | **Producción** — Swagger | [statsnostra-produccion.onrender.com/docs](https://statsnostra-produccion.onrender.com/docs) |
| 🐙 | **Repositorio** | [github.com/MarianaPineda0/StatsNostra](https://github.com/MarianaPineda0/StatsNostra) |

> ⏱️ Los servicios gratuitos de Render "duermen" tras 15 min de
> inactividad — la primera petición puede tardar ~50 s en responder
> mientras arrancan de nuevo. No es un error.

## 🎯 Objetivo

Proyecto de la materia **Énfasis I: DevOps**, construido para demostrar un
ciclo completo de desarrollo y despliegue: API REST real con persistencia en
PostgreSQL, contenerización con Docker, y dos ambientes independientes
(Pruebas/Producción) desplegados en Render mediante pipelines de CI/CD con
GitHub Actions.

## 🏗️ Arquitectura

Arquitectura por capas, cada una con una única responsabilidad:

```
app/
├── api/            # Rutas HTTP (FastAPI) y wiring de dependencias
│   ├── routes/
│   └── dependencies.py
├── core/           # Configuración, excepciones de dominio, middleware
├── db/             # Conexión a PostgreSQL (engine, sesión)
├── models/         # Entidades de SQLAlchemy (tablas reales)
├── schemas/        # Validación de entrada/salida (Pydantic)
├── repositories/   # Acceso a datos (consultas SQL), sin reglas de negocio
├── services/       # Reglas de negocio — capa donde vive la lógica real
└── main.py         # Punto de entrada de la aplicación
```

Flujo de una petición: **ruta → servicio (valida reglas de negocio) →
repositorio (accede a la BD) → modelo (tabla real)**. Ninguna ruta accede a
la base de datos directamente, y ningún repositorio contiene reglas de
negocio — ver [`docs/arquitectura.md`](docs/arquitectura.md) para el
detalle completo.

## 🛠️ Tecnologías

| Categoría | Tecnología |
|---|---|
| 🐍 Backend | Python 3.12, FastAPI, Uvicorn |
| 🐘 Base de datos | PostgreSQL 16/18 |
| 🔗 ORM | SQLAlchemy 2.x |
| 🗃️ Migraciones | Alembic |
| ✅ Validación | Pydantic v2 |
| 🧪 Testing | Pytest, pytest-cov, httpx |
| 🧹 Calidad | Ruff, Black |
| 🐳 Contenedores | Docker, Docker Compose |
| 🚀 CI/CD | GitHub Actions |
| ☁️ Cloud | Render (plan gratuito) |

## 📦 Entidades y relaciones

Tres entidades del dominio, sin excepciones:

- 🙋 **Apostador** — usuario que registra predicciones (`nombre`, `username`
  único, `email` único, `activo`).
- ⚽ **Partido** — evento deportivo (`deporte`, `liga`, equipos, `estado`,
  resultados una vez finalizado).
- 🔮 **Predicción** — pronóstico de un apostador sobre un partido
  (`goles_local_pred`, `goles_visitante_pred`, `acertada`, `puntos`).

```
Apostador (1) ────< Predicción >──── (1) Partido
```

Un apostador puede tener muchas predicciones; un partido puede recibir
muchas predicciones; pero un mismo apostador solo puede predecir **una vez**
por partido (constraint `UNIQUE(apostador_id, partido_id)`).

## 📜 Reglas de negocio

1️⃣ No se puede predecir un partido ya finalizado.
2️⃣ El apostador debe existir.
3️⃣ El apostador debe estar activo.
4️⃣ El partido debe existir.
5️⃣ Un apostador no puede tener dos predicciones para el mismo partido.
6️⃣ Un partido no se puede finalizar dos veces.
7️⃣ Al finalizar un partido, se evalúan automáticamente todas sus predicciones.

**🏅 Sistema de puntos** (aplicado al finalizar un partido):

| Resultado de la predicción | Puntos |
|---|---|
| 🎯 Marcador exacto | 3 |
| ✅ Acierta el ganador (o empate), falla el marcador | 1 |
| ❌ Falla el ganador | 0 |

## 🌐 Endpoints

```
POST   /apostadores
GET    /apostadores
GET    /apostadores/{id}
PUT    /apostadores/{id}
DELETE /apostadores/{id}

POST   /partidos
GET    /partidos
GET    /partidos/{id}
PUT    /partidos/{id}
DELETE /partidos/{id}
POST   /partidos/{id}/finalizar

POST   /predicciones
GET    /predicciones
GET    /predicciones/{id}
PUT    /predicciones/{id}
DELETE /predicciones/{id}
```

### 🔍 Método QUERY

Además del CRUD estándar, la API implementa el verbo HTTP **QUERY** real
(no un `GET` disfrazado) para lecturas compuestas:

```
QUERY /query/apostadores/{id}/predicciones
QUERY /query/partidos/{id}/predicciones
QUERY /query/apostadores/{id}/estadisticas
QUERY /query/apostadores/ranking
QUERY /query/partidos/finalizados
QUERY /query/partidos?deporte=...&liga=...
```

Como algunas redes (incluida la de Render, verificado con evidencia — ver
[`docs/pruebas.md`](docs/pruebas.md)) bloquean métodos HTTP no estándar en
su capa de borde, estos mismos endpoints también aceptan `POST` con el
header `X-HTTP-Method-Override: QUERY` como mecanismo de compatibilidad,
sin que el verbo QUERY real deje de existir en el código.

## 🐘 PostgreSQL y Alembic

Persistencia real en PostgreSQL — no se usa `Base.metadata.create_all()`
como mecanismo de creación de tablas en ningún ambiente; todo el esquema se
gestiona con migraciones de Alembic (`migrations/versions/`).

## 🐳 Docker

```bash
docker compose up --build
```

Levanta la API y PostgreSQL juntos, aplica las migraciones automáticamente,
y deja la API disponible en `http://localhost:8000`. Detalle completo en
[`docs/docker.md`](docs/docker.md).

## ⚙️ Instalación y ejecución local

**Con Docker (recomendado):**
```bash
git clone https://github.com/MarianaPineda0/StatsNostra.git
cd StatsNostra
cp .env.example .env
docker compose up --build
```

**Sin Docker (entorno virtual local):**
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt
docker compose up -d db         # solo la base de datos
alembic upgrade head
uvicorn app.main:app --reload
```

- 📘 Swagger UI: http://localhost:8000/docs
- 📕 ReDoc: http://localhost:8000/redoc

## 🔐 Variables de entorno

Ver [`.env.example`](.env.example) para la lista completa. `.env` nunca se
versiona (está en `.gitignore`); solo se versiona `.env.example` con
nombres de variables, sin valores reales.

## 🧪 Testing y cobertura

```bash
pytest -v
pytest --cov=app --cov-report=term-missing
pytest --cov=app --cov-fail-under=60    # gate de Pruebas
pytest --cov=app --cov-fail-under=85    # gate de Producción
```

43 pruebas automatizadas, corriendo contra PostgreSQL real (no mocks), con
**97% de cobertura**. Detalle completo en [`docs/pruebas.md`](docs/pruebas.md).

## 🚀 CI/CD

Dos pipelines independientes en GitHub Actions:

| Pipeline | Rama | Cobertura mínima |
|---|---|---|
| ⚙️ `.github/workflows/pruebas.yml` | `develop` | ≥ 60% |
| ⚙️ `.github/workflows/produccion.yml` | `main` | ≥ 85% |

Cada uno: build → PostgreSQL efímero de CI → migraciones → pruebas +
quality gate → lint → build de imagen Docker → despliegue a Render (solo si
todo lo anterior pasa). Ver [`docs/ci-cd.md`](docs/ci-cd.md) para el
detalle y la evidencia de que un test fallido bloquea el despliegue.

## ☁️ Ambientes (Render)

Dos Web Services independientes, cada uno con su propia base de datos
PostgreSQL (aisladas entre sí: `CONNECT` revocado de `PUBLIC`, un rol de
BD distinto por ambiente):

| Ambiente | Rama | Cobertura mínima | URL |
|---|---|---|---|
| 🟢 Pruebas | `develop` | ≥ 60% | [statsnostra-pruebas.onrender.com](https://statsnostra-pruebas.onrender.com) |
| 🔵 Producción | `main` | ≥ 85% | [statsnostra-produccion.onrender.com](https://statsnostra-produccion.onrender.com) |

Detalle completo de la infraestructura en [`docs/render.md`](docs/render.md).

## 📚 Documentación adicional

- 🏗️ [`docs/arquitectura.md`](docs/arquitectura.md)
- 🐳 [`docs/docker.md`](docs/docker.md)
- 🚀 [`docs/ci-cd.md`](docs/ci-cd.md)
- ☁️ [`docs/render.md`](docs/render.md)
- 🧪 [`docs/pruebas.md`](docs/pruebas.md)
