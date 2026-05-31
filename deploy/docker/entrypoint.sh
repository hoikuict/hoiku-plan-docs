#!/bin/sh
set -eu

facility_db_path="${HOIKU_FACILITY_BUNREI_DB_PATH:-}"
seed_db_path="/app/gen_bunnrei/facility.sqlite"

if [ -n "$facility_db_path" ] && [ ! -f "$facility_db_path" ]; then
  mkdir -p "$(dirname "$facility_db_path")"
  if [ -f "$seed_db_path" ]; then
    cp "$seed_db_path" "$facility_db_path"
  fi
fi

exec "$@"
