#!/bin/bash
# Coolify PostgreSQL İstatistikler
# Container ID: 1c40bfcee1a3

CONTAINER_ID="1c40bfcee1a3"

echo "======================================"
echo "📊 COOLIFY POSTGRESQL İSTATİSTİKLER"
echo "======================================"
echo ""

echo "🔹 Veritabanı Bilgileri:"
docker exec -it $CONTAINER_ID psql -U postgres -d minibar_takip -c "
SELECT 
    current_database() as database,
    pg_size_pretty(pg_database_size(current_database())) as size,
    version() as version;
"

echo ""
echo "🔹 Tablo Sayıları:"
docker exec -it $CONTAINER_ID psql -U postgres -d minibar_takip -c "
SELECT 
    COUNT(*) as total_tables
FROM information_schema.tables 
WHERE table_schema = 'public';
"

echo ""
echo "🔹 Kullanıcı İstatistikleri:"
docker exec -it $CONTAINER_ID psql -U postgres -d minibar_takip -c "
SELECT 
    rol,
    COUNT(*) as sayi,
    SUM(CASE WHEN aktif THEN 1 ELSE 0 END) as aktif_sayi
FROM kullanicilar
GROUP BY rol
ORDER BY rol;
"

echo ""
echo "🔹 En Büyük 10 Tablo:"
docker exec -it $CONTAINER_ID psql -U postgres -d minibar_takip -c "
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
"

echo ""
echo "======================================"
echo "✅ Tamamlandı"
echo "======================================"
