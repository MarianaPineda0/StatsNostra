# ☁️ Render

## 📦 Recursos desplegados

Un solo proyecto de Render ("StatsNostra"), con 3 recursos:

| Recurso | Tipo | Rama | Plan |
|---|---|---|---|
| `statsnostra-pruebas` | Web Service (Docker) | `develop` | Free |
| `statsnostra-produccion` | Web Service (Docker) | `main` | Free |
| `statsnostra-db` | PostgreSQL | — (compartida) | Free |

## 🐘 Por qué una sola instancia de PostgreSQL para los dos ambientes

El plan gratuito de Render permite **una sola instancia de PostgreSQL por
workspace** (verificado en la documentación oficial de Render). Para
cumplir el requisito de "BD distinta" por ambiente sin salir del plan
gratuito, la instancia única contiene **dos bases de datos reales y
completamente aisladas** (no dos esquemas dentro de la misma base — una
base de datos separada es un catálogo distinto en PostgreSQL, con mayor
aislamiento):

- `statsnostra_pruebas`, propiedad del rol `statsnostra_pruebas`
- `statsnostra_produccion`, propiedad del rol `statsnostra_produccion`

Cada rol tiene su propia contraseña, y **`CONNECT` fue revocado de
`PUBLIC`** en ambas bases — por defecto PostgreSQL otorga permiso de
conexión a todos los roles, así que sin este paso cualquier rol podría
conectarse a la base del otro ambiente. Verificado con evidencia real: un
intento de `statsnostra_produccion` de conectarse a `statsnostra_pruebas`
(o viceversa) es rechazado con `permission denied for database ... User
does not have CONNECT privilege`.

⚠️ **Limitación aceptada conscientemente:** ambas bases comparten la misma
instancia física. Si esa instancia entra en mantenimiento o falla, los dos
ambientes se ven afectados a la vez — el aislamiento es de **datos y
acceso**, no de infraestructura física. Es la mejor alternativa disponible
dentro de las restricciones del plan gratuito de Render (una sola instancia
de Postgres por cuenta); la alternativa hubiera sido usar dos cuentas de
Render distintas, descartada por complejidad operativa adicional.

## 🔐 Variables de entorno por servicio

Cada Web Service tiene su propio `DATABASE_URL` apuntando a su base
correspondiente, configurado directamente en el dashboard de Render (nunca
en el repositorio):

```
statsnostra-pruebas:      DATABASE_URL -> statsnostra_pruebas
statsnostra-produccion:   DATABASE_URL -> statsnostra_produccion
```

## 🚀 Despliegue

Cada Web Service usa el `Dockerfile` del repositorio (Render detecta
automáticamente que es un proyecto Docker) — no un buildpack genérico. El
despliegue se dispara por un **Deploy Hook** (URL privada por servicio),
llamado desde el pipeline de CI/CD correspondiente solo si las pruebas y el
quality gate pasan (ver [`docs/ci-cd.md`](ci-cd.md)).

## 🔍 El método QUERY y Cloudflare

Render pone **Cloudflare** delante de todos sus servicios (verificado con
evidencia: comparando los headers de una respuesta bloqueada contra una
exitosa — la bloqueada no tiene `x-render-origin-server`, lo que confirma
que nunca llegó a la aplicación). Cloudflare rechaza cualquier método HTTP
fuera del conjunto estándar (GET/POST/PUT/DELETE/PATCH/etc.), incluyendo el
verbo `QUERY` que exige la rúbrica — esto se confirmó comparando además
contra un método inventado (`FOOBAR`), que recibe el mismo bloqueo. No es
un problema de la implementación: es una restricción de la plataforma, no
configurable en el plan gratuito.

La solución implementada (ver `app/core/middleware.py`) mantiene el verbo
QUERY real en el código, y además acepta `POST` con el header
`X-HTTP-Method-Override: QUERY` como vía alterna para que la aplicación
pública siga siendo 100% funcional a pesar de la restricción de la red.

## ⏱️ Límites del plan gratuito considerados

- 🌐 **Web Services**: 750 horas de instancia/mes compartidas por workspace,
  se "duermen" tras 15 min de inactividad (~1 min para despertar).
- 🐘 **PostgreSQL**: 1 instancia por workspace, 1 GB de almacenamiento,
  expira 30 días después de creada (con 14 días de gracia).

Ninguno de estos límites afecta la entrega del proyecto dentro del plazo
académico.
