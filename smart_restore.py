#!/usr/bin/env python3
"""
Akıllı Database Restore
- Mevcut tabloları kontrol eder
- Eksik tabloları ekler
- Verileri merge eder (çakışma varsa atlar)
"""

import os
import re
from sqlalchemy import create_engine, text, inspect

print("=" * 70)
print("🔄 AKILLI DATABASE RESTORE")
print("=" * 70)

# Coolify Database URL
DATABASE_URL = 'postgresql://postgres:518518Erkan@b4oo4wg8kwgw4c8kc4k444c8:5432/minibar_takip'

# Backup dosyası
BACKUP_FILE = 'railway_backup.sql'

print(f"\n📁 Backup dosyası: {BACKUP_FILE}")

if not os.path.exists(BACKUP_FILE):
    print(f"❌ {BACKUP_FILE} bulunamadı!")
    exit(1)

# Engine oluştur
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

# Mevcut tabloları listele
existing_tables = inspector.get_table_names()
print(f"\n📊 Mevcut tablolar: {len(existing_tables)} adet")

# Backup dosyasını oku
print(f"\n📖 Backup dosyası okunuyor...")

with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
    sql_content = f.read()

# SQL'i satırlara böl
sql_lines = sql_content.split('\n')

print(f"✅ {len(sql_lines)} satır okundu")

# Seçenekler
print("\n" + "=" * 70)
print("RESTORE SEÇENEKLERİ")
print("=" * 70)
print("\n1. 🗑️  Tüm verileri sil ve yeniden yükle (FULL RESTORE)")
print("2. 📦 Sadece eksik tabloları ekle (SAFE RESTORE)")
print("3. 🔄 Verileri merge et (çakışma varsa atla)")
print("4. ❌ İptal")

choice = input("\nSeçiminiz (1-4): ")

with engine.connect() as conn:
    if choice == '1':
        # FULL RESTORE
        print("\n⚠️  UYARI: Tüm veriler silinecek!")
        confirm = input("Emin misiniz? (EVET yazın): ")
        
        if confirm != "EVET":
            print("❌ İşlem iptal edildi")
            exit(0)
        
        print("\n🗑️  Tüm tablolar siliniyor...")
        
        # Tüm tabloları sil
        for table in existing_tables:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"   ✅ {table} silindi")
            except Exception as e:
                print(f"   ⚠️  {table} silinemedi: {e}")
        
        conn.commit()
        
        print("\n📦 Backup yükleniyor...")
        
        # Tüm SQL'i çalıştır
        try:
            conn.execute(text(sql_content))
            conn.commit()
            print("✅ Backup başarıyla yüklendi!")
        except Exception as e:
            print(f"❌ Hata: {e}")
            conn.rollback()
    
    elif choice == '2':
        # SAFE RESTORE - Sadece eksik tablolar
        print("\n📦 Eksik tablolar kontrol ediliyor...")
        
        # CREATE TABLE statement'larını bul
        create_pattern = re.compile(r'CREATE TABLE (\w+)', re.IGNORECASE)
        tables_in_backup = create_pattern.findall(sql_content)
        
        missing_tables = [t for t in tables_in_backup if t not in existing_tables]
        
        if not missing_tables:
            print("✅ Tüm tablolar mevcut, eksik yok!")
        else:
            print(f"\n📋 Eksik tablolar ({len(missing_tables)} adet):")
            for table in missing_tables:
                print(f"   - {table}")
            
            print("\n📦 Eksik tablolar oluşturuluyor...")
            
            # Her satırı işle
            current_table = None
            table_sql = []
            
            for line in sql_lines:
                # CREATE TABLE başlangıcı
                if 'CREATE TABLE' in line.upper():
                    match = create_pattern.search(line)
                    if match:
                        current_table = match.group(1)
                        table_sql = [line]
                elif current_table:
                    table_sql.append(line)
                    
                    # Tablo bitişi
                    if ');' in line:
                        if current_table in missing_tables:
                            try:
                                sql_statement = '\n'.join(table_sql)
                                conn.execute(text(sql_statement))
                                conn.commit()
                                print(f"   ✅ {current_table} oluşturuldu")
                            except Exception as e:
                                print(f"   ⚠️  {current_table} hatası: {e}")
                        
                        current_table = None
                        table_sql = []
            
            print("\n✅ Eksik tablolar eklendi!")
    
    elif choice == '3':
        # MERGE RESTORE
        print("\n🔄 Veriler merge ediliyor...")
        print("⚠️  Bu işlem uzun sürebilir...")
        
        # INSERT statement'larını bul ve çalıştır
        insert_pattern = re.compile(r'INSERT INTO (\w+)', re.IGNORECASE)
        
        success_count = 0
        skip_count = 0
        
        for line in sql_lines:
            if 'INSERT INTO' in line.upper():
                try:
                    conn.execute(text(line))
                    success_count += 1
                    
                    if success_count % 100 == 0:
                        print(f"   📊 {success_count} kayıt eklendi...")
                        conn.commit()
                except Exception as e:
                    skip_count += 1
                    # Çakışma varsa atla
                    continue
        
        conn.commit()
        
        print(f"\n✅ Merge tamamlandı!")
        print(f"   - Eklenen: {success_count}")
        print(f"   - Atlanan: {skip_count}")
    
    else:
        print("❌ İşlem iptal edildi")
        exit(0)

print("\n" + "=" * 70)
print("✅ RESTORE TAMAMLANDI!")
print("=" * 70)
print("\n🎉 Database hazır!")
print("\n📝 Giriş bilgileri:")
print("   URL: http://h8k8wo040wc48gc4k8skwokw.185.9.38.66.sslip.io/login")
print("   Kullanıcı: Mradmin")
print("   Şifre: Mr12141618.")
print()
