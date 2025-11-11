#!/bin/bash
# Coolify Kullanıcı Kontrolü
# Container ID: 1c40bfcee1a3

CONTAINER_ID="1c40bfcee1a3"

echo "======================================"
echo "👥 COOLIFY KULLANICI KONTROLÜ"
echo "======================================"
echo ""

echo "🔹 Tüm Kullanıcılar:"
docker exec -it $CONTAINER_ID psql -U postgres -d minibar_takip -c "
SELECT 
    id,
    kullanici_adi,
    ad || ' ' || soyad as ad_soyad,
    rol,
    CASE WHEN aktif THEN '✅' ELSE '❌' END as durum,
    to_char(olusturma_tarihi, 'DD.MM.YYYY HH24:MI') as olusturma
FROM kullanicilar
ORDER BY id;
"

echo ""
echo "======================================"
echo "✅ Tamamlandı"
echo "======================================"
