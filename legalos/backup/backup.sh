#!/bin/sh
# Nightly pg_dump → MinIO with 14-day retention.
# Env: PGHOST PGUSER PGPASSWORD PGDATABASE MINIO_ENDPOINT MINIO_ACCESS_KEY
#      MINIO_SECRET_KEY BACKUP_BUCKET BACKUP_INTERVAL_SECONDS BACKUP_RETENTION_DAYS
set -eu

INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
RETENTION="${BACKUP_RETENTION_DAYS:-14}"
BUCKET="${BACKUP_BUCKET:-legalos-backups}"

echo "backup service: every ${INTERVAL}s, retention ${RETENTION}d, bucket ${BUCKET}"

while true; do
  STAMP="$(date -u +%Y%m%d-%H%M%S)"
  echo "[$(date -u)] starting backup ${STAMP}"
  if mc alias set minio "http://${MINIO_ENDPOINT}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" >/dev/null 2>&1; then
    mc mb --ignore-existing "minio/${BUCKET}" >/dev/null 2>&1 || true
    if pg_dump --no-owner --format=custom | gzip | mc pipe "minio/${BUCKET}/${PGDATABASE}-${STAMP}.dump.gz"; then
      echo "[$(date -u)] backup ${STAMP} uploaded"
      mc rm --recursive --force --older-than "${RETENTION}d" "minio/${BUCKET}" >/dev/null 2>&1 || true
    else
      echo "[$(date -u)] ERROR: pg_dump/upload failed" >&2
    fi
  else
    echo "[$(date -u)] ERROR: MinIO unreachable at ${MINIO_ENDPOINT}" >&2
  fi
  sleep "${INTERVAL}"
done
