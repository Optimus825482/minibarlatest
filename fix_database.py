#!/usr/bin/env python3
"""
Database Index Çakışması Düzeltme Script'i
Scheduler başlamadan tabloları oluşturur
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

print("=" * 50)
print("🔧 Database Fix Script Başlatılıyor...")
print("=" * 50)

# Database URL'i al
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL bulunamadı!")
    sys.exit(1)

# postgresql:// formatına çevir
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

print(f"📊 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown'}")

# Engine oluştur (app.py import etmeden)
engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")

print("\n🔍 Mevcut indexler kontrol ediliyor...")

# Problematik indexleri bul ve sil
with engine.connect() as conn:
    # Tüm indexleri listele
    result = conn.execute(text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public'
        AND indexname LIKE 'idx_%'
    """))
    
    indexes = [row[0] for row in result]
    
    if indexes:
        print(f"⚠️  {len(indexes)} adet index bulundu, siliniyor...")
        for idx in indexes:
            try:
                conn.execute(text(f"DROP INDEX IF EXISTS {idx} CASCADE"))
                print(f"   ✅ {idx} silindi")
            except Exception as e:
                print(f"   ⚠️  {idx} silinemedi: {e}")
    else:
        print("✅ Hiç index yok")

print("\n🗑️  Tüm tabloları siliniyor...")

# Tüm tabloları sil
with engine.connect() as conn:
    # Foreign key constraint'leri devre dışı bırak
    conn.execute(text("SET session_replication_role = 'replica'"))
    
    # Tüm tabloları listele
    result = conn.execute(text("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
    """))
    
    tables = [row[0] for row in result]
    
    if tables:
        for table in tables:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"   ✅ {table} silindi")
            except Exception as e:
                print(f"   ⚠️  {table} silinemedi: {e}")
    
    # Foreign key constraint'leri tekrar aktif et
    conn.execute(text("SET session_replication_role = 'origin'"))

print("\n📦 Tabloları yeniden oluşturuluyor...")

# Şimdi models'i import et ve tabloları oluştur
try:
    # SQLAlchemy Base'i import et
    from models import db
    
    # Metadata'dan tabloları oluştur (app context'e gerek yok)
    db.metadata.create_all(bind=engine)
    
    print("✅ Tüm tablolar başarıyla oluşturuldu!")
    
    # Oluşturulan tabloları listele
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n📊 Oluşturulan tablolar ({len(tables)} adet):")
    for table in sorted(tables):
        print(f"   ✅ {table}")
    
    print("\n" + "=" * 50)
    print("🎉 Database başarıyla düzeltildi!")
    print("=" * 50)
    print("\n📝 Sonraki adım:")
    print("   python create_superadmin_only.py")
    print()
    
except Exception as e:
    print(f"\n❌ Hata: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
