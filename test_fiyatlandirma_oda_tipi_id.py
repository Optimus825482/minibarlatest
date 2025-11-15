"""
Test: Fiyatlandırma Modülü - oda_tipi_id Güncellemesi
"""

from app import app
from models import db, Oda, Urun, OdaTipiSatisFiyati, OdaTipi
from utils.fiyatlandirma_servisler import FiyatYonetimServisi
from datetime import datetime, timezone
from decimal import Decimal


def test_oda_tipi_id_kullanimi():
    """Fiyatlandırma servislerinin oda_tipi_id ile çalıştığını test et"""
    
    with app.app_context():
        print("=" * 80)
        print("FİYATLANDIRMA MODÜLÜ - ODA_TİPİ_ID TEST")
        print("=" * 80)
        
        try:
            # 1. Test verilerini hazırla
            print("\n1️⃣  Test verileri hazırlanıyor...")
            
            # Oda tipi al
            oda_tipi = OdaTipi.query.first()
            if not oda_tipi:
                print("   ❌ Oda tipi bulunamadı!")
                return False
            
            print(f"   ✅ Oda Tipi: {oda_tipi.ad} (ID: {oda_tipi.id})")
            
            # Oda al
            oda = Oda.query.filter_by(oda_tipi_id=oda_tipi.id).first()
            if not oda:
                print("   ❌ Oda bulunamadı!")
                return False
            
            print(f"   ✅ Oda: {oda.oda_no} (ID: {oda.id})")
            
            # Ürün al
            urun = Urun.query.filter_by(aktif=True).first()
            if not urun:
                print("   ❌ Aktif ürün bulunamadı!")
                return False
            
            print(f"   ✅ Ürün: {urun.urun_adi} (ID: {urun.id})")
            
            # 2. Oda tipi fiyatı oluştur
            print("\n2️⃣  Oda tipi satış fiyatı oluşturuluyor...")
            
            # Mevcut fiyatı kontrol et
            mevcut_fiyat = OdaTipiSatisFiyati.query.filter_by(
                urun_id=urun.id,
                oda_tipi_id=oda_tipi.id,
                aktif=True
            ).first()
            
            if not mevcut_fiyat:
                # Yeni fiyat oluştur
                yeni_fiyat = OdaTipiSatisFiyati(
                    urun_id=urun.id,
                    oda_tipi_id=oda_tipi.id,
                    satis_fiyati=Decimal('50.00'),
                    baslangic_tarihi=datetime.now(timezone.utc),
                    aktif=True
                )
                db.session.add(yeni_fiyat)
                db.session.commit()
                print(f"   ✅ Yeni fiyat oluşturuldu: {yeni_fiyat.satis_fiyati} TL")
            else:
                print(f"   ✅ Mevcut fiyat: {mevcut_fiyat.satis_fiyati} TL")
            
            # 3. oda_tipi_fiyati_getir() test et
            print("\n3️⃣  oda_tipi_fiyati_getir() test ediliyor...")
            
            satis_fiyati = FiyatYonetimServisi.oda_tipi_fiyati_getir(
                urun_id=urun.id,
                oda_tipi_id=oda_tipi.id,
                tarih=datetime.now(timezone.utc)
            )
            
            if satis_fiyati:
                print(f"   ✅ Satış fiyatı alındı: {satis_fiyati} TL")
            else:
                print("   ❌ Satış fiyatı alınamadı!")
                return False
            
            # 4. dinamik_fiyat_hesapla() test et
            print("\n4️⃣  dinamik_fiyat_hesapla() test ediliyor...")
            
            try:
                sonuc = FiyatYonetimServisi.dinamik_fiyat_hesapla(
                    urun_id=urun.id,
                    oda_id=oda.id,
                    oda_tipi_id=oda_tipi.id,
                    miktar=1,
                    tarih=datetime.now(timezone.utc)
                )
                
                print(f"   ✅ Dinamik fiyat hesaplandı:")
                print(f"      - Alış Fiyatı: {sonuc['alis_fiyati']} TL")
                print(f"      - Satış Fiyatı: {sonuc['satis_fiyati']} TL")
                print(f"      - Kar Tutarı: {sonuc['kar_tutari']} TL")
                print(f"      - Kar Oranı: %{sonuc['kar_orani']}")
                
            except Exception as e:
                print(f"   ❌ Dinamik fiyat hesaplama hatası: {e}")
                return False
            
            # 5. Veritabanı kontrolü
            print("\n5️⃣  Veritabanı kontrolü...")
            
            # oda_tipi_id kullanımını kontrol et
            fiyatlar = OdaTipiSatisFiyati.query.filter_by(aktif=True).limit(5).all()
            
            print(f"   ✅ Aktif fiyat kayıtları: {len(fiyatlar)}")
            for fiyat in fiyatlar:
                print(f"      - Ürün ID: {fiyat.urun_id}, Oda Tipi ID: {fiyat.oda_tipi_id}, Fiyat: {fiyat.satis_fiyati} TL")
            
            print("\n" + "=" * 80)
            print("✅ TÜM TESTLER BAŞARILI!")
            print("=" * 80)
            
            return True
            
        except Exception as e:
            print(f"\n❌ Test hatası: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    test_oda_tipi_id_kullanimi()
