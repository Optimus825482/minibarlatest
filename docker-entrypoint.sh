#!/bin/bash
set -e

echo "=========================================="
echo "DOCKER CONTAINER BAŞLATILIYOR"
echo "=========================================="

# Database bağlantısını bekle (pg_isready ile - app import etmeden)
echo "[1/3] Database bağlantısı kontrol ediliyor..."

# DATABASE_URL'den host ve port parse et
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:]*\):.*|\1|p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')

if [ -z "$DB_HOST" ]; then
    DB_HOST="minibartakip-db"
fi
if [ -z "$DB_PORT" ]; then
    DB_PORT="5432"
fi

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -q 2>/dev/null; then
        echo "✅ Database bağlantısı başarılı!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "⏳ Database bekleniyor... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "❌ Database bağlantısı kurulamadı!"
    exit 1
fi

echo ""
echo "[2/3] Veritabanı tabloları kontrol ediliyor..."
python -c "
from app import app, db
from models import *
from sqlalchemy import text, inspect

with app.app_context():
    try:
        # Onceki hatali index varsa temizle
        with db.engine.connect() as conn:
            for idx in ['idx_dnd_kontrol_zaman', 'idx_dnd_kontrol_kayit', 'idx_dnd_kontrol_personel']:
                conn.execute(text(f'DROP INDEX IF EXISTS {idx}'))
            conn.commit()
        db.create_all()
        print('✅ Veritabanı tabloları hazır!')
    except Exception as e:
        print(f'⚠️  Tablo oluşturma uyarısı: {e}')
        import traceback
        traceback.print_exc()
        print('ℹ️  Devam ediliyor...')
"

echo ""
echo "[3/3] Performance index'leri kontrol ediliyor..."
python -c "
import os, sys
from sqlalchemy import create_engine, text

db_url = os.environ.get('DATABASE_URL', '')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

if not db_url:
    print('⚠️  DATABASE_URL bulunamadı, index adımı atlanıyor.')
    sys.exit(0)

try:
    engine = create_engine(db_url, connect_args={'connect_timeout': 10})
    with engine.connect() as conn:
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_odalar_aktif_oda_no ON odalar (aktif, oda_no)',
            'CREATE INDEX IF NOT EXISTS idx_odalar_kat_id ON odalar (kat_id)',
        ]
        for idx_sql in indexes:
            conn.execute(text(idx_sql))
            print(f'  ✅ {idx_sql.split(\"idx_\")[1].split(\" ON\")[0]}')
        conn.commit()
    print('✅ Performance index kontrolleri tamamlandı!')
    engine.dispose()
except Exception as e:
    print(f'⚠️  Index oluşturma hatası: {e}')
    import traceback
    traceback.print_exc()
    print('ℹ️  Devam ediliyor...')
"

echo ""
echo "=========================================="
echo "✅ HAZIRLIK TAMAMLANDI - UYGULAMA BAŞLIYOR"
echo "=========================================="
echo ""

# Uygulamayı başlat
exec "$@"
