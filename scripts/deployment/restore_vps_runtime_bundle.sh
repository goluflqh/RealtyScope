#!/usr/bin/env bash
set -euo pipefail

compose_file="${COMPOSE_FILE:-docker-compose.prod.yml}"
env_file="${ENV_FILE:-.env}"
db_dump="${1:-}"
model_archive="${2:-}"

if [ -z "$db_dump" ]; then
  db_dump="$(ls -1t realtyscope-db-*.dump 2>/dev/null | head -n 1 || true)"
fi
if [ -z "$model_archive" ]; then
  model_archive="$(ls -1t realtyscope-model-artifacts-*.tar.gz 2>/dev/null | head -n 1 || true)"
fi

if [ ! -f "$compose_file" ]; then
  echo "Missing Compose file: $compose_file" >&2
  exit 1
fi
if [ ! -f "$env_file" ]; then
  echo "Missing env file: $env_file" >&2
  exit 1
fi
if [ ! -f "$db_dump" ]; then
  echo "Missing DB dump. Expected realtyscope-db-*.dump or pass path as first argument." >&2
  exit 1
fi
if [ ! -f "$model_archive" ]; then
  echo "Missing model archive. Expected realtyscope-model-artifacts-*.tar.gz or pass path as second argument." >&2
  exit 1
fi
if [ ! -f "data/external/moscow_district_boundaries.geojson" ]; then
  echo "Missing tracked boundary file: data/external/moscow_district_boundaries.geojson" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$env_file"
set +a

postgres_user="${POSTGRES_USER:-realtyscope}"
postgres_db="${POSTGRES_DB:-realtyscope}"
app_domain="${APP_DOMAIN:-realtyscope.bond}"
api_domain="${API_DOMAIN:-api.realtyscope.bond}"

echo "Using DB dump: $db_dump"
echo "Using model archive: $model_archive"

docker compose -f "$compose_file" --env-file "$env_file" up -d db redis mlflow
docker compose -f "$compose_file" --env-file "$env_file" stop api streamlit caddy >/dev/null 2>&1 || true

docker compose -f "$compose_file" --env-file "$env_file" exec -T db dropdb -U "$postgres_user" --force --if-exists "$postgres_db"
docker compose -f "$compose_file" --env-file "$env_file" exec -T db createdb -U "$postgres_user" "$postgres_db"
cat "$db_dump" | docker compose -f "$compose_file" --env-file "$env_file" exec -T db pg_restore -U "$postgres_user" -d "$postgres_db" --no-owner --no-acl

docker run --rm \
  -v realtyscope_model_artifacts:/models \
  -v "$PWD":/transfer:ro \
  alpine sh -c "rm -rf /models/* && tar -xzf /transfer/$model_archive -C /models"

docker compose -f "$compose_file" --env-file "$env_file" up -d api streamlit caddy
docker compose -f "$compose_file" --env-file "$env_file" ps

docker compose -f "$compose_file" --env-file "$env_file" exec -T streamlit test -f /app/data/external/moscow_district_boundaries.geojson
docker compose -f "$compose_file" --env-file "$env_file" exec -T streamlit test -f /app/data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib

curl -fsS "https://${api_domain}/health"
echo
curl -fsS "https://${api_domain}/monitoring/status" >/dev/null
curl -fsS "https://${api_domain}/data?limit=1" >/dev/null
curl -fsSI "https://${app_domain}" >/dev/null

echo "Runtime restore and smoke checks completed."
