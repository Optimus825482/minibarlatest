#!/bin/bash

echo ""
echo "============================================================"
echo "⚡ OTEL MİNİBAR TAKİP SİSTEMİ - HIZLI KURULUM"
echo "============================================================"
echo ""
echo "Bu script sıfırdan sistem kurulumu yapar:"
echo "  1. Veritabanı ve tabloları oluşturur"
echo "  2. Varsayılan admin oluşturur"
echo "  3. Örnek veriler ekler (opsiyonel)"
echo ""
echo "Varsayılan Giriş:"
echo "  Kullanıcı: admin"
echo "  Şifre: admin123"
echo ""
read -p "Devam edilsin mi? (E/H): " choice

if [[ "$choice" != "E" && "$choice" != "e" ]]; then
    echo ""
    echo "❌ İşlem iptal edildi"
    exit 1
fi

python3 quick_setup.py

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✅ KURULUM BAŞARILI!"
    echo "============================================================"
    echo ""
    echo "Uygulamayı başlatmak için:"
    echo "  python3 app.py"
    echo ""
    echo "veya"
    echo "  ./railway_start.sh"
    echo ""
else
    echo ""
    echo "============================================================"
    echo "❌ KURULUM BAŞARISIZ!"
    echo "============================================================"
    echo ""
    echo "Lütfen hata mesajlarını kontrol edin."
    echo ""
fi
