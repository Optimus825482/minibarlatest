#!/bin/bash
# Celery Worker Başlatma Script'i (Linux/Mac)
# Fiyatlandırma ve Karlılık Sistemi için asenkron task işleyici

echo "========================================"
echo "Celery Worker Başlatılıyor..."
echo "========================================"
echo ""

# Redis'in çalıştığını kontrol et
echo "Redis bağlantısı kontrol ediliyor..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "[HATA] Redis çalışmıyor! Lütfen Redis'i başlatın."
    echo "Redis başlat: redis-server"
    exit 1
fi
echo "[OK] Redis bağlantısı başarılı"
echo ""

# Celery worker'ı başlat
echo "Celery worker başlatılıyor..."
echo "Çıkış için: Ctrl+C"
echo ""

celery -A celery_app worker --loglevel=info

