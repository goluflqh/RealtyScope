#!/usr/bin/env bash
set -euo pipefail

output_dir="${1:-../realtyscope-vps-transfer}"
stamp="${RUNTIME_BUNDLE_STAMP:-$(date +%Y%m%d)}"
db_container="${LOCAL_DB_CONTAINER:-realtyscope-db-1}"
db_user="${POSTGRES_USER:-realtyscope}"
db_name="${POSTGRES_DB:-realtyscope}"

mkdir -p "$output_dir"

db_dump="$output_dir/realtyscope-db-${stamp}.dump"
model_archive="$output_dir/realtyscope-model-artifacts-${stamp}.tar.gz"

if ! docker ps --format '{{.Names}}' | grep -qx "$db_container"; then
  echo "Local PostgreSQL container '$db_container' is not running." >&2
  exit 1
fi

if [ ! -d "data/processed/models/phase5" ]; then
  echo "Missing local model artifacts directory: data/processed/models/phase5" >&2
  exit 1
fi

docker exec "$db_container" pg_dump -U "$db_user" -d "$db_name" -Fc > "$db_dump"
tar -czf "$model_archive" -C data/processed/models phase5

printf 'Created runtime bundle:\n'
ls -lh "$db_dump" "$model_archive"
