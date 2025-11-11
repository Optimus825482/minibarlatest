#!/bin/bash
# PostgreSQL Performans Optimizasyonu
# Coolify Container: c2358aa575ec

CONTAINER_ID="c2358aa575ec"
DB_USER="postgres"
DB_NAME="minibar_takip"

echo "=============================================="
echo "🚀 POSTGRESQL PERFORMANS OPTİMİZASYONU"
echo "=============================================="
echo ""
echo "Container: $CONTAINER_ID"
echo "Database: $DB_NAME"
echo ""

# SQL dosyasını container'a kopyala
echo "📋 SQL script container'a kopyalanıyor..."
docker cp optimize_db_indexes.sql $CONTAINER_ID:/tmp/optimize.sql

# SQL'i çalıştır
echo "⚡ Optimizasyon başlatılıyor..."
echo ""
docker exec -it $CONTAINER_ID psql -U $DB_USER -d $DB_NAME -f /tmp/optimize.sql

# Temizlik
echo ""
echo "🧹 Temizlik yapılıyor..."
docker exec -it $CONTAINER_ID rm /tmp/optimize.sql

echo ""
echo "=============================================="
echo "✅ OPTİMİZASYON TAMAMLANDI!"
echo "=============================================="
echo ""
echo "📊 Sonuçlar yukarıda gösterildi"
echo "🎯 Uygulama performansı artırıldı"
echo ""
