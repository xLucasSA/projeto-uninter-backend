#!/bin/sh
# Shell em vez de .sql porque as senhas dos roles vêm de variáveis de ambiente.
# O entrypoint do Postgres só executa este script com o volume de dados vazio.
set -e

: "${BACKOFFICE_DB_PASSWORD:?defina BACKOFFICE_DB_PASSWORD no .env}"
: "${API_DB_PASSWORD:?defina API_DB_PASSWORD no .env}"
: "${DEBEZIUM_DB_PASSWORD:?defina DEBEZIUM_DB_PASSWORD no .env}"

executar_sql() {
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --no-password "$@"
}

criar_roles() {
  executar_sql --dbname "$POSTGRES_DB" \
    -v backoffice_password="$BACKOFFICE_DB_PASSWORD" \
    -v api_password="$API_DB_PASSWORD" \
    -v debezium_password="$DEBEZIUM_DB_PASSWORD" <<'SQL'
CREATE ROLE backoffice_app LOGIN PASSWORD :'backoffice_password';
CREATE ROLE api_app LOGIN PASSWORD :'api_password';
CREATE ROLE debezium LOGIN REPLICATION PASSWORD :'debezium_password';
SQL
}

configurar_schemas() {
  executar_sql --dbname "$1" <<'SQL'
CREATE SCHEMA catalogo AUTHORIZATION backoffice_app;
CREATE SCHEMA vendas AUTHORIZATION api_app;
GRANT USAGE ON SCHEMA catalogo TO api_app, debezium;
GRANT USAGE ON SCHEMA vendas TO debezium;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
SQL
}

criar_roles
configurar_schemas "$POSTGRES_DB"
