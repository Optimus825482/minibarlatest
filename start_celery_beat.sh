#!/bin/bash
# Celery Beat Başlatma Script'i (Linux/Mac)
# Periyodik task'ları zamanında çalıştırır (günlük, haftalık, aylık analizler)

echo "========================================"
echo "Celery Beat Başlatılıyor..."
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

# Celery beat'i başlat
echo "Celery beat başlatılıyor..."
echo "Periyodik task'lar:"
echo "- Günlük kar analizi (her gece 00:30)"
echo "- Haftalık trend analizi (her Pazartesi 06:00)"
echo "- Aylık stok devir analizi (her ayın 1'i 07:00)"
echo ""
echo "Çıkış için: Ctrl+C"
echo ""

celery -A celery_app beat --loglevel=info

