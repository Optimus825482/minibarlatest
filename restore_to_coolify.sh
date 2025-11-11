#!/bin/bash
# Coolify'a SQL Restore Script

echo "=========================================="
echo "📥 Coolify Database Restore"
echo "=========================================="

# Backup dosyası
BACKUP_FILE="railway_backup.sql"

# Coolify Database URL
DATABASE_URL="postgresql://postgres:518518Erkan@b4oo4wg8kwgw4c8kc4k444c8:5432/minibar_takip"

# Dosya kontrolü
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Hata: $BACKUP_FILE bulunamadı!"
    echo ""
    echo "Önce Railway'den backup alın:"
    echo "  python backup_railway_python.py"
    exit 1
fi

echo ""
echo "📁 Backup dosyası: $BACKUP_FILE"
echo "📊 Boyut: $(du -h $BACKUP_FILE | cut -f1)"
echo ""
echo "⚠️  UYARI: Mevcut veriler silinecek!"
read -p "Devam etmek istiyor musunuz? (E/H): " CONFIRM

if [ "$CONFIRM" != "E" ] && [ "$CONFIRM" != "e" ]; then
    echo "❌ İşlem iptal edildi"
    exit 0
fi

echo ""
echo "🔄 Restore başlıyor..."

# Restore
cat "$BACKUP_FILE" | psql "$DATABASE_URL"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Restore başarılı!"
    echo "=========================================="
    echo ""
    echo "🎉 Coolify database'i Railway verileriyle dolu!"
    echo ""
else
    echo ""
    echo "❌ Restore başarısız!"
    exit 1
fi
