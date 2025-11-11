#!/bin/bash
# Railway Database Backup Script
# SQL formatında backup alır

echo "=========================================="
echo "🗄️  Railway Database Backup"
echo "=========================================="

# Railway Database URL
DATABASE_URL="postgresql://postgres:kJQQiRoGKGgWRPWGsRrSdKRoMogEVAGy@postgres.railway.internal:5432/railway"

# Backup dosya adı (tarih ile)
BACKUP_FILE="railway_backup_$(date +%Y%m%d_%H%M%S).sql"

echo ""
echo "📦 Backup alınıyor..."
echo "📁 Dosya: $BACKUP_FILE"
echo ""

# pg_dump ile backup al
pg_dump "$DATABASE_URL" > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    # Dosya boyutunu göster
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    
    echo "✅ Backup başarılı!"
    echo "📊 Boyut: $SIZE"
    echo "📁 Konum: $(pwd)/$BACKUP_FILE"
    echo ""
    echo "=========================================="
    echo "📥 Dosyayı indirmek için:"
    echo "   Railway Dashboard → Deployments → Files"
    echo "   veya"
    echo "   cat $BACKUP_FILE"
    echo "=========================================="
else
    echo "❌ Backup başarısız!"
    exit 1
fi
