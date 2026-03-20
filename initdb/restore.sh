#!/bin/bash
set -e

# Eğer veritabanı boşsa (tablo yoksa) yedeği yükle
TABLE_COUNT=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")

if [ "$TABLE_COUNT" -lt 5 ]; then
    echo "=== Veritabani bos, yedek yukleniyor... ==="
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < /docker-entrypoint-initdb.d/restore.sql
    echo "=== Yedek yukleme tamamlandi ==="
else
    echo "=== Veritabani zaten dolu ($TABLE_COUNT tablo), yedek atlanıyor ==="
fi
