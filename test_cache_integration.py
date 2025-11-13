"""
Redis Cache Entegrasyon Test Scripti
Cache sisteminin çalışıp çalışmadığını test eder
"""

import sys
import os
from datetime import datetime, timezone
from decimal import Decimal

# Flask app context
from app import app, cache
from utils.cache_manager import FiyatCache, KarCache, StokCache, CacheStats

def test_cache_connection():
    """Cache bağlantısını test et"""
    print("\n" + "="*60)
    print("1. CACHE BAĞLANTI TESTİ")
    print("="*60)
    
    try:
        with app.app_context():
            # Basit bir cache testi
            test_key = "test_key"
            test_value = {"test": "data", "timestamp": datetime.now(timezone.utc).isoformat()}
            
            # Set
            cache.set(test_key, test_value, timeout=60)
            print("✅ Cache SET başarılı")
            
            # Get
            cached_value = cache.get(test_key)
            if cached_value == test_value:
                print("✅ Cache GET başarılı")
                print(f"   Cached value: {cached_value}")
            else:
                print("❌ Cache GET başarısız - Değer eşleşmiyor")
                return False
            
            # Delete
            cache.delete(test_key)
            deleted_value = cache.get(test_key)
            if deleted_value is None:
                print("✅ Cache DELETE başarılı")
            else:
                print("❌ Cache DELETE başarısız")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ Cache bağlantı hatası: {e}")
        return False


def test_fiyat_cache():
    """FiyatCache sınıfını test et"""
    print("\n" + "="*60)
    print("2. FİYAT CACHE TESTİ")
    print("="*60)
    
    try:
        with app.app_context():
            # Test verisi
            urun_id = 999
            oda_id = 999
            tarih = datetime.now(timezone.utc)
            
            fiyat_data = {
                'alis_fiyati': Decimal('10.50'),
                'satis_fiyati': Decimal('15.75'),
                'kar_tutari': Decimal('5.25'),
                'kar_orani': 50.0,
                'bedelsiz': False
            }
            
            # SET
            result = FiyatCache.set_dinamik_fiyat(urun_id, fiyat_data, oda_id, tarih)
            if result:
                print("✅ FiyatCache SET başarılı")
            else:
                print("❌ FiyatCache SET başarısız")
                return False
            
            # GET
            cached_fiyat = FiyatCache.get_dinamik_fiyat(urun_id, oda_id, tarih)
            if cached_fiyat:
                print("✅ FiyatCache GET başarılı")
                print(f"   Cached fiyat: {cached_fiyat}")
            else:
                print("❌ FiyatCache GET başarısız")
                return False
            
            # INVALIDATE
            count = FiyatCache.invalidate_urun_fiyat(urun_id)
            print(f"✅ FiyatCache INVALIDATE başarılı ({count} key temizlendi)")
            
            # Temizlendikten sonra GET
            cached_after_invalidate = FiyatCache.get_dinamik_fiyat(urun_id, oda_id, tarih)
            if cached_after_invalidate is None:
                print("✅ Cache invalidation doğrulandı")
            else:
                print("❌ Cache invalidation başarısız")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ FiyatCache test hatası: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_kar_cache():
    """KarCache sınıfını test et"""
    print("\n" + "="*60)
    print("3. KAR CACHE TESTİ")
    print("="*60)
    
    try:
        with app.app_context():
            # Test verisi
            otel_id = 1
            donem_tipi = 'gunluk'
            baslangic = datetime.now(timezone.utc).date()
            bitis = datetime.now(timezone.utc).date()
            
            kar_data = {
                'toplam_gelir': Decimal('1000.00'),
                'toplam_maliyet': Decimal('600.00'),
                'net_kar': Decimal('400.00'),
                'kar_marji': 40.0
            }
            
            # SET
            result = KarCache.set_donemsel_kar(otel_id, donem_tipi, baslangic, bitis, kar_data)
            if result:
                print("✅ KarCache SET başarılı")
            else:
                print("❌ KarCache SET başarısız")
                return False
            
            # GET
            cached_kar = KarCache.get_donemsel_kar(otel_id, donem_tipi, baslangic, bitis)
            if cached_kar:
                print("✅ KarCache GET başarılı")
                print(f"   Cached kar: {cached_kar}")
            else:
                print("❌ KarCache GET başarısız")
                return False
            
            # INVALIDATE
            count = KarCache.invalidate_otel_kar(otel_id)
            print(f"✅ KarCache INVALIDATE başarılı ({count} key temizlendi)")
            
            return True
            
    except Exception as e:
        print(f"❌ KarCache test hatası: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stok_cache():
    """StokCache sınıfını test et"""
    print("\n" + "="*60)
    print("4. STOK CACHE TESTİ")
    print("="*60)
    
    try:
        with app.app_context():
            # Test verisi
            urun_id = 999
            otel_id = 1
            
            stok_data = {
                'mevcut_stok': 100,
                'minimum_stok': 20,
                'kritik_seviye': False
            }
            
            # SET
            result = StokCache.set_stok_durum(urun_id, otel_id, stok_data)
            if result:
                print("✅ StokCache SET başarılı")
            else:
                print("❌ StokCache SET başarısız")
                return False
            
            # GET
            cached_stok = StokCache.get_stok_durum(urun_id, otel_id)
            if cached_stok:
                print("✅ StokCache GET başarılı")
                print(f"   Cached stok: {cached_stok}")
            else:
                print("❌ StokCache GET başarısız")
                return False
            
            # INVALIDATE
            count = StokCache.invalidate_urun_stok(urun_id, otel_id)
            print(f"✅ StokCache INVALIDATE başarılı ({count} key temizlendi)")
            
            return True
            
    except Exception as e:
        print(f"❌ StokCache test hatası: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_stats():
    """Cache istatistiklerini test et"""
    print("\n" + "="*60)
    print("5. CACHE İSTATİSTİKLERİ")
    print("="*60)
    
    try:
        with app.app_context():
            stats = CacheStats.get_cache_info()
            
            print("✅ Cache istatistikleri alındı:")
            print(f"   Cache Type: {stats.get('cache_type')}")
            print(f"   Default Timeout: {stats.get('default_timeout')}s")
            print(f"   Fiyat Timeout: {stats.get('fiyat_timeout')}s")
            print(f"   Kar Timeout: {stats.get('kar_timeout')}s")
            print(f"   Stok Timeout: {stats.get('stok_timeout')}s")
            
            if 'redis_stats' in stats:
                redis_stats = stats['redis_stats']
                print(f"\n   Redis İstatistikleri:")
                print(f"   - Total Commands: {redis_stats.get('total_commands_processed', 0)}")
                print(f"   - Keyspace Hits: {redis_stats.get('keyspace_hits', 0)}")
                print(f"   - Keyspace Misses: {redis_stats.get('keyspace_misses', 0)}")
                print(f"   - Hit Rate: {redis_stats.get('hit_rate', 0)}%")
            
            return True
            
    except Exception as e:
        print(f"❌ Cache stats hatası: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ana test fonksiyonu"""
    print("\n" + "="*60)
    print("REDIS CACHE ENTEGRASYON TESTİ")
    print("="*60)
    
    results = []
    
    # Test 1: Cache bağlantısı
    results.append(("Cache Bağlantı", test_cache_connection()))
    
    # Test 2: FiyatCache
    results.append(("FiyatCache", test_fiyat_cache()))
    
    # Test 3: KarCache
    results.append(("KarCache", test_kar_cache()))
    
    # Test 4: StokCache
    results.append(("StokCache", test_stok_cache()))
    
    # Test 5: Cache Stats
    results.append(("Cache Stats", test_cache_stats()))
    
    # Sonuçları özetle
    print("\n" + "="*60)
    print("TEST SONUÇLARI")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ BAŞARILI" if result else "❌ BAŞARISIZ"
        print(f"{test_name:20s}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "="*60)
    print(f"Toplam: {len(results)} test")
    print(f"Başarılı: {passed}")
    print(f"Başarısız: {failed}")
    print("="*60)
    
    if failed == 0:
        print("\n🎉 TÜM TESTLER BAŞARILI!")
        return 0
    else:
        print(f"\n⚠️  {failed} TEST BAŞARISIZ!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
