#!/usr/bin/env python3
"""
Railway'den Coolify'a Database Migration
Tüm verileri kopyalar
"""

import os
import sys
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker

print("=" * 70)
print("🚀 RAILWAY → COOLIFY DATABASE MIGRATION")
print("=" * 70)

# Source: Railway Database
RAILWAY_URL = 'postgresql://postgres:kJQQiRoGKGgWRPWGsRrSdKRoMogEVAGy@postgres.railway.internal:5432/railway'

# Target: Coolify Database
COOLIFY_URL = 'postgresql://postgres:518518Erkan@b4oo4wg8kwgw4c8kc4k444c8:5432/minibar_takip'

print("\n📊 Kaynak Database: Railway")
print("📊 Hedef Database: Coolify")
print()

# Engines oluştur
try:
    print("🔌 Railway'e bağlanılıyor...")
    source_engine = create_engine(RAILWAY_URL)
    source_conn = source_engine.connect()
    print("✅ Railway bağlantısı başarılı")
    
    print("🔌 Coolify'a bağlanılıyor...")
    target_engine = create_engine(COOLIFY_URL)
    target_conn = target_engine.connect()
    print("✅ Coolify bağlantısı başarılı")
    
except Exception as e:
    print(f"❌ Bağlantı hatası: {e}")
    sys.exit(1)

# Metadata
source_metadata = MetaData()
source_metadata.reflect(bind=source_engine)

print(f"\n📋 Railway'de {len(source_metadata.tables)} tablo bulundu")

# Tabloları sırala (foreign key sırasına göre)
sorted_tables = source_metadata.sorted_tables

print("\n🔄 Veri kopyalama başlıyor...\n")

# Her tablo için veri kopyala
total_rows = 0
migrated_tables = []

for table in sorted_tables:
    table_name = table.name
    
    try:
        # Kaynak tablodan veri oku
        result = source_conn.execute(table.select())
        rows = result.fetchall()
        
        if len(rows) == 0:
            print(f"⏭️  {table_name}: Boş tablo, atlandı")
            continue
        
        print(f"📦 {table_name}: {len(rows)} kayıt kopyalanıyor...")
        
        # Hedef tabloya veri yaz
        # Önce tabloyu temizle
        target_conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
        
        # Verileri ekle
        for row in rows:
            # Row'u dict'e çevir
            row_dict = dict(row._mapping)
            
            # Insert statement oluştur
            insert_stmt = table.insert().values(**row_dict)
            target_conn.execute(insert_stmt)
        
        target_conn.commit()
        
        total_rows += len(rows)
        migrated_tables.append(table_name)
        print(f"   ✅ {len(rows)} kayıt kopyalandı")
        
    except Exception as e:
        print(f"   ❌ Hata: {e}")
        continue

# Sequence'leri güncelle (auto increment için)
print("\n🔢 Sequence'ler güncelleniyor...")

for table in sorted_tables:
    table_name = table.name
    
    # Primary key kolonunu bul
    pk_columns = [col for col in table.columns if col.primary_key]
    
    if pk_columns and pk_columns[0].autoincrement:
        pk_name = pk_columns[0].name
        
        try:
            # Max ID'yi al
            result = target_conn.execute(text(f"SELECT MAX({pk_name}) FROM {table_name}"))
            max_id = result.scalar()
            
            if max_id:
                # Sequence'i güncelle
                target_conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{table_name}', '{pk_name}'), {max_id})"))
                print(f"   ✅ {table_name}.{pk_name} sequence güncellendi (max: {max_id})")
        except:
            pass

target_conn.commit()

# Bağlantıları kapat
source_conn.close()
target_conn.close()

print("\n" + "=" * 70)
print("✅ MIGRATION TAMAMLANDI!")
print("=" * 70)
print(f"\n📊 Özet:")
print(f"   - Kopyalanan tablo sayısı: {len(migrated_tables)}")
print(f"   - Toplam kayıt sayısı: {total_rows}")
print(f"\n📋 Kopyalanan tablolar:")
for table in migrated_tables:
    print(f"   ✅ {table}")
print()
print("🎉 Artık Coolify database'i Railway verilerinizle dolu!")
print()
