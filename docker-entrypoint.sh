#!/bin/sh
set -e

# Wait for Postgres to become available
DATABASE_URL=${DATABASE_URL:-postgresql://infracrawl:infracrawl_pass@db:5432/infracrawl_db}

echo "Waiting for Postgres..."
# try a simple psql check if available
until pg_isready -d "$DATABASE_URL" >/dev/null 2>&1 || [ "$TRY_PG_BYPASS" = "1" ]; do
  echo "Postgres is unavailable - sleeping"
  sleep 1
done

# Apply base schema if present
if [ -f /app/infracrawl/schema.sql ]; then
  echo "Applying base schema..."
  psql "$DATABASE_URL" -f /app/infracrawl/schema.sql || true
fi

# Apply SQL migrations in migrations/ (ordered by filename)
if [ -d /app/migrations ]; then
  echo "Applying migrations..."
  for f in /app/migrations/*.sql; do
    [ -e "$f" ] || continue
    fname=$(basename "$f")
    # Check if this migration has already been applied
    already=$(psql "$DATABASE_URL" -t -c "SELECT 1 FROM migrations WHERE filename = '$fname' LIMIT 1;" | tr -d '[:space:]' || true)
    if [ "$already" = "1" ]; then
      echo "Skipping already-applied migration $fname"
      continue
    fi
    echo "Applying $f"
    if psql "$DATABASE_URL" -f "$f"; then
      psql "$DATABASE_URL" -c "INSERT INTO migrations (filename) VALUES ('$fname');" || true
    else
      echo "Warning: migration $fname failed (continuing)"
    fi
  done
fi

# Exec the original CMD
exec "$@"
