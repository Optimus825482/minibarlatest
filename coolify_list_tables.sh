#!/bin/bash
# Coolify PostgreSQL Tablo Listeleme
# Kullanım: bash coolify_list_tables.sh

echo "======================================"
echo "📊 COOLIFY POSTGRESQL TABLOLAR"
echo "======================================"
echo ""

# .env.coolify'den bilgileri al
export PGPASSWORD="518518Erkan"
export PGHOST="b4oo4wg8kwgw4c8kc4k444c8"
export PGUSER="postgres"
export PGDATABASE="minibar_takip"
export PGPORT="5432"

# Tabloları listele
psql -h $PGHOST -U $PGUSER -d $PGDATABASE -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
"

echo ""
echo "======================================"
echo "✅ Tamamlandı"
echo "======================================"
