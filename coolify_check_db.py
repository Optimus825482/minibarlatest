#!/usr/bin/env python3
"""
Coolify PostgreSQL Veritabanı Kontrol
Kullanım: python coolify_check_db.py
"""

import os
import psycopg2
from psycopg2 import sql

# Coolify PostgreSQL bağlantı bilgileri
DB_CONFIG = {
    'host': 'b4oo4wg8kwgw4c8kc4k444c8',
    'port': '5432',
    'user': 'postgres',
    'password': '518518Erkan',
    'database': 'minibar_takip'
}

def list_tables():
    """Tabloları listele ve kayıt sayılarını göster"""
    try:
        print("=" * 70)
        print("📊 COOLIFY POSTGRESQL VERİTABANI KONTROL")
        print("=" * 70)
        print()
        
        # Bağlan
        print("🔌 Veritabanına bağlanılıyor...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Tabloları getir
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        
        print(f"✅ Bağlantı başarılı! {len(tables)} tablo bulundu.\n")
        print(f"{'Tablo Adı':<35} {'Kayıt Sayısı':>15}")
        print("-" * 70)
        
        total_records = 0
        
        for (table_name,) in tables:
            try:
                # Kayıt sayısını al
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
                    sql.Identifier(table_name)
                ))
                count = cur.fetchone()[0]
                total_records += count
                
                # Renk kodu (kayıt sayısına göre)
                if count == 0:
                    status = "⚪"
                elif count < 10:
                    status = "🟡"
                elif count < 100:
                    status = "🟢"
                else:
                    status = "🔵"
                
                print(f"{status} {table_name:<33} {count:>15,}")
                
            except Exception as e:
                print(f"❌ {table_name:<33} {'Hata':>15}")
        
        print("-" * 70)
        print(f"{'TOPLAM':<35} {total_records:>15,}")
        print()
        
        # Veritabanı boyutu
        cur.execute("""
            SELECT pg_size_pretty(pg_database_size(current_database()))
        """)
        db_size = cur.fetchone()[0]
        print(f"💾 Veritabanı Boyutu: {db_size}")
        
        cur.close()
        conn.close()
        
        print()
        print("=" * 70)
        print("✅ Kontrol tamamlandı!")
        print("=" * 70)
        
    except psycopg2.Error as e:
        print(f"\n❌ Veritabanı hatası: {e}")
        print(f"   Kod: {e.pgcode}")
        print(f"   Detay: {e.pgerror}")
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")

if __name__ == '__main__':
    list_tables()
