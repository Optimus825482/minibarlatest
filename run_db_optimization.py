"""
Database Optimizasyon CLI Script
Komut satırından database optimizasyonu çalıştırma

Erkan için - CLI Database Optimization Tool

Kullanım:
    python run_db_optimization.py --check-health
    python run_db_optimization.py --check-indexes
    python run_db_optimization.py --create-indexes
    python run_db_optimization.py --optimize-tables
    python run_db_optimization.py --full-optimization
    python run_db_optimization.py --analyze-performance
"""

import sys
import argparse
from app import app, db
from utils.db_optimization import DatabaseOptimizer
import json


def print_json(data):
    """JSON verisini güzel formatta yazdır"""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def check_health():
    """Veritabanı sağlık kontrolü"""
    print("\n🔍 Veritabanı Sağlık Kontrolü...")
    print("-" * 50)
    
    with app.app_context():
        result = DatabaseOptimizer.check_database_health()
        
        if result['status'] == 'healthy':
            print("✅ Veritabanı Sağlıklı")
            print(f"   Aktif Bağlantı: {result['active_connections']}")
            print(f"   Database Boyutu: {result['database_size']}")
            print(f"   Cache Hit Ratio: {result['cache_hit_ratio']}%")
            print(f"   Deadlock Sayısı: {result['deadlocks']}")
        else:
            print("❌ Veritabanı Sağlıksız")
            print(f"   Hata: {result.get('error', 'Bilinmeyen hata')}")


def check_indexes():
    """Eksik index'leri kontrol et"""
    print("\n🔍 Index Kontrolü...")
    print("-" * 50)
    
    with app.app_context():
        result = DatabaseOptimizer.check_missing_indexes()
        
        if result['status'] == 'success':
            if result['missing_count'] == 0:
                print("✅ Tüm gerekli index'ler mevcut!")
            else:
                print(f"⚠️  {result['missing_count']} eksik index tespit edildi:\n")
                
                for idx in result['missing_indexes']:
                    print(f"   Tablo: {idx['table']}")
                    print(f"   Index: {idx['index_name']}")
                    print(f"   Kolonlar: {', '.join(idx['columns'])}")
                    print(f"   SQL: {idx['sql']}")
                    print()
        else:
            print(f"❌ Hata: {result['message']}")


def create_indexes():
    """Eksik index'leri oluştur"""
    print("\n🔨 Index Oluşturma...")
    print("-" * 50)
    
    with app.app_context():
        result = DatabaseOptimizer.create_missing_indexes()
        
        if result['status'] == 'success':
            if result['created_count'] > 0:
                print(f"✅ {result['created_count']} index başarıyla oluşturuldu:")
                for idx_name in result['created_indexes']:
                    print(f"   ✓ {idx_name}")
            else:
                print("ℹ️  Oluşturulacak index bulunamadı")
            
            if result['failed_count'] > 0:
                print(f"\n❌ {result['failed_count']} index oluşturulamadı:")
                for failed in result['failed_indexes']:
                    print(f"   ✗ {failed['index']}: {failed['error']}")
        else:
            print(f"❌ Hata: {result['message']}")


def optimize_tables():
    """Tabloları optimize et"""
    print("\n⚡ Tablo Optimizasyonu...")
    print("-" * 50)
    
    with app.app_context():
        result = DatabaseOptimizer.optimize_tables()
        
        if result['status'] == 'success':
            if result['optimized_count'] > 0:
                print(f"✅ {result['optimized_count']} tablo başarıyla optimize edildi:")
                for table in result['optimized_tables']:
                    print(f"   ✓ {table}")
            else:
                print("ℹ️  Optimize edilecek tablo bulunamadı")
            
            if result['failed_count'] > 0:
                print(f"\n❌ {result['failed_count']} tablo optimize edilemedi:")
                for failed in result['failed_tables']:
                    print(f"   ✗ {failed['table']}: {failed['error']}")
        else:
            print(f"❌ Hata: {result['message']}")


def analyze_performance():
    """Query performansını analiz et"""
    print("\n📊 Performans Analizi...")
    print("-" * 50)
    
    with app.app_context():
        result = DatabaseOptimizer.analyze_query_performance()
        
        if result['status'] == 'success':
            # Yavaş Query'ler
            if result['slow_queries']:
                print("\n⚠️  Yavaş Query'ler (Son 24 Saat):")
                for q in result['slow_queries']:
                    print(f"   Endpoint: {q['endpoint']}")
                    print(f"   Ortalama: {q['avg_time']:.2f}s | Max: {q['max_time']:.2f}s | Çağrı: {q['call_count']}")
                    print()
            else:
                print("\n✅ Yavaş query tespit edilmedi")
            
            # En Büyük Tablolar
            if result['table_sizes']:
                print("\n📦 En Büyük Tablolar:")
                for t in result['table_sizes'][:5]:
                    print(f"   {t['table']}: {t['size']}")
            
            # Kullanılmayan Index'ler
            if result['unused_indexes']:
                print(f"\n⚠️  {len(result['unused_indexes'])} Kullanılmayan Index:")
                for idx in result['unused_indexes'][:5]:
                    print(f"   {idx['table']}.{idx['index']}: {idx['size']}")
            else:
                print("\n✅ Kullanılmayan index yok")
        else:
            print(f"❌ Hata: {result['message']}")


def full_optimization():
    """Tam optimizasyon paketi"""
    print("\n🚀 Tam Optimizasyon Başlatılıyor...")
    print("=" * 50)
    
    with app.app_context():
        result = DatabaseOptimizer.run_full_optimization()
        
        if result['status'] == 'success':
            results = result['results']
            
            # Sağlık Kontrolü
            print("\n1️⃣  Sağlık Kontrolü:")
            health = results['health_check']
            if health['status'] == 'healthy':
                print(f"   ✅ Sağlıklı - Cache Hit: {health['cache_hit_ratio']}%")
            else:
                print(f"   ❌ Sağlıksız")
            
            # Index Kontrolü
            print("\n2️⃣  Index Kontrolü:")
            indexes = results['missing_indexes']
            print(f"   {indexes['missing_count']} eksik index tespit edildi")
            
            # Index Oluşturma
            if 'index_creation' in results:
                creation = results['index_creation']
                print(f"   ✅ {creation['created_count']} index oluşturuldu")
            
            # Tablo Optimizasyonu
            print("\n3️⃣  Tablo Optimizasyonu:")
            tables = results['table_optimization']
            print(f"   ✅ {tables['optimized_count']} tablo optimize edildi")
            
            # Connection Pool
            print("\n4️⃣  Connection Pool:")
            pool = results['connection_pool']
            print(f"   Pool Size: {pool['pool_size']}")
            print(f"   Checked Out: {pool['checked_out']}")
            print(f"   Total: {pool['total_connections']}")
            
            print("\n" + "=" * 50)
            print("✅ Tam Optimizasyon Tamamlandı!")
        else:
            print(f"❌ Hata: {result['message']}")


def main():
    """Ana fonksiyon"""
    parser = argparse.ArgumentParser(
        description='Database Optimizasyon CLI Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python run_db_optimization.py --check-health
  python run_db_optimization.py --check-indexes
  python run_db_optimization.py --create-indexes
  python run_db_optimization.py --optimize-tables
  python run_db_optimization.py --full-optimization
  python run_db_optimization.py --analyze-performance
        """
    )
    
    parser.add_argument('--check-health', action='store_true',
                       help='Veritabanı sağlık kontrolü')
    parser.add_argument('--check-indexes', action='store_true',
                       help='Eksik index kontrolü')
    parser.add_argument('--create-indexes', action='store_true',
                       help='Eksik index\'leri oluştur')
    parser.add_argument('--optimize-tables', action='store_true',
                       help='Tabloları optimize et (ANALYZE)')
    parser.add_argument('--full-optimization', action='store_true',
                       help='Tam optimizasyon paketi')
    parser.add_argument('--analyze-performance', action='store_true',
                       help='Query performans analizi')
    
    args = parser.parse_args()
    
    # Hiç argüman verilmemişse help göster
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    try:
        if args.check_health:
            check_health()
        
        if args.check_indexes:
            check_indexes()
        
        if args.create_indexes:
            create_indexes()
        
        if args.optimize_tables:
            optimize_tables()
        
        if args.analyze_performance:
            analyze_performance()
        
        if args.full_optimization:
            full_optimization()
        
        print("\n✅ İşlem tamamlandı!\n")
        
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
