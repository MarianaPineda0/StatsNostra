#!/usr/bin/env bash
set -e

# Crea los esquemas de ambiente y un rol de conexion dedicado por cada uno,
# de forma que Pruebas y Produccion queden aislados dentro de la misma instancia.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS pruebas;
    CREATE SCHEMA IF NOT EXISTS produccion;

    CREATE ROLE statsnostra_pruebas LOGIN PASSWORD '$PRUEBAS_DB_PASSWORD';
    CREATE ROLE statsnostra_produccion LOGIN PASSWORD '$PRODUCCION_DB_PASSWORD';

    ALTER ROLE statsnostra_pruebas SET search_path TO pruebas;
    ALTER ROLE statsnostra_produccion SET search_path TO produccion;

    GRANT ALL PRIVILEGES ON SCHEMA pruebas TO statsnostra_pruebas;
    GRANT ALL PRIVILEGES ON SCHEMA produccion TO statsnostra_produccion;

    ALTER DEFAULT PRIVILEGES FOR ROLE statsnostra_pruebas IN SCHEMA pruebas
        GRANT ALL ON TABLES TO statsnostra_pruebas;
    ALTER DEFAULT PRIVILEGES FOR ROLE statsnostra_produccion IN SCHEMA produccion
        GRANT ALL ON TABLES TO statsnostra_produccion;
EOSQL
