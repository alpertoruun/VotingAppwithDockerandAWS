#!/bin/sh
# wait-for-postgres.sh

set -e

until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  >&2 echo "Postgres bekleniyor..."
  sleep 2
done

>&2 echo "Postgres hazır!"
exec "$@"
