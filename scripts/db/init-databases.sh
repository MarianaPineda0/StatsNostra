#!/usr/bin/env bash
set -e

# Crea un rol de conexion dedicado por ambiente y una base de datos propia
# para cada uno (no un esquema compartido), de forma que Pruebas y
# Produccion queden en catalogos completamente distintos dentro de la
# misma instancia.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE statsnostra_pruebas LOGIN PASSWORD '$PRUEBAS_DB_PASSWORD';
    CREATE ROLE statsnostra_produccion LOGIN PASSWORD '$PRODUCCION_DB_PASSWORD';
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "CREATE DATABASE statsnostra_pruebas OWNER statsnostra_pruebas;"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "CREATE DATABASE statsnostra_produccion OWNER statsnostra_produccion;"

# Por defecto Postgres otorga CONNECT a PUBLIC sobre toda BD nueva: se revoca
# para que cada ambiente sea accesible unicamente por su propio rol.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    REVOKE CONNECT ON DATABASE statsnostra_pruebas FROM PUBLIC;
    GRANT CONNECT ON DATABASE statsnostra_pruebas TO statsnostra_pruebas;

    REVOKE CONNECT ON DATABASE statsnostra_produccion FROM PUBLIC;
    GRANT CONNECT ON DATABASE statsnostra_produccion TO statsnostra_produccion;
EOSQL
