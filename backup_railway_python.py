#!/usr/bin/env python3
"""
Railway Database Backup - Pure Python
pg_dump olmadan SQL export
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, MetaData, inspect

print("=" * 60)
print("🗄️  RAILWAY DATABASE BACKUP (Pure Python)")
print("=" * 60)

# Railway Database URL
DATABASE_URL = 'postgresql://postgres:kJQQiRoGKGgWRPWGsRrSdKRoMogEVAGy@shinkansen.proxy.rlwy.net:27699/railway'
# Backup dosya adı
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = f"railway_backup_{timestamp}.sql"

print(f"\n📦 Backup alınıyor...")
print(f"📁 Dosya: {backup_file}")
print()

try:
    # Engine oluştur
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    inspector = inspect(engine)
    
    print(f"✅ Database'e bağlanıldı")
    print(f"📊 {len(metadata.tables)} tablo bulundu")
    print()
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("-- Railway Database Backup\n")
        f.write(f"-- Date: {datetime.now()}\n")
        f.write(f"-- Tables: {len(metadata.tables)}\n")
        f.write("\n")
        f.write("SET client_encoding = 'UTF8';\n")
        f.write("SET standard_conforming_strings = on;\n")
        f.write("\n")
        
        # Her tablo için
        for table_name in metadata.tables:
            table = metadata.tables[table_name]
            
            print(f"📦 {table_name} export ediliyor...")
            
            # CREATE TABLE
            f.write(f"\n-- Table: {table_name}\n")
            f.write(f"DROP TABLE IF EXISTS {table_name} CASCADE;\n")
            
            # Kolon tanımları
            columns = []
            for col in table.columns:
                col_def = f"{col.name} {col.type}"
                if col.primary_key:
                    col_def += " PRIMARY KEY"
                if not col.nullable:
                    col_def += " NOT NULL"
                if col.default is not None:
                    col_def += f" DEFAULT {col.default}"
                columns.append(col_def)
            
            f.write(f"CREATE TABLE {table_name} (\n")
            f.write(",\n".join(f"    {col}" for col in columns))
            f.write("\n);\n\n")
            
            # INSERT statements
            with engine.connect() as conn:
                result = conn.execute(table.select())
                rows = result.fetchall()
                
                if rows:
                    f.write(f"-- Data for {table_name} ({len(rows)} rows)\n")
                    
                    for row in rows:
                        values = []
                        for val in row:
                            if val is None:
                                values.append("NULL")
                            elif isinstance(val, str):
                                # Escape single quotes
                                escaped = val.replace("'", "''")
                                values.append(f"'{escaped}'")
                            elif isinstance(val, (int, float)):
                                values.append(str(val))
                            elif isinstance(val, bool):
                                values.append("TRUE" if val else "FALSE")
                            else:
                                values.append(f"'{str(val)}'")
                        
                        f.write(f"INSERT INTO {table_name} VALUES ({', '.join(values)});\n")
                    
                    f.write("\n")
                    print(f"   ✅ {len(rows)} kayıt export edildi")
                else:
                    print(f"   ⏭️  Boş tablo")
        
        # Footer
        f.write("\n-- Backup completed\n")
    
    # Dosya boyutu
    size = os.path.getsize(backup_file)
    size_mb = size / (1024 * 1024)
    
    print()
    print("=" * 60)
    print("✅ BACKUP TAMAMLANDI!")
    print("=" * 60)
    print(f"📊 Boyut: {size_mb:.2f} MB ({size:,} bytes)")
    print(f"📁 Konum: {os.path.abspath(backup_file)}")
    print()
    print("📥 Sonraki Adım:")
    print("   1. Bu dosyayı local'e indir")
    print("   2. Coolify'a yükle:")
    print(f"      cat {backup_file} | docker exec -i [postgres-container] psql -U postgres -d minibar_takip")
    print()
    
except Exception as e:
    print(f"❌ Hata: {e}")
    import traceback
    traceback.print_exc()
