"""
Backup'tan Belirli Tabloları Geri Yükleme
Sadece: oteller, katlar, odalar, kullanicilar, urun_gruplari, urunler
"""

import psycopg2
import os
import re
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Geri yüklenecek tablolar (sıralı - foreign key bağımlılıkları için)
TABLES_TO_RESTORE = [
    'oteller',
    'kullanicilar',
    'kullanici_otel',  # Kullanıcı-otel ilişkisi
    'katlar',
    'odalar',
    'urun_gruplari',
    'urunler'
]

def extract_table_data(backup_file, table_name):
    """Backup dosyasından belirli bir tablonun INSERT komutlarını çıkar"""
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # COPY komutlarını bul (PostgreSQL backup formatı)
        copy_pattern = rf"COPY public\.{table_name}.*?FROM stdin;(.*?)\\\."
        copy_match = re.search(copy_pattern, content, re.DOTALL)
        
        if copy_match:
            logger.info(f"   ✓ {table_name} tablosu için COPY komutu bulundu")
            return copy_match.group(0)
        
        # INSERT komutlarını bul (alternatif format)
        insert_pattern = rf"INSERT INTO (?:public\.)?{table_name}.*?;"
        inserts = re.findall(insert_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if inserts:
            logger.info(f"   ✓ {table_name} tablosu için {len(inserts)} INSERT komutu bulundu")
            return '\n'.join(inserts)
        
        logger.warning(f"   ⚠ {table_name} tablosu için veri bulunamadı")
        return None
        
    except Exception as e:
        logger.error(f"   ❌ {table_name} veri çıkarma hatası: {e}")
        return None

def restore_table_data(cursor, table_name, sql_data):
    """Tablo verilerini geri yükle"""
    try:
        if not sql_data:
            return False
        
        # COPY formatı mı kontrol et
        if 'COPY' in sql_data and 'FROM stdin' in sql_data:
            # COPY komutunu satır satır parse et
            lines = sql_data.split('\n')
            copy_header = lines[0]  # COPY public.table_name ...
            
            # Sütun isimlerini çıkar
            match = re.search(r'COPY public\.\w+ \((.*?)\)', copy_header)
            if not match:
                logger.error(f"   ❌ COPY header parse edilemedi")
                return False
            
            columns = match.group(1)
            
            # Veri satırlarını topla (FROM stdin ile \\. arası)
            data_lines = []
            in_data = False
            for line in lines[1:]:
                if 'FROM stdin' in line:
                    in_data = True
                    continue
                if line.strip() == '\\.':
                    break
                if in_data and line.strip():
                    data_lines.append(line)
            
            if not data_lines:
                logger.warning(f"   ⚠ Veri satırı bulunamadı")
                return False
            
            # COPY komutunu çalıştır - StringIO kullan
            from io import StringIO
            data_io = StringIO('\n'.join(data_lines) + '\n')
            copy_sql = f"COPY {table_name} ({columns}) FROM stdin"
            cursor.copy_expert(copy_sql, data_io)
            
        else:
            # INSERT komutlarını çalıştır
            cursor.execute(sql_data)
        
        # Kaç satır eklendi?
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        logger.info(f"   ✓ {table_name}: {count} kayıt yüklendi")
        
        return True
        
    except Exception as e:
        logger.error(f"   ❌ {table_name} yükleme hatası: {e}")
        import traceback
        traceback.print_exc()
        return False

def restore_specific_tables(backup_file):
    """Belirli tabloları backup'tan geri yükle"""
    try:
        db_url = os.getenv('DATABASE_URL')
        
        logger.info(f"📂 Backup dosyası: {backup_file}")
        logger.info(f"📋 Yüklenecek tablolar: {', '.join(TABLES_TO_RESTORE)}")
        logger.info("")
        
        # PostgreSQL bağlantısı
        conn = psycopg2.connect(db_url)
        conn.autocommit = False  # Transaction kullan
        cursor = conn.cursor()
        
        success_count = 0
        
        for table_name in TABLES_TO_RESTORE:
            logger.info(f"🔄 {table_name} tablosu işleniyor...")
            
            # Backup'tan veriyi çıkar
            sql_data = extract_table_data(backup_file, table_name)
            
            if sql_data:
                # Mevcut verileri temizle
                try:
                    cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE")
                    logger.info(f"   ✓ Mevcut veriler temizlendi")
                except Exception as e:
                    logger.warning(f"   ⚠ Temizleme hatası: {e}")
                
                # Yeni verileri yükle
                if restore_table_data(cursor, table_name, sql_data):
                    success_count += 1
                else:
                    logger.warning(f"   ⚠ {table_name} yüklenemedi, devam ediliyor...")
            
            logger.info("")
        
        # Transaction'ı commit et
        if success_count > 0:
            conn.commit()
            logger.info(f"✅ {success_count}/{len(TABLES_TO_RESTORE)} tablo başarıyla yüklendi!")
        else:
            conn.rollback()
            logger.error("❌ Hiçbir tablo yüklenemedi!")
        
        cursor.close()
        conn.close()
        
        return success_count > 0
        
    except Exception as e:
        logger.error(f"❌ Genel hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    backup_file = r'D:\minibartakip2cool\backups\backup_20251112_210802_6d6481c2.sql'
    
    print("=" * 60)
    print("🏨 OTEL MİNİBAR TAKİP SİSTEMİ")
    print("   BELİRLİ TABLOLARI GERİ YÜKLEME")
    print("=" * 60)
    print()
    print(f"📂 Backup: {os.path.basename(backup_file)}")
    print(f"📋 Tablolar: {', '.join(TABLES_TO_RESTORE)}")
    print()
    print("⚠️  UYARI: Bu tablolardaki mevcut veriler silinecek!")
    print()
    
    confirm = input("Devam etmek istiyor musun? (EVET yazarak onayla): ")
    
    if confirm.strip().upper() == "EVET":
        print()
        success = restore_specific_tables(backup_file)
        
        if success:
            print()
            print("=" * 60)
            print("✅ İşlem tamamlandı!")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print("❌ İşlem başarısız!")
            print("=" * 60)
    else:
        print()
        print("❌ İşlem iptal edildi.")
